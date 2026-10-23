// 백엔드 호출 함수. 항상 상대 경로 /api 사용 (개발: Vite 프록시, 배포: Nginx)

const SERVER_DOWN = "서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.";

async function request(path, options) {
  let res;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    // 네트워크 오류 (서버 꺼짐 등): 브라우저 원문("Failed to fetch") 대신 안내 문구
    throw new Error(SERVER_DOWN);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // 합의한 에러 형식: { error: { code, message, details } } → 사용자용 message만 표시
    if (body?.error?.message) throw new Error(body.error.message);
    // 형식에 맞는 에러 본문이 없으면 서버 내부 문구를 보여 주지 않음
    throw new Error(res.status >= 500 ? SERVER_DOWN : `요청을 처리하지 못했어요. (${res.status})`);
  }
  if (body === null) throw new Error(SERVER_DOWN);
  return body;
}

export function fetchCategories() {
  return request("/api/categories");
}

// reviews: [{ id, text, semester? }]
export function analyzeReviews(reviews) {
  return request("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ reviews }),
  });
}