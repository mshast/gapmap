import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  ...nextVitals,
  { ignores: [".next-e2e/**", "public/monaco/**", "public/pdf.worker.min.mjs", "test-results/**", "playwright-report/**"] },
];

export default eslintConfig;
