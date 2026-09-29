import { useEffect, useState } from "react";
import { ExtractedView } from "../components/ExtractedView";
import { FileUpload, MAX_UPLOAD_MB_PADRAO } from "../components/FileUpload";
import { GeminiApiKey } from "../components/GeminiApiKey";
import { Icon } from "../components/Icon";
import { JsonViewer } from "../components/JsonViewer";
import { Tabs } from "../components/Tabs";
import { ApiError, mensagemDeErro } from "../services/api";
import { CODIGO_CHAVE_RECUSADA, extrairNotaFiscal, obterLimites } from "../services/notaFiscalService";
import type { ExtracaoResponse } from "../types/notaFiscal";

type Aba = "formatada" | "json";

export function NotaFiscalPage() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ExtracaoResponse | null>(null);
  const [aba, setAba] = useState<Aba>("formatada");
  const [geminiApiKey, setGeminiApiKey] = useState<string | null>(null);
  // Incrementado quando o Gemini recusa a chave: recria o campo da chave, que precisa ser validada de novo.
  const [versaoChave, setVersaoChave] = useState(0);
  const [maxUploadMb, setMaxUploadMb] = useState(MAX_UPLOAD_MB_PADRAO);

  useEffect(() => {
    let ativo = true;
    // Se falhar, mantém o padrão: o backend valida o tamanho de qualquer forma.
    obterLimites()
      .then((l) => ativo && setMaxUploadMb(l.max_upload_mb))
      .catch(() => undefined);
    return () => {
      ativo = false;
    };
  }, []);

  function selecionar(file: File | null) {
    setArquivo(file);
    setErro(null);
    setResultado(null);
  }

  async function extrair() {
    if (!arquivo || !geminiApiKey || processando) return;
    setProcessando(true);
    setErro(null);
    setResultado(null);
    try {
      setResultado(await extrairNotaFiscal(arquivo, geminiApiKey));
      setAba("formatada");
    } catch (e) {
      setErro(mensagemDeErro(e));
      if (e instanceof ApiError && e.codigo === CODIGO_CHAVE_RECUSADA) {
        setGeminiApiKey(null);
        setVersaoChave((v) => v + 1);
      }
    } finally {
      setProcessando(false);
    }
  }

  return (
    <div className="page page-narrow">
      <header className="page-header center">
        <h1>Extração de Dados de Nota Fiscal</h1>
      </header>

      <GeminiApiKey key={versaoChave} disabled={processando} onChange={setGeminiApiKey} />

      <section className="card">
        <h2 className="card-title">Upload do PDF</h2>
        <p className="card-hint">Selecione o arquivo PDF da nota fiscal</p>

        <FileUpload file={arquivo} maxMb={maxUploadMb} disabled={processando} onSelect={selecionar} onInvalid={setErro} />

        <button
          className="btn btn-primary btn-block"
          disabled={!arquivo || !geminiApiKey || processando}
          onClick={extrair}
        >
          {processando ? (
            <>
              <span className="spinner" aria-hidden="true" /> PROCESSANDO...
            </>
          ) : (
            "EXTRAIR DADOS"
          )}
        </button>

        {!geminiApiKey && (
          <p className="card-hint center">Valide a Gemini API Key para habilitar a extração.</p>
        )}

        {processando && (
          <p className="card-hint center" role="status">
            Lendo a nota fiscal. Isso pode levar alguns segundos.
          </p>
        )}

        {erro && (
          <div className="alert alert-error" role="alert">
            <Icon name="alert" />
            <span>{erro}</span>
          </div>
        )}
      </section>

      {resultado && (
        <section className="card result-card">
          <div className="result-head">
            <h2 className="card-title">Dados Extraídos</h2>
            <span className="muted small">
              {resultado.arquivo.nome} · modelo {resultado.modelo}
            </span>
          </div>

          <Tabs
            tabs={[
              { id: "formatada", label: "Visualização Formatada" },
              { id: "json", label: "JSON" },
            ]}
            active={aba}
            onChange={setAba}
          />

          {aba === "formatada" ? <ExtractedView dados={resultado.dados} /> : <JsonViewer value={resultado.dados} />}
        </section>
      )}
    </div>
  );
}
