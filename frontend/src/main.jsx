import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"; // 글꼴: 필요한 글자만 내려받는 가변 Pretendard
import "./styles/tokens.css";
import "./App.css";
import "./styles/theme.css"; // 정보 블록과 위계 (마지막에 불러와 덮어씀)

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
