from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from google.genai import errors

from app.services.gemini_service import (
    GeminiKeyMissingError,
    GeminiServiceError,
    GeneratedAnswersResponse,
    generate_answer_pool,
)
from app.services.text_mutation import micro_mutate


def test_micro_mutate_creates_variants_without_losing_content() -> None:
    rng = np.random.default_rng(3)
    pool = ["Giao hàng nhanh.", "Hàng chính hãng", "Giá hơi cao"]
    variants = {micro_mutate("Giao hàng nhanh.", rng, pool) for _ in range(300)}
    assert len(variants) >= 4
    assert all(v.strip() and "giao hàng nhanh" in v.casefold() for v in variants)
    assert micro_mutate("   ", rng, pool) == "   "


class FakeModels:
    def __init__(self, batches: list[Any]) -> None:
        self.batches = batches
        self.prompts: list[str] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        self.prompts.append(contents)
        item = self.batches.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(parsed=GeneratedAnswersResponse(answers=item), text=None)


def fake_client(batches: list[Any]) -> Any:
    models = FakeModels(batches)
    return SimpleNamespace(aio=SimpleNamespace(models=models)), models


async def no_sleep(_: float) -> None:
    return None


async def test_pool_is_batched_and_deduplicated() -> None:
    first = [f"Câu {i}" for i in range(50)]
    second = ["Câu 1", "câu 2  ", *[f"Mới {i}" for i in range(48)]]
    third = ["Mới 100", "Mới 101", "Mới 102"]
    client, models = fake_client([first, second, third])
    answers = await generate_answer_pool("Góp ý?", "Khảo sát", 100, client=client, sleep=no_sleep)
    assert len(answers) == 100 and len({a.casefold() for a in answers}) == 100
    assert "KHÔNG lặp lại" in models.prompts[1]


async def test_retries_rate_limit_then_succeeds() -> None:
    client, models = fake_client([errors.APIError(429, {"error": {"message": "quota"}}), ["Một", "Hai"]])
    answers = await generate_answer_pool("Góp ý?", "Khảo sát", 2, client=client, sleep=no_sleep)
    assert answers == ["Một", "Hai"] and len(models.prompts) == 2


async def test_invalid_key_gives_friendly_error() -> None:
    client, _ = fake_client([errors.APIError(400, {"error": {"message": "API key not valid"}})])
    with pytest.raises(GeminiServiceError, match="API key"):
        await generate_answer_pool("Góp ý?", "Khảo sát", 5, client=client, sleep=no_sleep)


async def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.gemini_service.resolve_gemini_api_key", lambda _: None)
    with pytest.raises(GeminiKeyMissingError):
        await generate_answer_pool("Góp ý?", "Khảo sát", 5)
