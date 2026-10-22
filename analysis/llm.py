"""Single-review extraction. Backend owns evidence checks and aggregation."""
import hashlib
import os
import time
from .runtime import ROOT, enable_local_packages, load_private_env

enable_local_packages()
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError
from pydantic import ValidationError
from .llm_schemas import LLMReviewOutput, LLMWireOutput
from .prompt import build_instructions


class LLMAnalysisError(RuntimeError):
    """Safe error message without SDK request bodies or credentials."""


def merge_same_pairs(items):
    """Merge duplicate category/sentiment without inventing evidence text."""
    grouped = {}
    for item in items:
        key = (item.category, item.sentiment)
        if key not in grouped:
            grouped[key] = item.model_copy(deep=True)
            continue
        target = grouped[key]
        if item.summary != target.summary:
            target.summary += ' / ' + item.summary
        if len(item.evidence) > len(target.evidence):
            target.evidence = item.evidence
        target.keywords = list(dict.fromkeys(target.keywords + item.keywords))[:3]
        if item.condition and item.condition != target.condition:
            target.condition = ' / '.join(filter(None, [target.condition, item.condition]))
        target.mentions_change = target.mentions_change or item.mentions_change
    return list(grouped.values())


def configured_settings():
    load_private_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    effort = os.environ.get("OPENAI_REASONING_EFFORT", "none").strip()
    if not key or not model:
        raise LLMAnalysisError("OPENAI_API_KEY와 OPENAI_MODEL을 설정하세요.")
    if effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
        raise LLMAnalysisError("OPENAI_REASONING_EFFORT 설정이 올바르지 않습니다.")
    return key, model, effort


def analyze_review_with_metrics(text: str, *, semester: str | None = None):
    if not isinstance(text, str) or not text.strip() or len(text) > 3000:
        raise ValueError("리뷰는 공백이 아닌 1~3000자 문자열이어야 합니다.")
    if semester is not None and (not isinstance(semester, str) or not semester.strip()):
        raise ValueError("semester는 비어 있지 않은 문자열 또는 null이어야 합니다.")
    key, model, effort = configured_settings()
    glossary_path = ROOT / "docs/slang_glossary.md"
    glossary = glossary_path.read_text(encoding="utf-8") if glossary_path.is_file() else ""
    options = {"reasoning": {"effort": effort}}
    if effort == "none":
        options["temperature"] = 0
    started = time.perf_counter()
    try:
        with OpenAI(api_key=key, timeout=30.0, max_retries=0) as client:
            response = client.responses.parse(
                model=model, store=False,
                instructions=build_instructions(glossary),
                input=text,
                text_format=LLMWireOutput, max_output_tokens=4000,
                **options,
            )
        if response.status != "completed" or response.output_parsed is None:
            raise LLMAnalysisError("LLM 응답이 미완료이거나 분석을 거부했습니다.")
        wire = LLMWireOutput.model_validate(response.output_parsed.model_dump())
        parsed = LLMReviewOutput(items=merge_same_pairs(wire.items))
    except APITimeoutError:
        raise LLMAnalysisError("OpenAI 응답 제한 시간 30초를 초과했습니다.") from None
    except APIConnectionError:
        raise LLMAnalysisError("OpenAI 서버에 연결할 수 없습니다.") from None
    except APIError as error:
        status = getattr(error, "status_code", None)
        raise LLMAnalysisError(f"OpenAI 요청 실패(HTTP {status or 'unknown'}). 모델 접근 권한·결제·한도를 확인하세요.") from None
    except ValidationError as error:
        # Only schema locations/types. Never include input, context or SDK bodies.
        details = ", ".join(
            f"{'.'.join(str(part) for part in issue['loc']) or 'output'}:{issue['type']}"
            for issue in error.errors(include_input=False, include_context=False)[:5]
        )
        raise LLMAnalysisError(f"LLM 응답 형식 검증 실패({details}).") from None
    except (ValueError, TypeError):
        raise LLMAnalysisError("LLM 응답이 분석 출력 형식을 충족하지 않습니다.") from None
    except LLMAnalysisError:
        raise
    except Exception as error:
        raise LLMAnalysisError(f"LLM 응답 처리 실패({type(error).__name__}).") from None
    usage = response.usage.model_dump() if response.usage is not None else None
    return parsed, {
        "model": response.model, "reasoning_effort": effort,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "usage": usage, "glossary_loaded": bool(glossary.strip()),
        "prompt_sha256": hashlib.sha256(build_instructions(glossary).encode()).hexdigest(),
        "merged_item_count": len(wire.items) - len(parsed.items),
    }


def analyze_review(text: str, *, semester: str | None = None) -> LLMReviewOutput:
    """Backend adapter: consume .model_dump() when backend expects a dict."""
    parsed, _ = analyze_review_with_metrics(text, semester=semester)
    return parsed
