"""Kiểm chứng gửi thật lên một Google Form THỬ của chính bạn (dev-notes RISK-009, RISK-010).

Gửi đúng 1 phản hồi bằng HTTP và (tùy chọn) 1 phản hồi bằng trình duyệt dự phòng, in kết quả
phân loại của app và lưu HTML Google trả về để đối chiếu. KHÔNG dùng với form khảo sát thật.

    python tools/verify_live_form.py <link form thử> [--browser] [--out <thư mục>]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252 (dev-notes ISS-002)

from app.core.config import get_settings  # noqa: E402
from app.schemas.campaign_schema import QuestionRuleConfig  # noqa: E402
from app.services.form_parser import parse_google_form  # noqa: E402
from app.services.spss_generator import SurveyDataGenerator, build_payload_tuples  # noqa: E402
from app.workers.http_submitter import classify_response  # noqa: E402
from app.workers.playwright_fallback import PlaywrightSubmitter, build_prefill_url  # noqa: E402

TEST_TEXT = ["Phản hồi thử nghiệm từ Auto-Form"]


def text_rules(structure) -> list[QuestionRuleConfig]:  # noqa: ANN001
    return [
        QuestionRuleConfig(entry_id=q.entry_id, question_type=q.type_id, text_pool=TEST_TEXT, other_text_pool=TEST_TEXT)
        for q in structure.questions
    ]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--browser", action="store_true", help="gửi thêm 1 phản hồi qua trình duyệt dự phòng")
    parser.add_argument("--out", default=".", help="thư mục lưu HTML trả về")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    structure = await parse_google_form(args.url)
    print(f"Form: {structure.title} | {structure.total_pages} trang | {len(structure.questions)} câu | fbzx={bool(structure.fbzx)}")
    generator = SurveyDataGenerator(structure, text_rules(structure), seed=None)
    first, second = generator.generate(2)

    payload = build_payload_tuples(first, structure.fbzx)
    print(f"[HTTP] pageHistory={first.page_history_str}, {len(payload)} trường")
    headers = {"User-Agent": get_settings().HTTP_USER_AGENT, "Content-Type": "application/x-www-form-urlencoded", "Referer": structure.view_url}
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        from urllib.parse import urlencode

        response = await client.post(structure.submit_url, content=urlencode(payload).encode(), headers=headers)
    (out / "http_response.html").write_text(response.text, encoding="utf-8")
    outcome = classify_response(response.status_code, response.text, response.headers)
    print(f"[HTTP] status={response.status_code} → app phân loại: {outcome.kind} ({outcome.error or 'OK'})")
    print(f"[HTTP] final url: {response.url}")

    if args.browser:
        print(f"[TRÌNH DUYỆT] link điền sẵn: {build_prefill_url(structure, second)[:120]}…")
        submitter = PlaywrightSubmitter()
        try:
            result = await submitter.submit(structure, second)
        finally:
            await submitter.close()
        print(f"[TRÌNH DUYỆT] → {result.kind} ({result.error or 'OK'})")
    print("Kiểm tra tab Câu trả lời của form thử để đối chiếu số phản hồi đã nhận.")


if __name__ == "__main__":
    asyncio.run(main())
