"use client";

import dynamic from "next/dynamic";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="editor-loading">Opening editor…</div>,
});

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
        theme="vs-dark"
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