import { useState } from "react";
import { ExtractedView } from "../components/ExtractedView";
import { FileUpload } from "../components/FileUpload";
import { Icon } from "../components/Icon";
import { JsonViewer } from "../components/JsonViewer";
import { Tabs } from "../components/Tabs";
import { mensagemDeErro } from "../services/api";
import { extrairNotaFiscal } from "../services/notaFiscalService";
import type { ExtracaoResponse } from "../types/notaFiscal";

type Aba = "formatada" | "json";

export function NotaFiscalPage() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ExtracaoResponse | null>(null);
  const [aba, setAba] = useState<Aba>("formatada");

  function selecionar(file: File | null) {
    setArquivo(file);
    setErro(null);
    setResultado(null);
  }

  async function extrair() {
    if (!arquivo || processando) return;
    setProcessando(true);
    setErro(null);
    setResultado(null);
    try {
      setResultado(await extrairNotaFiscal(arquivo));
      setAba("formatada");
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setProcessando(false);
    }
  }

  return (
    <div className="page page-narrow">
      <header className="page-header center">
        <h1>Extração de Dados de Nota Fiscal</h1>
        <p>Carregue um PDF da nota fiscal e extraia os dados automaticamente usando IA</p>
      </header>

      <section className="card">
        <h2 className="card-title">Upload do PDF</h2>
        <p className="card-hint">Selecione o arquivo PDF da nota fiscal</p>

        <FileUpload file={arquivo} disabled={processando} onSelect={selecionar} onInvalid={setErro} />

        <button className="btn btn-primary btn-block" disabled={!arquivo || processando} onClick={extrair}>
          {processando ? (
            <>
              <span className="spinner" aria-hidden="true" /> PROCESSANDO...
            </>
          ) : (
            "EXTRAIR DADOS"
          )}
        </button>

        {processando && (
          <p className="card-hint center" role="status">
            A IA está lendo a nota fiscal. Isso pode levar alguns segundos.
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

          {resultado.avisos.length > 0 && (
            <div className="alert alert-warn" role="status">
              <Icon name="alert" />
              <div>
                <strong>Confira estes pontos antes de usar os dados:</strong>
                <ul>
                  {resultado.avisos.map((aviso, i) => (
                    <li key={i}>{aviso}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

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
