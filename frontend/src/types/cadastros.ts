export interface CadastroBase {
  id: number;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

export type CadastroRegistro = CadastroBase & Record<string, string | number | boolean | null>;

export type StatusFiltro = "ativos" | "inativos" | "todos";

export interface CampoConfig {
  name: string;
  label: string;
  required?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export interface CadastroConfig {
  titulo: string;
  singular: string;
  subtitulo: string;
  endpoint: string;
  campos: CampoConfig[];
}

export interface DashboardResumo {
  fornecedores: number;
  clientes: number;
  contas_pagar: number;
  contas_receber: number;
}
