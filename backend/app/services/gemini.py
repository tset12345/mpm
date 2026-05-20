import asyncio
import json
import logging

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# Free-tier: ~15 RPM → enforce a minimum interval between calls
_MIN_INTERVAL = 5.0  # seconds between consecutive Gemini requests
_last_call_time: float = 0.0

_PROMPT_TEMPLATE = """\
당신은 주식 리포트 전문 분석가입니다.
아래 리포트 본문을 읽고 투자자 관점에서 핵심을 추출하여 반드시 아래 JSON 형식으로만 응답하세요.
마크다운 코드블록이나 추가 설명 없이 순수 JSON만 출력하세요.

{{
  "summary": "핵심 포인트 1 (결론/투자의견)\\n핵심 포인트 2 (실적/밸류에이션 근거)\\n핵심 포인트 3 (목표주가/리스크 등)",
  "target_companies": [
    {{"name": "기업명", "code": "6자리 종목코드"}}
  ]
}}

규칙:
- summary: \\n 으로 구분된 정확히 3문장. 각 문장은 50자 이내. 수치·팩트 우선, 추상적 표현 금지.
- target_companies: 본문에 언급된 한국 상장 기업만 포함. 종목코드를 확실히 모르면 제외. 최대 5개.
- 반드시 유효한 JSON만 출력. 키 이름·구조 변경 금지.

리포트 본문 (최대 1,500자):
{text}
"""


async def summarize_report(text: str) -> dict:
    global _last_call_time

    # Rate-limit: wait if the previous call was too recent
    import time
    elapsed = time.monotonic() - _last_call_time
    if elapsed < _MIN_INTERVAL:
        await asyncio.sleep(_MIN_INTERVAL - elapsed)

    prompt = _PROMPT_TEMPLATE.format(text=text[:1500])

    for attempt in range(3):
        _last_call_time = time.monotonic()
        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            return json.loads(raw)
        except Exception as e:
            err = str(e)
            if "429" in err or "ResourceExhausted" in err or "quota" in err.lower():
                wait = 15 * (attempt + 1)  # 15s, 30s, 45s
                logger.warning(f"Gemini RPM 한도 초과 — {wait}초 대기 후 재시도 ({attempt + 1}/3)")
                await asyncio.sleep(wait)
            elif attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                raise

    raise RuntimeError("Gemini API 재시도 횟수 초과")
