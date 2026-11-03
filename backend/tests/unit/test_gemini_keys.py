"""Chuỗi key Gemini, key nhúng lúc build và lời gọi có thử lại / model dự phòng."""

from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from google.genai import errors

from app.core import build_secrets
from app.services import gemini_keys
from app.services.gemini_call import FALLBACK_MODELS, GeminiCallError, generate_json
from app.services.gemini_keys import (
    AiKeysUnavailableError,
    AiUnreachableError,
    KeySlot,
    KeyState,
    run_with_keys,
)

KEYS = [(KeySlot.USER, "user-key"), (KeySlot.SHARED, "shared-key"), (KeySlot.BACKUP, "backup-key")]


def _api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": f"lỗi {code}"}})


def _caller(outcomes: dict[str, Any]):
    used: list[str] = []

    async def call(client: str) -> str:
        used.append(client)
        outcome = outcomes[client]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return call, used


# ------------------------------------------------------------------ build secrets
@pytest.mark.parametrize("key", ["AIzaSyABC123", "AQ.FakeKeyOnlyForTests-000", "k"])
def test_ma_hoa_khu_lai_dung_key(key: str) -> None:
    blob = build_secrets.encode(key)
    assert key not in blob and build_secrets.decode(blob) == key


def test_giai_ma_chuoi_rong_la_none() -> None:
    assert build_secrets.decode("") is None


def test_ban_chay_tu_ma_nguon_khong_co_key_nhung() -> None:
    assert build_secrets.embedded_keys() == (None, None)


def test_candidate_keys_thu_tu_va_dung_key_dev_lam_key_chung(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_keys.secret_store, "get_gemini_api_key", lambda: "u")
    monkeypatch.setattr(gemini_keys, "embedded_keys", lambda: (None, "b"))
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "GEMINI_API_KEY", "dev")
    assert gemini_keys.candidate_keys() == [(KeySlot.USER, "u"), (KeySlot.SHARED, "dev"), (KeySlot.BACKUP, "b")]


def test_key_nhung_uu_tien_hon_key_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_keys.secret_store, "get_gemini_api_key", lambda: None)
    monkeypatch.setattr(gemini_keys, "embedded_keys", lambda: ("s", None))
    assert gemini_keys.candidate_keys()[1] == (KeySlot.SHARED, "s")


# ------------------------------------------------------------------ chain
async def test_dung_key_dau_tien_thanh_cong() -> None:
    call, used = _caller({"user-key": "ok"})
    assert await run_with_keys(call, keys=KEYS, client_factory=lambda k: k) == "ok"
    assert used == ["user-key"]


async def test_het_luot_chuyen_key_sau() -> None:
    call, used = _caller({"user-key": _api_error(429), "shared-key": GeminiCallError("hết", 429), "backup-key": "ok"})
    assert await run_with_keys(call, keys=KEYS, client_factory=lambda k: k) == "ok"
    assert used == ["user-key", "shared-key", "backup-key"]


@pytest.mark.parametrize("code", [400, 401, 403])
async def test_key_khong_hop_le_chuyen_key_sau(code: int) -> None:
    call, _ = _caller({"user-key": _api_error(code), "shared-key": "ok"})
    assert await run_with_keys(call, keys=KEYS, client_factory=lambda k: k) == "ok"


async def test_het_ca_chuoi_bao_trang_thai_tung_key() -> None:
    call, _ = _caller({"shared-key": _api_error(429), "backup-key": _api_error(403)})
    keys = [(KeySlot.USER, None), *KEYS[1:]]
    with pytest.raises(AiKeysUnavailableError, match="Hết lượt AI") as info:
        await run_with_keys(call, keys=keys, client_factory=lambda k: k)
    assert [(a.slot, a.state) for a in info.value.attempts] == [
        (KeySlot.USER, KeyState.MISSING), (KeySlot.SHARED, KeyState.EXHAUSTED), (KeySlot.BACKUP, KeyState.INVALID),
    ]


async def test_chua_co_key_nao() -> None:
    call, used = _caller({})
    with pytest.raises(AiKeysUnavailableError, match="Chưa có API key"):
        await run_with_keys(call, keys=[(s, None) for s, _ in KEYS], client_factory=lambda k: k)
    assert used == []


async def test_key_trung_nhau_chi_thu_mot_lan() -> None:
    call, used = _caller({"same": _api_error(429)})
    with pytest.raises(AiKeysUnavailableError):
        await run_with_keys(call, keys=[(KeySlot.USER, "same"), (KeySlot.SHARED, "same")], client_factory=lambda k: k)
    assert used == ["same"]


async def test_mat_mang_bao_loi_rieng_khong_doi_key() -> None:
    call, used = _caller({"user-key": httpx.ConnectError("offline")})
    with pytest.raises(AiUnreachableError, match="mạng"):
        await run_with_keys(call, keys=KEYS, client_factory=lambda k: k)
    assert used == ["user-key"]


async def test_loi_khac_khong_nuot() -> None:
    call, _ = _caller({"user-key": ValueError("bug")})
    with pytest.raises(ValueError, match="bug"):
        await run_with_keys(call, keys=KEYS, client_factory=lambda k: k)


# ------------------------------------------------------------------ generate_json
class _Models:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.models: list[str] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        self.models.append(model)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _client(outcomes: list[Any]) -> tuple[Any, _Models]:
    models = _Models(outcomes)
    return SimpleNamespace(aio=SimpleNamespace(models=models)), models


async def _no_sleep(_: float) -> None:
    return None


async def test_qua_tai_thu_lai_roi_thanh_cong() -> None:
    client, models = _client([_api_error(503), "ok"])
    assert await generate_json(client, "m", "p", dict, temperature=0, sleep=_no_sleep) == "ok"
    assert models.models == ["m", "m"]


async def test_qua_tai_keo_dai_chuyen_model_du_phong() -> None:
    client, models = _client([_api_error(503)] * 4 + ["ok"])
    assert await generate_json(client, "m", "p", dict, temperature=0, sleep=_no_sleep) == "ok"
    assert models.models == ["m"] * 4 + [FALLBACK_MODELS[0]]


async def test_model_ngung_ho_tro_404_chuyen_ngay() -> None:
    client, models = _client([_api_error(404), "ok"])
    assert await generate_json(client, "gemini-2.5-flash", "p", dict, temperature=0, sleep=_no_sleep) == "ok"
    assert models.models == ["gemini-2.5-flash", FALLBACK_MODELS[0]]


async def test_het_luot_chi_thu_lai_mot_lan_roi_bao_ma_429() -> None:
    client, models = _client([_api_error(429), _api_error(429)])
    with pytest.raises(GeminiCallError) as info:
        await generate_json(client, "m", "p", dict, temperature=0, sleep=_no_sleep)
    assert info.value.code == 429 and len(models.models) == 2


async def test_key_sai_khong_thu_lai() -> None:
    client, models = _client([_api_error(400)])
    with pytest.raises(GeminiCallError, match="API key") as info:
        await generate_json(client, "m", "p", dict, temperature=0, sleep=_no_sleep)
    assert info.value.code == 400 and models.models == ["m"]


async def test_moi_model_deu_qua_tai_bao_loi_de_hieu() -> None:
    client, _ = _client([_api_error(503)] * 20)
    with pytest.raises(GeminiCallError, match="quá tải") as info:
        await generate_json(client, "m", "p", dict, temperature=0, sleep=_no_sleep)
    assert info.value.code == 503
