import { copyFile, cp, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const source = resolve(root, "../node_modules/pdfjs-dist/legacy/build/pdf.worker.min.mjs");
const destination = resolve(root, "../public/pdf.worker.min.mjs");
await mkdir(dirname(destination), { recursive: true });
await copyFile(source, destination);
await cp(resolve(root, "../node_modules/monaco-editor/min/vs"), resolve(root, "../public/monaco/vs"), { recursive: true });
