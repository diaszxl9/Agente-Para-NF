import type {
  AnaliseResponse,
  Classificacao,
  LancamentoResponse,
  Movimento,
  MovimentoForm,
  Pessoa,
  PessoaForm,
  Status,
  TipoClassificacao,
  TipoMovimento,
  TipoPessoa,
} from "../types/financeiro";
import type { NotaFiscalExtraida } from "../types/notaFiscal";
import { request } from "./api";

// Enviado pelo backend quando o lançamento depende de um cadastro INATIVO e a reativação não foi confirmada.
export const CODIGO_CADASTRO_INATIVO = "cadastro_inativo";

function json(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

function query(params: Record<string, string | undefined>): string {
  const qs = new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => !!e[1]));
  return qs.toString() ? `?${qs}` : "";
}

// Pessoas (fornecedor, cliente, faturado). A exclusão é lógica: inativar/reativar.
export const listarPessoas = (tipo: TipoPessoa, status?: Status, busca?: string) =>
  request<Pessoa[]>(`/api/pessoas${query({ tipo, status, busca })}`);
export const criarPessoa = (tipo: TipoPessoa, dados: PessoaForm) =>
  request<Pessoa>("/api/pessoas", json("POST", { tipo, ...dados }));
export const atualizarPessoa = (id: number, dados: PessoaForm) =>
  request<Pessoa>(`/api/pessoas/${id}`, json("PUT", dados));
export const alterarStatusPessoa = (id: number, ativo: boolean) =>
  request<Pessoa>(`/api/pessoas/${id}/${ativo ? "reativar" : "inativar"}`, json("POST"));

// Classificações (tipos de receita e despesa).
export const listarClassificacoes = (tipo: TipoClassificacao, status?: Status, busca?: string) =>
  request<Classificacao[]>(`/api/classificacoes${query({ tipo, status, busca })}`);
export const criarClassificacao = (tipo: TipoClassificacao, descricao: string) =>
  request<Classificacao>("/api/classificacoes", json("POST", { tipo, descricao }));
export const atualizarClassificacao = (id: number, descricao: string) =>
  request<Classificacao>(`/api/classificacoes/${id}`, json("PUT", { descricao }));
export const alterarStatusClassificacao = (id: number, ativo: boolean) =>
  request<Classificacao>(`/api/classificacoes/${id}/${ativo ? "reativar" : "inativar"}`, json("POST"));

// Contas a pagar/receber e parcelas.
export const listarContas = (tipo: TipoMovimento, status?: Status, busca?: string) =>
  request<Movimento[]>(`/api/contas${query({ tipo, status, busca })}`);
export const criarConta = (dados: MovimentoForm) => request<Movimento>("/api/contas", json("POST", dados));
// O tipo (pagar/receber) não muda na edição.
export const atualizarConta = (id: number, dados: Omit<MovimentoForm, "tipo">) =>
  request<Movimento>(`/api/contas/${id}`, json("PUT", dados));
export const alterarStatusConta = (id: number, ativo: boolean) =>
  request<Movimento>(`/api/contas/${id}/${ativo ? "reativar" : "inativar"}`, json("POST"));
export const alterarSituacaoParcela = (id: number, quitar: boolean) =>
  request<Movimento>(`/api/contas/parcelas/${id}/${quitar ? "quitar" : "reabrir"}`, json("POST"));

// Segunda etapa da nota: consulta ao banco e lançamento.
export const analisarNota = (dados: NotaFiscalExtraida) =>
  request<AnaliseResponse>("/api/lancamentos/analisar", json("POST", dados));
export const lancarNota = (dados: NotaFiscalExtraida, reativarInativos: boolean) =>
  request<LancamentoResponse>("/api/lancamentos", json("POST", { dados, reativar_inativos: reativarInativos }));
