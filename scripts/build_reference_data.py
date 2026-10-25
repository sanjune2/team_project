"""기존 레퍼런스 분석 결과에 overview만 추가한다.

기존 frontend/public/reference/*.json을 읽어 overview만 추가한 뒤 원자적으로 반영한다.

사용법 (저장소 루트에서):
    python scripts/build_reference_data.py --input data/reference/reviews_p01.jsonl data/reference/reviews_p02.jsonl
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.llm import configured_settings  # noqa: E402

REQUIRED_INPUT_FIELDS = (
    "id",
    "text",
    "professor_id",
    "professor_name",
    "course_id",
    "course_name",
    "semester",
)
MAX_REVIEW_CHARS = 3000


class OverviewListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str
    text: str
    review_ids: list[str]


class OverviewGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sentiment: str
    topic: str
    short: str
    detail: str
    review_ids: list[str]


class OverviewCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    headline: dict[str, str]
    groups: list[OverviewGroup]


class OverviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience: str
    left: list[OverviewListItem]
    right: list[OverviewListItem]
    suggestion: str
    categories: list[OverviewCategory]


def normalize_id(value) -> str:
    return str(value)


def load_input_rows(paths: list[Path]) -> tuple[dict[str, dict], dict[tuple[str, str], list[dict]]]:
    """JSONL 원문을 읽는다. 여기서는 입력을 검증하는 데만 사용하고 분석하지 않는다."""
    rows_by_id: dict[str, dict] = {}
    bundles: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {path}")
        for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name} {line_no}번째 줄: JSON 오류 - {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path.name} {line_no}번째 줄: 각 행은 JSON 객체여야 합니다.")
            missing = [key for key in REQUIRED_INPUT_FIELDS if row.get(key) is None or not str(row.get(key, "")).strip()]
            if missing:
                raise ValueError(f"{path.name} {line_no}번째 줄: 필수 필드 누락 {missing}")
            if not isinstance(row["text"], str):
                raise ValueError(f"{path.name} {line_no}번째 줄: text는 문자열이어야 합니다.")
            if len(row["text"]) > MAX_REVIEW_CHARS:
                raise ValueError(f"{path.name} {line_no}번째 줄: text가 {MAX_REVIEW_CHARS}자를 초과합니다.")

            rid = normalize_id(row["id"])
            if rid in rows_by_id:
                raise ValueError(f"입력 파일 사이 id 중복: {rid}")
            normalized = dict(row)
            normalized["id"] = rid
            rows_by_id[rid] = normalized
            bundles[(str(row["course_id"]), str(row["semester"]))].append(normalized)

    if not rows_by_id:
        raise ValueError("입력 JSONL에 리뷰가 없습니다.")
    return rows_by_id, bundles


def review_category_sentiments(reviews: list[dict]) -> dict[str, set[tuple[str, str]]]:
    """각 리뷰에서 실제로 분석된 (category, sentiment) 조합을 수집한다."""
    pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for review in reviews:
        rid = normalize_id(review.get("review_id", ""))
        items = review.get("items", [])
        if not isinstance(items, list):
            raise ValueError(f"리뷰 {rid}: items는 배열이어야 합니다.")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"리뷰 {rid}: items의 각 항목은 객체여야 합니다.")
            category = item.get("category")
            sentiment = item.get("sentiment")
            if category is not None and sentiment is not None:
                pairs[rid].add((str(category), str(sentiment)))
    return pairs


def validate_overview(overview: dict, reviews: list[dict]) -> dict:
    """필수 구조와 review_ids를 검증하고 basis를 계산한다."""
    # Pydantic으로 필수 필드, 자료형, 불필요한 필드를 엄격히 검증한다.
    parsed = OverviewOutput.model_validate(overview)
    result = parsed.model_dump(mode="json")

    valid_ids = set()
    for review in reviews:
        rid = review.get("review_id")
        if rid is None:
            raise ValueError("분석 결과 리뷰에 review_id가 없습니다.")
        valid_ids.add(normalize_id(rid))
    category_sentiments = review_category_sentiments(reviews)
    actual_categories = {category for pairs in category_sentiments.values() for category, _ in pairs}

    def clean_items(items: list[dict], category: str | None = None, sentiment: str | None = None) -> list[dict]:
        cleaned = []
        for item in items:
            ids = item.get("review_ids")
            if not isinstance(ids, list):
                raise ValueError("review_ids는 배열이어야 합니다.")
            kept = []
            for value in ids:
                if value is None or isinstance(value, (dict, list)):
                    raise ValueError("review_ids에는 문자열 또는 숫자 ID만 허용됩니다.")
                rid = normalize_id(value)
                if rid not in valid_ids:
                    raise ValueError(f"존재하지 않는 review_id가 overview에 있습니다: {rid}")
                if category is not None and sentiment is not None:
                    if (category, sentiment) not in category_sentiments.get(rid, set()):
                        raise ValueError(
                            f"review_id {rid}에는 category={category}, sentiment={sentiment} 근거가 없습니다."
                        )
                if rid not in kept:
                    kept.append(rid)
            if kept:
                normalized_item = dict(item)
                normalized_item["review_ids"] = kept
                normalized_item["basis"] = len(kept)
                cleaned.append(normalized_item)
        cleaned.sort(key=lambda item: item["basis"], reverse=True)
        return cleaned

    result["left"] = clean_items(result["left"])
    result["right"] = clean_items(result["right"])

    cleaned_categories = []
    seen_categories = set()
    for category in result["categories"]:
        code = category["category"]
        if code not in actual_categories:
            raise ValueError(f"분석 결과에 없는 category가 overview에 있습니다: {code}")
        if code in seen_categories:
            raise ValueError(f"overview.categories에 중복 category가 있습니다: {code}")
        seen_categories.add(code)
        cleaned_groups = []
        for group in category["groups"]:
            sentiment = group["sentiment"]
            cleaned_groups.extend(clean_items([group], category=code, sentiment=sentiment))
        if cleaned_groups:
            category["groups"] = cleaned_groups
            cleaned_categories.append(category)
    result["categories"] = cleaned_categories
    result["basis"] = len(valid_ids)
    return result


def generate_overview(response: dict, source_text_by_id: dict[str, str], audience: str) -> dict:
    """기존 분석 JSON을 읽어 overview만 생성한다. 분석 API는 호출하지 않는다."""
    if audience not in {"instructor", "learner"}:
        raise ValueError("audience는 instructor 또는 learner여야 합니다.")
    reviews = response.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("기존 분석 결과에 reviews 배열이 없습니다.")

    source_reviews = []
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("reviews의 각 항목은 객체여야 합니다.")
        rid_value = review.get("review_id")
        if rid_value is None:
            raise ValueError("기존 분석 결과 리뷰에 review_id가 없습니다.")
        rid = normalize_id(rid_value)
        if rid not in source_text_by_id:
            raise ValueError(f"분석 결과의 review_id {rid}가 입력 JSONL에 없습니다.")
        if review.get("status") != "ok":
            continue
        items = review.get("items", [])
        if not isinstance(items, list):
            raise ValueError(f"리뷰 {rid}: items는 배열이어야 합니다.")
        source_reviews.append({
            "review_id": rid,
            "text": source_text_by_id[rid],
            "overall_sentiment": review.get("overall_sentiment"),
            "items": [
                {
                    "category": item.get("category"),
                    "sentiment": item.get("sentiment"),
                    "summary": item.get("summary"),
                    "evidence": item.get("evidence"),
                    "condition": item.get("condition"),
                }
                for item in items
                if isinstance(item, dict)
            ],
        })

    if not source_reviews:
        raise ValueError("overview를 생성할 수 있는 성공 리뷰가 없습니다.")

    source = {
        "audience": audience,
        "reviews": source_reviews,
        "summary_by_category": response.get("summary_by_category", []),
    }
    instructions = """
너는 대학 강의평가 분석 결과의 종합 의견을 작성한다.
입력으로 주어진 리뷰 원문과 기존 분석 결과만 사용하고 사실을 만들어내지 않는다.
기존 분석 결과를 재분석하거나 수정하지 않는다. 자연스러운 한국어를 사용한다.

출력 규칙:
- audience는 입력값을 그대로 사용한다.
- left는 유지할 점 또는 수강 추천 이유, right는 개선할 점 또는 수강 시 고려 사항이다.
- left와 right는 각각 최대 3개 항목으로 작성한다.
- 각 항목 keyword는 짧은 평가 주제, text는 근거가 있는 종합 문장이다.
- 모든 review_ids는 문장을 실제로 뒷받침하는 리뷰 ID만 넣는다.
- suggestion은 입력 근거에 기반한 교수자 개선 방향이다. 근거가 없으면 지어내지 않는다.
- categories에는 입력 분석에 실제로 등장한 category만 사용한다.
- headline은 감성별로 해당 category에 맞는 짧은 문장이다.
- groups는 주제별로 묶고 short는 짧게, detail은 구체적으로 작성한다.
- 그룹 review_ids에는 해당 category와 sentiment를 실제로 가진 리뷰만 넣는다.
- 근거 없는 빈도 표현이나 일반화를 하지 않는다.
- 지정된 JSON 스키마에 맞춰 출력한다.
"""
    key, model, effort = configured_settings()
    options = {"reasoning": {"effort": effort}}
    if effort == "none":
        options["temperature"] = 0

    with OpenAI(api_key=key, timeout=60.0, max_retries=0) as client:
        result = client.responses.parse(
            model=model,
            store=False,
            instructions=instructions,
            input=json.dumps(source, ensure_ascii=False),
            text_format=OverviewOutput,
            max_output_tokens=8000,
            **options,
        )
    if result.status != "completed" or result.output_parsed is None:
        raise ValueError("overview 생성 응답이 완료되지 않았습니다.")
    overview = result.output_parsed.model_dump(mode="json")
    overview["audience"] = audience
    return validate_overview(overview, reviews)


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def commit_outputs(staging: Path, output_dir: Path) -> None:
    """스테이징 파일을 반영한다. 교체 도중 실패하면 기존 파일을 복구한다."""
    staged_files = sorted(path for path in staging.iterdir() if path.is_file())
    backup_dir = Path(tempfile.mkdtemp(prefix=".reference_backup_", dir=output_dir.parent))
    replaced = []
    installed = []
    try:
        for staged in staged_files:
            destination = output_dir / staged.name
            backup = backup_dir / staged.name
            if destination.exists():
                os.replace(destination, backup)
                replaced.append((backup, destination))
            os.replace(staged, destination)
            installed.append(destination)
    except Exception:
        for destination in reversed(installed):
            if destination.exists():
                destination.unlink()
        for backup, destination in reversed(replaced):
            if backup.exists():
                os.replace(backup, destination)
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", nargs="+", required=True, help="원문이 들어 있는 리뷰 JSONL 파일")
    parser.add_argument("--out", default="frontend/public/reference", help="기존 분석 JSON 디렉터리")
    args = parser.parse_args()

    input_paths = [ROOT / filename for filename in args.input]
    source_text_by_id, bundles = load_input_rows(input_paths)
    output_dir = ROOT / args.out
    if not output_dir.is_dir():
        raise FileNotFoundError(f"기존 분석 결과 디렉터리가 없습니다: {output_dir}")

    # 모든 파일을 미리 확인한다. index.json과 분석 필드는 수정하지 않는다.
    targets: list[tuple[Path, str]] = []
    for course_id, semester in sorted(bundles):
        path = output_dir / f"{course_id}_{semester}.json"
        if not path.is_file():
            raise FileNotFoundError(f"기존 학기별 분석 파일이 없습니다: {path.name}")
        targets.append((path, "instructor"))
    for course_id in sorted({course_id for course_id, _ in bundles}):
        path = output_dir / f"{course_id}_all.json"
        if not path.is_file():
            raise FileNotFoundError(f"기존 과목 합산 분석 파일이 없습니다: {path.name}")
        targets.append((path, "learner"))

    # 출력 대상 중복 제거. 파일별로 overview만 교체하고 나머지 필드는 그대로 둔다.
    unique_targets = {}
    for path, audience in targets:
        unique_targets[path.resolve()] = (path, audience)

    staging = Path(tempfile.mkdtemp(prefix=".reference_staging_", dir=output_dir.parent))
    try:
        for path, audience in unique_targets.values():
            try:
                original = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"기존 JSON 파일을 읽을 수 없습니다: {path.name}: {exc}") from exc
            if not isinstance(original, dict):
                raise ValueError(f"기존 분석 파일의 최상위 값은 객체여야 합니다: {path.name}")

            # 새 딕셔너리에 overview만 덮어쓴다. 기존 집계와 meta는 수정하지 않는다.
            updated = dict(original)
            updated["overview"] = generate_overview(original, source_text_by_id, audience)
            staged_path = staging / path.name
            save_json(staged_path, updated)

            # 저장한 JSON을 다시 읽어 파일 형식만 확인한다.
            json.loads(staged_path.read_text(encoding="utf-8"))
            print(f"overview 생성 완료: {path.name} ({audience})")

        # 모든 생성과 검증이 성공한 경우에만 기존 파일을 교체한다.
        commit_outputs(staging, output_dir)
        print(f"완료: {len(unique_targets)}개 기존 JSON 파일에 overview만 반영했습니다.")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
