import { Fragment, useState, type ReactNode } from "react";
import { Icon } from "./Icon";

const TOKEN = /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g;

function highlight(line: string) {
  const parts: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const match of line.matchAll(TOKEN)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(line.slice(last, index));
    const [full, str, colon, keyword, num] = match;
    if (str !== undefined && colon) {
      parts.push(
        <Fragment key={key++}>
          <span className="tok-key">{str}</span>
          {colon}
        </Fragment>,
      );
    } else if (str !== undefined) {
      parts.push(<span key={key++} className="tok-str">{str}</span>);
    } else if (keyword !== undefined) {
      parts.push(<span key={key++} className="tok-kw">{keyword}</span>);
    } else if (num !== undefined) {
      parts.push(<span key={key++} className="tok-num">{num}</span>);
    }
    last = index + full.length;
  }
  if (last < line.length) parts.push(line.slice(last));
  return parts;
}

export function JsonViewer({ value }: { value: unknown }) {
  const [status, setStatus] = useState<"idle" | "copied" | "error">("idle");
  const text = JSON.stringify(value, null, 2);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus("error");
    }
    setTimeout(() => setStatus("idle"), 2000);
  }

  return (
    <div className="code-card">
      <div className="code-header">
        <span>Dados em JSON</span>
        <button className="code-copy" onClick={copiar}>
          <Icon name={status === "copied" ? "check" : "copy"} size={15} />
          {status === "copied" ? "Copiado!" : status === "error" ? "Falha ao copiar" : "Copiar JSON"}
        </button>
      </div>
      <pre className="code-body">
        <code>
          {text.split("\n").map((line, i) => (
            <div className="code-line" key={i}>
              <span className="code-ln">{i + 1}</span>
              <span>{highlight(line)}</span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}
