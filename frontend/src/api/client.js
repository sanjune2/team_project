// 백엔드 호출 함수. 항상 상대 경로 /api 사용 (개발: Vite 프록시, 배포: Nginx)

async function request(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // 합의한 에러 형식: { error: { code, message, details } }
    const message = body?.error?.message ?? `요청 실패 (${res.status})`;
    throw new Error(message);
  }
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
