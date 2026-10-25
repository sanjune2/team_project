
"""레퍼런스(가상 고객사) 화면용 분석 결과 JSON 만들기.

사용법 (저장소 루트에서, 백엔드 서버를 먼저 켠 상태):
    uvicorn backend.main:app --port 8000
    # 다른 터미널에서 실행. 실제 분석을 위해 .env의 USE_MOCK=false 확인
    python scripts/build_reference_data.py --input data/reference/reviews_p01.jsonl data/reference/reviews_p02.jsonl

하는 일
1. 입력 JSONL을 (과목, 학기) 단위로 묶어 /api/analyze 호출
2. 리뷰 원문을 결과에 추가
3. 같은 과목의 여러 학기 결과를 합쳐 집계 재계산
4. overview 그룹의 review_ids, basis를 검증하고 정렬
5. 모든 결과를 임시 디렉터리에 생성한 후 검증을 마치면 반영

출력:
    frontend/public/reference/index.json
    frontend/public/reference/{course_id}_{semester}.json
    frontend/public/reference/{course_id}_all.json
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, ConfigDict, Field
from openai import OpenAI
from analysis.llm import configured_settings

from backend.postprocess import summarize_by_category  # noqa: E402
from backend.schemas import ReviewResult, ReviewStatus  # noqa: E402


REQUIRED = [
    "id",
    "text",
    "professor_id",
    "professor_name",
    "course_id",
    "course_name",
    "semester",
]
MAX_PER_REQUEST = 50

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
    """리뷰 ID 비교 시 문자열/정수 차이를 없앤다."""
    return str(value)


def load_rows(path: Path) -> list[dict]:
    """JSONL 입력을 읽고 필수 필드, 길이, ID 중복을 검사한다."""
    rows = []

    for line_no, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.exit(f"{path.name} {line_no}번째 줄: JSON 형식 오류 - {exc}")

        if not isinstance(row, dict):
            sys.exit(f"{path.name} {line_no}번째 줄: 각 행은 JSON 객체여야 합니다.")

        missing = [
            key for key in REQUIRED
            if row.get(key) is None or not str(row.get(key, "")).strip()
        ]
        if missing:
            sys.exit(f"{path.name} {line_no}번째 줄: 빠진 필드 {missing}")

        if not isinstance(row["text"], str):
            sys.exit(f"{path.name} {line_no}번째 줄: text는 문자열이어야 합니다.")

        if len(row["text"]) > 3000:
            sys.exit(
                f"{path.name} {line_no}번째 줄: "
                f"3000자 초과 ({len(row['text'])}자)"
            )

        row["id"] = normalize_id(row["id"])
        rows.append(row)

    id_counts = Counter(row["id"] for row in rows)
    duplicates = sorted(key for key, count in id_counts.items() if count > 1)

    if duplicates:
        sys.exit(f"{path.name}: id 중복 - {duplicates}")

    return rows


def call_analyze(server: str, reviews: list[dict]) -> dict:
    """표준 요청 형식으로 API를 호출한다."""
    body = json.dumps(
        {
            "reviews": [
                {
                    "id": row["id"],
                    "text": row["text"],
                    "semester": row["semester"],
                }
                for row in reviews
            ]
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{server.rstrip('/')}/api/analyze",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        sys.exit(f"/api/analyze HTTP 오류 ({exc.code}): {detail}")

    except urllib.error.URLError as exc:
        sys.exit(
            f"서버 호출 실패 ({server}): {exc}. "
            "백엔드 서버가 켜져 있는지 확인하세요."
        )

    except json.JSONDecodeError as exc:
        sys.exit(f"/api/analyze 응답이 올바른 JSON이 아닙니다: {exc}")

    if not isinstance(result, dict) or not isinstance(result.get("reviews"), list):
        sys.exit("/api/analyze 응답에 reviews 배열이 없습니다.")

    if not isinstance(result.get("meta"), dict):
        sys.exit("/api/analyze 응답에 meta 객체가 없습니다.")

    return result


def review_category_sentiments(reviews: list[dict]) -> dict[str, set]:
    """리뷰별로 실제 분석된 (category, sentiment) 쌍을 수집한다."""
    result = defaultdict(set)

    for review in reviews:
        review_id = normalize_id(review.get("review_id", ""))

        for item in review.get("items", []) or []:
            if not isinstance(item, dict):
                continue

            category = item.get("category")
            sentiment = item.get("sentiment")

            if category is not None and sentiment is not None:
                result[review_id].add((str(category), str(sentiment)))

    return result

def generate_overview(response: dict, audience: str = "instructor") -> dict:
    """기존 분석 결과를 이용해 overview만 별도로 생성한다."""
    if audience not in {"instructor", "learner"}:
        raise ValueError("audience는 instructor 또는 learner여야 합니다.")

    key, model, effort = configured_settings()

    reviews = response.get("reviews", [])
    summaries = response.get("summary_by_category", [])

    # 리뷰 원문과 기존 분석 결과만 전달한다.
    source = {
        "audience": audience,
        "reviews": [
            {
                "review_id": str(r.get("review_id", "")),
                "text": r.get("text", ""),
                "overall_sentiment": r.get("overall_sentiment"),
                "items": [
                    {
                        "category": item.get("category"),
                        "sentiment": item.get("sentiment"),
                        "summary": item.get("summary"),
                        "evidence": item.get("evidence"),
                        "condition": item.get("condition"),
                    }
                    for item in r.get("items", [])
                    if isinstance(item, dict)
                ],
            }
            for r in reviews
            if r.get("status") == "ok"
        ],
        "summary_by_category": summaries,
    }

    instructions = """
너는 대학 강의평가 분석 결과의 종합 의견을 작성한다.

입력으로 주어진 리뷰 원문과 분석 결과만 사용한다.
입력에 없는 사실, 원인, 학생 의견을 만들어내지 않는다.
기존 분석 결과를 재분석하거나 수정하지 않는다.
모든 문장은 자연스러운 한국어로 작성한다.

출력 규칙:
- audience는 입력값을 그대로 사용한다.
- left는 유지할 점 또는 수강 추천 이유를 정리한다.
- right는 개선할 점 또는 수강 시 고려할 사항을 정리한다.
- 각 목록은 최대 3개 항목으로 작성한다.
- 각 항목의 keyword는 짧은 평가 주제다.
- 각 항목의 text는 근거가 있는 종합 문장이다.
- review_ids에는 해당 문장을 실제로 뒷받침하는 리뷰 ID만 넣는다.
- suggestion은 교수자에게 도움이 되는 개선 방향을 제시한다.
  단, 입력 근거가 없으면 새로운 개선안을 지어내지 않는다.
- categories에는 분석 결과에 실제로 등장한 category만 사용한다.
- headline은 해당 항목과 감성에 맞는 문장만 작성한다.
- groups는 주제별로 묶고 short는 짧게, detail은 구체적으로 작성한다.
- 그룹마다 실제 근거가 된 review_ids를 넣는다.
- 리뷰가 뒷받침하지 않는 일반화나 빈도 표현은 사용하지 않는다.
- 결과는 지정된 JSON 스키마에 맞춘다.
"""

    options = {"reasoning": {"effort": effort}}
    if effort == "none":
        options["temperature"] = 0

    with OpenAI(
        api_key=key,
        timeout=60.0,
        max_retries=0,
    ) as client:
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

def validate_overview(overview: dict, reviews: list[dict]) -> dict:
    """예시 JSON 구조를 검증하고 리뷰 ID와 basis를 정리한다."""
    if not isinstance(overview, dict):
        raise ValueError("overview는 JSON 객체여야 합니다.")

    valid_ids = {
        normalize_id(r["review_id"])
        for r in reviews
        if r.get("review_id") is not None
    }
    category_sentiments = review_category_sentiments(reviews)

    def clean_items(items, category=None, sentiment=None):
        if not isinstance(items, list):
            return []

        cleaned = []

        for item in items:
            if not isinstance(item, dict):
                continue

            ids = item.get("review_ids")
            if not isinstance(ids, list):
                continue

            kept = []
            for value in ids:
                rid = normalize_id(value)
                if rid not in valid_ids:
                    continue

                if category is not None and sentiment is not None:
                    if (category, sentiment) not in category_sentiments.get(
                        rid, set()
                    ):
                        continue

                if rid not in kept:
                    kept.append(rid)

            if not kept:
                continue

            item = dict(item)
            item["review_ids"] = kept
            item["basis"] = len(kept)
            cleaned.append(item)

        cleaned.sort(key=lambda item: item["basis"], reverse=True)
        return cleaned

    # left/right는 category가 아니라 문장 근거 ID를 기준으로 검증한다.
    for side in ("left", "right"):
        overview[side] = clean_items(overview.get(side))

    categories = overview.get("categories")
    if not isinstance(categories, list):
        raise ValueError("overview.categories는 배열이어야 합니다.")

    cleaned_categories = []

    for entry in categories:
        if not isinstance(entry, dict):
            continue

        code = entry.get("category")
        groups = entry.get("groups")

        if not isinstance(code, str) or not isinstance(groups, list):
            continue

        cleaned_groups = []
        for group in groups:
            if not isinstance(group, dict):
                continue

            sentiment = group.get("sentiment")
            if sentiment not in {"positive", "negative", "mixed"}:
                continue

            if not all(
                isinstance(group.get(field), str)
                and group[field].strip()
                for field in ("topic", "short", "detail")
            ):
                continue

            cleaned_groups.extend(
                clean_items([group], category=code, sentiment=sentiment)
            )

        if cleaned_groups:
            cleaned_entry = dict(entry)
            cleaned_entry["groups"] = cleaned_groups
            cleaned_categories.append(cleaned_entry)

    overview["categories"] = cleaned_categories
    overview["basis"] = len(valid_ids)
    return overview


def attach_text(response: dict, rows: list[dict]) -> dict:
    """응답에 원문을 붙이고 overview를 검증한다."""
    text_by_id = {normalize_id(row["id"]): row["text"] for row in rows}

    for review in response["reviews"]:
        review_id = normalize_id(review.get("review_id", ""))
        review["text"] = text_by_id.get(review_id, "")

    if "overview" in response:
        try:
            response["overview"] = validate_overview(
                response["overview"], response["reviews"]
            )
        except (TypeError, ValueError, KeyError) as exc:
            # overview 처리 실패가 기본 분석 결과를 망가뜨리지 않도록 한다.
            print(f"⚠️ overview 검증 실패: {exc}. 기본 분석 결과는 유지합니다.")

    return response



def merge_overviews(responses: list[dict], reviews: list[dict]):
    """여러 학기의 overview를 합치고 리뷰 ID와 basis를 재검증한다."""
    overviews = [
        response["overview"]
        for response in responses
        if isinstance(response.get("overview"), dict)
    ]

    if not overviews:
        return None

    merged_categories = {}

    for overview in overviews:
        for category in overview.get("categories", []):
            if not isinstance(category, dict):
                continue

            code = category.get("category")
            if not isinstance(code, str):
                continue

            target = merged_categories.setdefault(
                code,
                {
                    "category": code,
                    "headline": {},
                    "groups": [],
                },
            )

            for sentiment, headline in category.get("headline", {}).items():
                if isinstance(headline, str) and headline.strip():
                    target["headline"].setdefault(sentiment, headline)

            for group in category.get("groups", []):
                if not isinstance(group, dict):
                    continue

                identity = {
                    key: value
                    for key, value in group.items()
                    if key not in {"review_ids", "basis"}
                }
                identity_key = json.dumps(
                    identity,
                    ensure_ascii=False,
                    sort_keys=True,
                )

                existing = next(
                    (
                        item for item in target["groups"]
                        if item["_identity"] == identity_key
                    ),
                    None,
                )

                if existing is None:
                    existing = {
                        **identity,
                        "review_ids": [],
                        "_identity": identity_key,
                    }
                    target["groups"].append(existing)

                for review_id in group.get("review_ids", []):
                    rid = normalize_id(review_id)
                    if rid not in existing["review_ids"]:
                        existing["review_ids"].append(rid)

    base = dict(overviews[0])
    base["categories"] = []

    for category in merged_categories.values():
        for group in category["groups"]:
            group.pop("_identity", None)

        base["categories"].append(category)

    return validate_overview(base, reviews)



def merge(responses: list[dict]) -> dict:
    """여러 학기 응답을 합치고 카테고리 집계를 다시 계산한다."""
    reviews = [
        review
        for response in responses
        for review in response["reviews"]
    ]

    results = [
        ReviewResult.model_validate(
            {key: value for key, value in review.items() if key != "text"}
        )
        for review in reviews
    ]

    summary = [
        item.model_dump(mode="json")
        for item in summarize_by_category(results)
    ]
    succeeded = sum(
        result.status == ReviewStatus.OK for result in results
    )

    merged_response = {
        "reviews": reviews,
        "summary_by_category": summary,
        "meta": {
            "total_reviews": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
            "model": responses[0]["meta"]["model"],
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # 모든 학기의 overview 그룹을 합산한다.
    try:
        overview = merge_overviews(responses, reviews)
        if overview is not None:
            merged_response["overview"] = overview
    except (TypeError, ValueError, KeyError) as exc:
        print(f"⚠️ 합산 overview 처리 실패: {exc}")

    return merged_response


def save(path: Path, data: dict) -> None:
    """JSON 파일을 UTF-8로 저장한다."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def commit_outputs(staging: Path, output_dir: Path) -> None:
    """생성된 파일을 반영하고, 교체 도중 오류가 나면 기존 파일을 복구한다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    staged_files = sorted(path for path in staging.iterdir() if path.is_file())
    backup_dir = Path(
        tempfile.mkdtemp(prefix=".reference_backup_", dir=output_dir.parent)
    )
    replaced = []
    installed = []

    try:
        # 기존 파일을 백업한 뒤 새 파일을 반영한다.
        for staged in staged_files:
            destination = output_dir / staged.name
            backup = backup_dir / staged.name

            if destination.exists():
                os.replace(destination, backup)
                replaced.append((backup, destination))

            os.replace(staged, destination)
            installed.append(destination)

    except Exception:
        # 새 파일을 제거하고 기존 파일을 되돌린다.
        for destination in reversed(installed):
            if destination.exists():
                destination.unlink()

        for backup, destination in reversed(replaced):
            if backup.exists():
                os.replace(backup, destination)

        raise

    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="리뷰 JSONL 파일 (여러 개 가능)",
    )
    parser.add_argument(
        "--out",
        default="frontend/public/reference",
        help="출력 디렉터리",
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="백엔드 서버 주소",
    )
    args = parser.parse_args()

    # 입력 파일 전체를 읽고 파일 간 ID 중복을 검사한다.
    rows = [
        row
        for filename in args.input
        for row in load_rows(ROOT / filename)
    ]

    id_counts = Counter(row["id"] for row in rows)
    duplicates = sorted(
        key for key, count in id_counts.items() if count > 1
    )

    if duplicates:
        sys.exit(f"입력 파일 사이 id 중복: {duplicates}")

    output_dir = ROOT / args.out
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    # 기존 결과 디렉터리와 같은 부모 경로에 임시 디렉터리를 만든다.
    staging = Path(
        tempfile.mkdtemp(
            prefix=".reference_staging_",
            dir=output_dir.parent,
        )
    )

    try:
        # 서버 상태 확인
        try:
            with urllib.request.urlopen(
                f"{args.server.rstrip('/')}/api/health",
                timeout=10,
            ) as response:
                health = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            sys.exit(f"서버 상태 확인 실패 ({args.server}): {exc}")

        if health.get("mock"):
            print(
                "⚠️ 서버가 USE_MOCK=true 상태입니다. "
                "실제 분석 결과가 필요하면 .env 수정 후 서버를 재시작하세요."
            )

        bundles = defaultdict(list)

        for row in rows:
            bundles[(row["course_id"], row["semester"])].append(row)

        by_course = defaultdict(list)
        index = {}

        for (course_id, semester), items in sorted(bundles.items()):
            if len(items) > MAX_PER_REQUEST:
                sys.exit(
                    f"{course_id} {semester}: {len(items)}개 "
                    f"(한 요청 최대 {MAX_PER_REQUEST}개)"
                )

            print(
                f"분석 중: {course_id} {semester} ({len(items)}개) ...",
                flush=True,
            )

            response = attach_text(
                call_analyze(args.server, items),
                items,
            )

            try:
                response["overview"] = generate_overview(
                    response,
                    audience="instructor",
                )
                print("  → overview 생성 완료")

            except Exception as exc:
                raise RuntimeError(
                    f"{course_id} {semester}: overview 생성 실패. "
                    "기존 결과 파일은 반영하지 않습니다."
                ) from exc

        meta = response["meta"]
            print(
                f"  → 성공 {meta.get('succeeded', '?')} / "
                f"실패 {meta.get('failed', '?')} · "
                f"모델 {meta.get('model', '?')}"
            )

            # 아직 최종 디렉터리가 아니라 임시 디렉터리에 저장한다.
            save(staging / f"{course_id}_{semester}.json", response)
            by_course[course_id].append(response)

            first = items[0]
            professor = index.setdefault(
                first["professor_id"],
                {
                    "id": first["professor_id"],
                    "name": first["professor_name"],
                    "courses": [],
                },
            )

            professor["courses"].append(
                {
                    "course_id": course_id,
                    "course_name": first["course_name"],
                    "section_id": first.get("section_id"),
                    "semester": semester,
                    "review_count": len(items),
                    "file": f"{course_id}_{semester}.json",
                }
            )

        courses = []


            merged["overview"] = generate_overview(
                merged,
                audience="learner",
            )
            total = merged["meta"]["total_reviews"]

            if total > MAX_PER_REQUEST:
                print(
                    f"ℹ️ {course_id} 전체 {total}개: "
                    "전체 학기 합산은 이 스크립트에서 처리합니다."
                )

            save(staging / f"{course_id}_all.json", merged)

            sample = next(
                row for row in rows
                if row["course_id"] == course_id
            )

            courses.append(
                {
                    "course_id": course_id,
                    "course_name": sample["course_name"],
                    "professor_name": sample["professor_name"],
                    "semesters": sorted(
                        {
                            row["semester"]
                            for row in rows
                            if row["course_id"] == course_id
                        }
                    ),
                    "review_count": total,
                    "file": f"{course_id}_all.json",
                }
            )

        save(
            staging / "index.json",
            {
                "school": "가나대학교 (가상)",
                "professors": list(index.values()),
                "courses": courses,
            },
        )

        # 생성된 JSON을 다시 읽어 기본적인 파일 형식을 검증한다.
        for path in staging.glob("*.json"):
            with path.open("r", encoding="utf-8") as file:
                json.load(file)

        # 모든 생성 단계가 성공한 뒤 최종 결과를 반영한다.
        commit_outputs(staging, output_dir)

        print(
            f"완료: {output_dir.relative_to(ROOT)} 에 "
            f"{len(bundles)}개 학기 묶음 + "
            f"{len(courses)}개 과목 합산 + index.json"
        )

    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
