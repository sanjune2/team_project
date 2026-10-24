import { CATEGORY_LABEL } from "../constants.js";

// 화면에는 짧은 항목 이름을 씀 (서버 이름의 가운뎃점 "과제량·로드" 등은 디자인 규칙 1번에 걸림)
export default function useCategoryLabels() {
  return CATEGORY_LABEL;
}
