// 포털 상단: 학교명 + 예시 로그인 전환 (교직원 / 학생)
const ROLES = [
  { mode: "instructor", label: "교직원" },
  { mode: "learner", label: "학생" },
];

export default function PortalHeader({ school, mode, onModeChange }) {
  return (
    <header className="pt-header">
      <div className="pt-header-inner">
        <span className="pt-school">{school}</span>
        <div className="pt-login" role="group" aria-label="예시 로그인">
          <span className="pt-login-label">예시 로그인</span>
          {ROLES.map((r) => (
            <button
              key={r.mode}
              type="button"
              className="pt-role"
              aria-pressed={mode === r.mode}
              onClick={() => onModeChange(r.mode)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
