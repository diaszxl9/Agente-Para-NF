import { useState } from "react";
import { mensagemDeErro } from "../services/api";
import { validarGeminiApiKey } from "../services/geminiService";
import { Icon } from "./Icon";

type Status = { tipo: "valida" | "invalida" | "erro"; mensagem: string } | null;

interface GeminiApiKeyProps {
  disabled?: boolean;
  // Chamado com a chave depois de validada, ou null quando ela muda e precisa ser validada de novo.
  onChange: (apiKeyValida: string | null) => void;
}

// A chave fica só na memória desta tela (estado do React): não vai para localStorage/sessionStorage.
export function GeminiApiKey({ disabled, onChange }: GeminiApiKeyProps) {
  const [apiKey, setApiKey] = useState("");
  const [validando, setValidando] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  function alterar(valor: string) {
    setApiKey(valor);
    setStatus(null);
    onChange(null);
  }

  async function validar() {
    const chave = apiKey.trim();
    if (!chave || validando) return;
    setValidando(true);
    setStatus(null);
    try {
      const r = await validarGeminiApiKey(chave);
      setStatus({ tipo: r.valida ? "valida" : "invalida", mensagem: r.mensagem });
      onChange(r.valida ? chave : null);
    } catch (e) {
      setStatus({ tipo: "erro", mensagem: mensagemDeErro(e) });
      onChange(null);
    } finally {
      setValidando(false);
    }
  }

  return (
    <section className="card">
      <h2 className="card-title">Gemini API Key</h2>
      <p className="card-hint">Informe e valide sua chave para habilitar a extração</p>

      <form
        className="key-row"
        onSubmit={(e) => {
          e.preventDefault();
          validar();
        }}
      >
        <input
          className="input"
          type="password"
          aria-label="Gemini API Key"
          placeholder="Cole aqui a sua Gemini API Key"
          autoComplete="off"
          spellCheck={false}
          value={apiKey}
          disabled={disabled || validando}
          onChange={(e) => alterar(e.target.value)}
        />
        <button type="submit" className="btn btn-secondary" disabled={disabled || validando || !apiKey.trim()}>
          {validando ? (
            <>
              <span className="spinner spinner-dark" aria-hidden="true" /> Validando...
            </>
          ) : (
            "Validar API Key"
          )}
        </button>
      </form>

      {status && (
        <div
          className={`alert ${status.tipo === "valida" ? "alert-success" : "alert-error"}`}
          role={status.tipo === "valida" ? "status" : "alert"}
        >
          <Icon name={status.tipo === "valida" ? "check" : "alert"} />
          <span>{status.mensagem}</span>
        </div>
      )}
    </section>
  );
}
