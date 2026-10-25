import { useEffect, useState } from "react";
import { ApiError, mensagemDeErro } from "../services/api";
import { CODIGO_CADASTRO_INATIVO, analisarNota, lancarNota } from "../services/financeiroService";
import type { AcaoConsulta, AnaliseResponse, LancamentoResponse, Status } from "../types/financeiro";
import type { NotaFiscalExtraida } from "../types/notaFiscal";
import { formatCurrency } from "../utils/format";
import { Icon } from "./Icon";

const ACOES: Record<AcaoConsulta, string> = {
  UTILIZAR: "Será utilizado o cadastro existente.",
  CRIAR: "Será cadastrado automaticamente no lançamento.",
  REATIVAR: "Cadastro INATIVO: será reativado se você confirmar.",
  INDISPONIVEL: "Dados insuficientes para cadastrar automaticamente.",
};

interface ResultadoProps {
  entidade: string;
  titulo: string | null;
  detalhe?: string | null;
  existe: boolean;
  id: number | null;
  status: Status | null;
  acao: AcaoConsulta;
}

function ResultadoConsulta({ entidade, titulo, detalhe, existe, id, status, acao }: ResultadoProps) {
  const inativo = existe && status === "INATIVO";
  const classe = !existe ? "nao-existe" : inativo ? "inativo" : "existe";
  return (
    <div className={`consulta ${classe}`}>
      <span className="consulta-entidade">{entidade}</span>
      <strong className="consulta-nome">{titulo ?? "Não informado"}</strong>
      {detalhe && <span className="consulta-detalhe">{detalhe}</span>}
      <span className={`consulta-resultado ${classe}`}>
        <Icon name={existe ? "check" : "x"} size={16} />
        {existe ? `EXISTE — ID: ${id}${inativo ? " (INATIVO)" : ""}` : "NÃO EXISTE"}
      </span>
      <span className="consulta-acao">{ACOES[acao]}</span>
    </div>
  );
}

export function LancamentoNota({ dados }: { dados: NotaFiscalExtraida }) {
  // Cópia editável: permite completar o que a extração não encontrou (ex.: vencimento, classificação).
  const [nota, setNota] = useState(dados);
  const [analise, setAnalise] = useState<AnaliseResponse | null>(null);
  const [analisando, setAnalisando] = useState(false);
  const [reativar, setReativar] = useState(false);
  const [lancando, setLancando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<LancamentoResponse | null>(null);
  const [novaDespesa, setNovaDespesa] = useState("");

  useEffect(() => {
    setNota(dados);
    setResultado(null);
    setReativar(false);
  }, [dados]);

  // Consulta o banco sempre que os dados mudam (com uma pequena espera enquanto o usuário digita).
  useEffect(() => {
    if (resultado) return;
    let ativo = true;
    const timer = setTimeout(async () => {
      setAnalisando(true);
      setErro(null);
      try {
        const r = await analisarNota(nota);
        if (ativo) setAnalise(r);
      } catch (e) {
        if (ativo) setErro(mensagemDeErro(e));
      } finally {
        if (ativo) setAnalisando(false);
      }
    }, 350);
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [nota, resultado]);

  function alterarVencimento(numero: number, data: string) {
    setNota((n) => ({
      ...n,
      parcelas: n.parcelas.map((p) => (p.numero === numero ? { ...p, data_vencimento: data || null } : p)),
    }));
  }

  async function lancar() {
    if (!analise || lancando) return;
    setLancando(true);
    setErro(null);
    try {
      setResultado(await lancarNota(nota, reativar));
    } catch (e) {
      setErro(mensagemDeErro(e));
      if (e instanceof ApiError && e.codigo === CODIGO_CADASTRO_INATIVO) setReativar(false);
    } finally {
      setLancando(false);
    }
  }

  const inativos = analise
    ? [analise.fornecedor, analise.faturado, ...analise.despesas].filter((c) => c?.acao === "REATIVAR").length
    : 0;
  const podeLancar = !!analise && analise.pendencias.length === 0 && (inativos === 0 || reativar) && !analisando;

  return (
    <section className="card">
      <div className="result-head">
        <h2 className="card-title">Análise e Lançamento</h2>
        <span className="muted small">Consulta ao banco de dados · conta a pagar</span>
      </div>

      <ol className="steps">
        <li className="done">Extração</li>
        <li className={analise ? "done" : "current"}>Consulta</li>
        <li className={resultado ? "done" : analise ? "current" : undefined}>Lançamento</li>
      </ol>

      {analisando && !analise && (
        <p className="card-hint center" role="status">
          <span className="spinner spinner-dark inline" aria-hidden="true" /> Consultando fornecedor, faturado e classificações...
        </p>
      )}

      {analise && (
        <div className="consultas">
          <ResultadoConsulta
            {...analise.fornecedor}
            entidade="Fornecedor"
            titulo={analise.fornecedor.nome}
            detalhe={analise.fornecedor.documento ? `CNPJ/CPF: ${analise.fornecedor.documento}` : "CNPJ/CPF não informado"}
          />
          {analise.faturado ? (
            <ResultadoConsulta
              {...analise.faturado}
              entidade="Faturado"
              titulo={analise.faturado.nome}
              detalhe={analise.faturado.documento ? `CPF/CNPJ: ${analise.faturado.documento}` : "CPF/CNPJ não informado"}
            />
          ) : (
            <div className="consulta vazio">
              <span className="consulta-entidade">Faturado</span>
              <span className="muted">Não identificado na nota (opcional).</span>
            </div>
          )}
          {analise.despesas.map((d) => (
            <ResultadoConsulta key={d.descricao} {...d} entidade="Despesa" titulo={d.descricao} />
          ))}
        </div>
      )}

      {analise && !resultado && (
        <>
          <div className="data-section">
            <h3>Parcelas a lançar</h3>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Parcela</th>
                    <th>Vencimento</th>
                    <th className="num">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {nota.parcelas.map((p) => (
                    <tr key={p.numero}>
                      <td>{p.numero}/{nota.parcelas.length}</td>
                      <td>
                        <input type="date" className={`input input-sm${p.data_vencimento ? "" : " input-invalid"}`}
                          aria-label={`Vencimento da parcela ${p.numero}`} value={p.data_vencimento ?? ""}
                          disabled={lancando} onChange={(e) => alterarVencimento(p.numero, e.target.value)} />
                      </td>
                      <td className="num">{formatCurrency(p.valor) ?? <span className="muted">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {nota.despesas.length === 0 && (
            <div className="form-field">
              <label htmlFor="nova-despesa">Classificação da despesa</label>
              <div className="key-row">
                <input id="nova-despesa" className="input" maxLength={160} placeholder="Ex.: MANUTENÇÃO E OPERAÇÃO"
                  value={novaDespesa} onChange={(e) => setNovaDespesa(e.target.value)} />
                <button type="button" className="btn btn-secondary" disabled={!novaDespesa.trim()}
                  onClick={() => setNota((n) => ({ ...n, despesas: [{ categoria: novaDespesa.trim(), subcategoria: null }] }))}>
                  Aplicar
                </button>
              </div>
            </div>
          )}

          {analise.pendencias.length > 0 && (
            <div className="alert alert-warning" role="alert">
              <Icon name="alert" />
              <div>
                <strong>Corrija antes de lançar:</strong>
                <ul className="lista-pendencias">
                  {analise.pendencias.map((p) => <li key={p}>{p}</li>)}
                </ul>
              </div>
            </div>
          )}

          {inativos > 0 && (
            <label className="check-row">
              <input type="checkbox" checked={reativar} onChange={(e) => setReativar(e.target.checked)} />
              Reativar {inativos === 1 ? "o cadastro inativo encontrado" : `os ${inativos} cadastros inativos encontrados`} e
              utilizá-{inativos === 1 ? "lo" : "los"} neste lançamento (nenhum registro duplicado será criado).
            </label>
          )}

          <button type="button" className="btn btn-primary btn-block" disabled={!podeLancar || lancando} onClick={lancar}>
            {lancando ? <><span className="spinner" aria-hidden="true" /> LANÇANDO...</> : "LANÇAR REGISTRO"}
          </button>
        </>
      )}

      {erro && (
        <div className="alert alert-error" role="alert">
          <Icon name="alert" />
          <span>{erro}</span>
        </div>
      )}

      {resultado && (
        <div className="alert alert-success sucesso-lancamento" role="status">
          <Icon name="check" />
          <div>
            <strong>{resultado.mensagem}</strong>
            <ul className="lista-pendencias">
              {resultado.acoes.map((a) => <li key={a}>{a}</li>)}
            </ul>
            <span className="small">
              Movimento ID {resultado.movimento.id} · {formatCurrency(resultado.movimento.valor_total)} · disponível em
              Contas a Pagar.
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
