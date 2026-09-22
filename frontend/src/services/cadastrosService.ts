import type { CadastroRegistro, DashboardResumo, StatusFiltro } from "../types/cadastros";
import { jsonInit, request } from "./api";

export function listar(endpoint: string, status: StatusFiltro, q: string): Promise<CadastroRegistro[]> {
  const params = new URLSearchParams({ status, limit: "500" });
  if (q.trim()) params.set("q", q.trim());
  return request<CadastroRegistro[]>(`/api/${endpoint}?${params}`);
}

export function criar(endpoint: string, payload: Record<string, unknown>): Promise<CadastroRegistro> {
  return request<CadastroRegistro>(`/api/${endpoint}`, jsonInit("POST", payload));
}

export function atualizar(endpoint: string, id: number, payload: Record<string, unknown>): Promise<CadastroRegistro> {
  return request<CadastroRegistro>(`/api/${endpoint}/${id}`, jsonInit("PUT", payload));
}

export function alterarSituacao(endpoint: string, id: number, ativar: boolean): Promise<CadastroRegistro> {
  return request<CadastroRegistro>(`/api/${endpoint}/${id}/${ativar ? "reativar" : "inativar"}`, jsonInit("PATCH"));
}

export function carregarDashboard(): Promise<DashboardResumo> {
  return request<DashboardResumo>("/api/dashboard");
}
