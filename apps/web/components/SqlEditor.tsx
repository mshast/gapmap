"use client";

import dynamic from "next/dynamic";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="editor-loading">Opening SQL editor…</div>,
});

export function SqlEditor({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
}) {
  return (
    <div className="editor-frame" aria-label={label}>
      <Editor
        height="280px"
        language="sql"
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
          tabSize: 2,
          suggestOnTriggerCharacters: true,
        }}
      />
    </div>
  );
}