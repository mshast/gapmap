"use client";

import dynamic from "next/dynamic";
import type { Monaco } from "@monaco-editor/react";
import type { editor, Position } from "monaco-editor";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="editor-loading">Opening editor…</div>,
});

function handleBeforeMount(monaco: Monaco) {
  monaco.editor.defineTheme("gapmap-theme", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "", foreground: "e3ede6", background: "162624" },
      { token: "keyword", foreground: "63baa9", fontStyle: "bold" },
      { token: "string", foreground: "e59b7d" },
      { token: "number", foreground: "e3c076" },
      { token: "comment", foreground: "7d988b", fontStyle: "italic" },
      { token: "operator", foreground: "63baa9" },
    ],
    colors: {
      "editor.background": "#162624",
      "editor.foreground": "#e3ede6",
      "editorCursor.foreground": "#63baa9",
      "editor.lineHighlightBackground": "#1d3330",
      "editorLineNumber.foreground": "#4c645b",
      "editorLineNumber.activeForeground": "#96b3a7",
      "editor.selectionBackground": "#234a44",
      "editor.inactiveSelectionBackground": "#1a3833",
    },
  });

  const globalScope = monaco.languages as unknown as { _gapmapSqlRegistered?: boolean };
  if (!globalScope._gapmapSqlRegistered) {
    globalScope._gapmapSqlRegistered = true;
    monaco.languages.registerCompletionItemProvider("sql", {
      provideCompletionItems: (model: editor.ITextModel, position: Position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const schemaItems = [
          { label: "customers", kind: monaco.languages.CompletionItemKind.Class, detail: "Table (id, name, region)", insertText: "customers", range },
          { label: "orders", kind: monaco.languages.CompletionItemKind.Class, detail: "Table (id, customer_id, amount_cents, status, created_at)", insertText: "orders", range },
          { label: "refunds", kind: monaco.languages.CompletionItemKind.Class, detail: "Table (id, order_id, amount_cents)", insertText: "refunds", range },
          { label: "id", kind: monaco.languages.CompletionItemKind.Field, detail: "Column", insertText: "id", range },
          { label: "customer_id", kind: monaco.languages.CompletionItemKind.Field, detail: "Column (FK customers.id)", insertText: "customer_id", range },
          { label: "order_id", kind: monaco.languages.CompletionItemKind.Field, detail: "Column (FK orders.id)", insertText: "order_id", range },
          { label: "amount_cents", kind: monaco.languages.CompletionItemKind.Field, detail: "Column (integer)", insertText: "amount_cents", range },
          { label: "status", kind: monaco.languages.CompletionItemKind.Field, detail: "Column (text)", insertText: "status", range },
          { label: "region", kind: monaco.languages.CompletionItemKind.Field, detail: "Column (text)", insertText: "region", range },
          { label: "gross_revenue_cents", kind: monaco.languages.CompletionItemKind.Variable, detail: "Alias", insertText: "gross_revenue_cents", range },
          { label: "net_revenue_cents", kind: monaco.languages.CompletionItemKind.Variable, detail: "Alias", insertText: "net_revenue_cents", range },
          { label: "COALESCE", kind: monaco.languages.CompletionItemKind.Function, detail: "Function", insertText: "COALESCE(${1:expression}, ${2:fallback})", insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet, range },
          { label: "SUM", kind: monaco.languages.CompletionItemKind.Function, detail: "Aggregate", insertText: "SUM(${1:column})", insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet, range },
        ];

        return { suggestions: schemaItems };
      },
    });
  }
}

export function SqlEditor({
  value,
  onChange,
  label,
  language = "sql",
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  language?: "sql" | "python";
}) {
  return (
    <div className="editor-frame" aria-label={label}>
      <Editor
        height="280px"
        language={language}
        theme="gapmap-theme"
        beforeMount={handleBeforeMount}
        value={value}
        onChange={(next) => onChange(next ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          wordWrap: "on",
          padding: { top: 14, bottom: 14 },
          automaticLayout: true,
          tabSize: language === "python" ? 4 : 2,
          suggestOnTriggerCharacters: true,
        }}
      />
    </div>
  );
}
