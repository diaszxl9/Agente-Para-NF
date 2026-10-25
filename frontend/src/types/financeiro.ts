export type TipoPessoa = "CLIENTE" | "FORNECEDOR" | "FATURADO";
export type TipoClassificacao = "RECEITA" | "DESPESA";
export type TipoMovimento = "PAGAR" | "RECEBER";
export type Status = "ATIVO" | "INATIVO";

export interface Pessoa {
  id: number;
  tipo: TipoPessoa;
  razao_social: string;
  fantasia: string | null;
  documento: string;
  status: Status;
  data_cadastro: string;
}

export interface PessoaForm {
  razao_social: string;
  fantasia: string | null;
  documento: string;
}

export interface Classificacao {
  id: number;
  tipo: TipoClassificacao;
  descricao: string;
  status: Status;
  data_cadastro: string;
}

export interface PessoaResumo {
  id: number;
  tipo: TipoPessoa;
  razao_social: string;
  documento: string;
  status: Status;
}

export interface Parcela {
  id: number;
  numero: number;
  identificacao: string;
  data_vencimento: string;
  valor: number;
  situacao: "ABERTA" | "QUITADA";
}

export interface Movimento {
  id: number;
  tipo: TipoMovimento;
  pessoa: PessoaResumo;
  faturado: PessoaResumo | null;
  numero_nota: string | null;
  data_emissao: string | null;
  descricao: string;
  valor_total: number;
  status: Status;
  data_cadastro: string;
  classificacoes: { id: number; descricao: string; status: Status }[];
  parcelas: Parcela[];
}

export interface MovimentoForm {
  tipo: TipoMovimento;
  pessoa_id: number;
  faturado_id: number | null;
  numero_nota: string | null;
  data_emissao: string | null;
  descricao: string;
  valor_total: number;
  classificacao_ids: number[];
  parcelas: { data_vencimento: string; valor: number }[];
}

export type AcaoConsulta = "UTILIZAR" | "CRIAR" | "REATIVAR" | "INDISPONIVEL";

export interface ConsultaPessoa {
  entidade: "FORNECEDOR" | "FATURADO";
  nome: string | null;
  documento: string | null;
  existe: boolean;
  id: number | null;
  status: Status | null;
  acao: AcaoConsulta;
}

export interface ConsultaClassificacao {
  entidade: "DESPESA";
  descricao: string;
  existe: boolean;
  id: number | null;
  status: Status | null;
  acao: AcaoConsulta;
}

export interface AnaliseResponse {
  fornecedor: ConsultaPessoa;
  faturado: ConsultaPessoa | null;
  despesas: ConsultaClassificacao[];
  pendencias: string[];
}

export interface LancamentoResponse {
  mensagem: string;
  acoes: string[];
  movimento: Movimento;
}
