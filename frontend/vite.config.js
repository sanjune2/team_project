import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 개발 중 /api 요청을 FastAPI(8000)로 전달 → CORS 설정 불필요
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
