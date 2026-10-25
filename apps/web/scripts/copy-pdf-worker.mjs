import { copyFile, mkdir, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const source = resolve(root, "../node_modules/pdfjs-dist/legacy/build/pdf.worker.min.mjs");
const destination = resolve(root, "../public/pdf.worker.min.mjs");
await mkdir(dirname(destination), { recursive: true });
try {
  await copyFile(source, destination);
} catch (error) {
  const existing = await stat(destination).catch(() => null);
  if (!existing) throw error;
}
