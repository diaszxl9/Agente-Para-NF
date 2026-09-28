export interface Fornecedor {
  razao_social: string | null;
  fantasia: string | null;
  cnpj: string | null;
}

export interface Faturado {
  nome_completo: string | null;
  cpf: string | null;
}

export interface NotaFiscalInfo {
  numero: string | null;
  data_emissao: string | null;
}

export interface Item {
  descricao: string;
  quantidade: number | null;
}

export interface Parcela {
  numero: number;
  data_vencimento: string | null;
  valor: number | null;
}

export interface Despesa {
  categoria: string | null;
  subcategoria: string | null;
}

export interface NotaFiscalExtraida {
  fornecedor: Fornecedor;
  faturado: Faturado;
  nota_fiscal: NotaFiscalInfo;
  itens: Item[];
  parcelas: Parcela[];
  valor_total: number | null;
  despesas: Despesa[];
}

export interface ExtracaoResponse {
  dados: NotaFiscalExtraida;
  arquivo: { nome: string; tamanho_bytes: number };
  modelo: string;
}
