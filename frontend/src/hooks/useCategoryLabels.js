import { useEffect, useState } from "react";
import { fetchCategories } from "../api/client.js";
import { CATEGORY_LABEL } from "../constants.js";

// 기본은 프론트 상수, 서버가 켜져 있으면 /api/categories 값으로 덮어씀
export default function useCategoryLabels() {
  const [labels, setLabels] = useState(CATEGORY_LABEL);

  useEffect(() => {
    fetchCategories()
      .then((list) => setLabels(Object.fromEntries(list.map((c) => [c.code, c.label]))))
      .catch(() => {});
  }, []);

  return labels;
}
