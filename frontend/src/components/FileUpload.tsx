import { useRef, useState } from "react";
import { formatBytes } from "../utils/format";
import { Icon } from "./Icon";

export const MAX_UPLOAD_MB = 10;

interface FileUploadProps {
  file: File | null;
  disabled?: boolean;
  onSelect: (file: File | null) => void;
  onInvalid: (message: string) => void;
}

function validar(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".pdf")) return "Selecione um arquivo no formato PDF.";
  if (file.size === 0) return "O arquivo selecionado está vazio.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `O arquivo excede o limite de ${MAX_UPLOAD_MB} MB.`;
  return null;
}

export function FileUpload({ file, disabled, onSelect, onInvalid }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function aceitar(candidate: File | undefined) {
    if (!candidate) return;
    const erro = validar(candidate);
    if (erro) {
      onInvalid(erro);
      return;
    }
    onSelect(candidate);
  }

  function remover() {
    if (inputRef.current) inputRef.current.value = "";
    onSelect(null);
  }

  return (
    <div>
      <input
        ref={inputRef}
        id="arquivo-pdf"
        type="file"
        accept=".pdf,application/pdf"
        hidden
        disabled={disabled}
        onChange={(e) => {
          aceitar(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {!file ? (
        <div
          className={`dropzone${dragging ? " dragging" : ""}${disabled ? " disabled" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (!disabled) aceitar(e.dataTransfer.files?.[0]);
          }}
        >
          <Icon name="upload" size={28} />
          <p>Arraste o PDF aqui ou</p>
          <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => inputRef.current?.click()}>
            Escolher arquivo
          </button>
          <small>Somente .pdf · até {MAX_UPLOAD_MB} MB</small>
        </div>
      ) : (
        <div className="file-chip">
          <span className="file-chip-icon">
            <Icon name="file" size={22} />
          </span>
          <div className="file-chip-info">
            <strong title={file.name}>{file.name}</strong>
            <span>{formatBytes(file.size)}</span>
          </div>
          <button type="button" className="btn btn-ghost" disabled={disabled} onClick={() => inputRef.current?.click()}>
            Trocar
          </button>
          <button
            type="button"
            className="icon-btn"
            disabled={disabled}
            onClick={remover}
            aria-label="Remover arquivo"
            title="Remover arquivo"
          >
            <Icon name="x" />
          </button>
        </div>
      )}
    </div>
  );
}
