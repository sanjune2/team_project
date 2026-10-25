"""레퍼런스(가상 고객사) 화면용 분석 결과 JSON 만들기.

사용법 (저장소 루트에서, 백엔드 서버를 먼저 켠 상태):
    uvicorn backend.main:app --port 8000          # 다른 터미널, .env에 USE_MOCK=false
    python scripts/build_reference_data.py --input data/reference/reviews_p01.jsonl data/reference/reviews_p02.jsonl

하는 일
1. 입력 JSONL을 (과목, 학기) 묶음으로 나눠 /api/analyze 를 묶음마다 1번 호출 → 교수자 화면용
2. 같은 과목의 여러 학기 결과를 합쳐 집계만 다시 계산 (LLM 재호출 없음) → 학습자 화면용
3. 화면에서 학기·과목 목록을 만들 index.json 저장

출력: frontend/public/reference/
    index.json                    교수·과목·학기 목록
    {course_id}_{semester}.json   교수자용 (한 학기)
    {course_id}_all.json          학습자용 (전체 학기 합산)
각 파일은 /api/analyze 응답과 같은 구조이고, 화면에서 원문을 보여 주도록 reviews[*].text 만 추가합니다.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.postprocess import summarize_by_category  # noqa: E402
from backend.schemas import ReviewResult, ReviewStatus  # noqa: E402

REQUIRED = ["id", "text", "professor_id", "professor_name", "course_id", "course_name", "semester"]
MAX_PER_REQUEST = 50


def load_rows(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = [k for k in REQUIRED if not str(row.get(k, "")).strip()]
        if missing:
            sys.exit(f"{path.name} {n}번째 줄: 빠진 필드 {missing}")
        if len(row["text"]) > 3000:
            sys.exit(f"{path.name} {n}번째 줄: 3000자 초과 ({len(row['text'])}자)")
        rows.append(row)
    ids = [r["id"] for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit(f"id 중복: {sorted(dup)}")
    return rows


def call_analyze(server: str, reviews: list[dict]) -> dict:
    body = json.dumps(
        {"reviews": [{"id": r["id"], "text": r["text"], "semester": r["semester"]} for r in reviews]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{server}/api/analyze", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.URLError as e:
        sys.exit(f"서버 호출 실패 ({server}): {e}. 백엔드 서버가 켜져 있는지 확인하세요.")


def attach_text(response: dict, rows: list[dict]) -> dict:
    text_by_id = {r["id"]: r["text"] for r in rows}
    for review in response["reviews"]:
        review["text"] = text_by_id.get(review["review_id"], "")
    return response


def merge(responses: list[dict]) -> dict:
    """여러 학기 응답을 합치고 집계만 다시 계산 (summarize_by_category 재사용)."""
    reviews = [r for resp in responses for r in resp["reviews"]]
    results = [ReviewResult.model_validate({k: v for k, v in r.items() if k != "text"}) for r in reviews]
    summary = [s.model_dump(mode="json") for s in summarize_by_category(results)]
    succeeded = sum(r.status == ReviewStatus.OK for r in results)
    return {
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


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", nargs="+", required=True, help="리뷰 JSONL 파일 (여러 개 가능)")
    p.add_argument("--out", default="frontend/public/reference")
    p.add_argument("--server", default="http://localhost:8000")
    args = p.parse_args()

    rows = [row for f in args.input for row in load_rows(ROOT / f)]
    ids = [r["id"] for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit(f"파일 사이 id 중복: {sorted(dup)}")
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    # 서버가 실제 LLM 모드인지 먼저 확인 (mock 결과로 화면을 만들지 않도록)
    try:
        with urllib.request.urlopen(f"{args.server}/api/health", timeout=10) as res:
            health = json.loads(res.read())
    except urllib.error.URLError as e:
        sys.exit(f"서버에 연결할 수 없습니다 ({args.server}): {e}")
    if health.get("mock"):
        print("⚠️  서버가 USE_MOCK=true 상태입니다. mock 결과로 저장됩니다. (실제 분석은 .env 수정 후 서버 재시작)")

    bundles: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        bundles[(r["course_id"], r["semester"])].append(r)

    by_course: dict[str, list[dict]] = defaultdict(list)
    index: dict[str, dict] = {}
    for (course_id, semester), items in sorted(bundles.items()):
        if len(items) > MAX_PER_REQUEST:
            sys.exit(f"{course_id} {semester}: {len(items)}개 (한 묶음 최대 {MAX_PER_REQUEST}개)")
        print(f"분석 중: {course_id} {semester} ({len(items)}개) ...", flush=True)
        resp = attach_text(call_analyze(args.server, items), items)
        m = resp["meta"]
        print(f"  → 성공 {m['succeeded']} / 실패 {m['failed']} · 모델 {m['model']}")
        save(out / f"{course_id}_{semester}.json", resp)
        by_course[course_id].append(resp)

        first = items[0]
        prof = index.setdefault(first["professor_id"], {"id": first["professor_id"], "name": first["professor_name"], "courses": []})
        prof["courses"].append({
            "course_id": course_id,
            "course_name": first["course_name"],
            "section_id": first.get("section_id"),
            "semester": semester,
            "review_count": len(items),
            "file": f"{course_id}_{semester}.json",
        })

    courses = []
    for course_id, responses in sorted(by_course.items()):
        merged = merge(responses)
        total = merged["meta"]["total_reviews"]
        if total > MAX_PER_REQUEST:
            print(f"  ℹ️  {course_id} 전체 {total}개: 실제 API는 한 번에 {MAX_PER_REQUEST}개까지라 합산은 이 스크립트에서만 가능")
        save(out / f"{course_id}_all.json", merged)
        sample = next(r for r in rows if r["course_id"] == course_id)
        courses.append({
            "course_id": course_id,
            "course_name": sample["course_name"],
            "professor_name": sample["professor_name"],
            "semesters": sorted({r["semester"] for r in rows if r["course_id"] == course_id}),
            "review_count": total,
            "file": f"{course_id}_all.json",
        })

    save(out / "index.json", {
        "school": "가나대학교 (가상)",
        "professors": list(index.values()),
        "courses": courses,
    })
    print(f"완료: {out.relative_to(ROOT)} 에 {len(bundles)}개 학기 묶음 + {len(courses)}개 과목 합산 + index.json")


if __name__ == "__main__":
    main()
