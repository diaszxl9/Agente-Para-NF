import { encerrarSessao, obterSessao } from "./session";

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

export class ApiError extends Error {
  status: number;
  codigo: string | null;

  constructor(message: string, status: number, codigo: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.codigo = codigo;
  }
}

function codigoDoErro(body: unknown): string | null {
  const codigo = (body as { codigo?: unknown } | null)?.codigo;
  return typeof codigo === "string" ? codigo : null;
}

function mensagemDoErro(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const campo = first.loc?.slice(1).join(".");
    return campo ? `${campo}: ${first.msg ?? "valor inválido"}` : (first.msg ?? "Dados inválidos.");
  }
  if (status === 502 || status === 504) return "O servidor não respondeu. Verifique se o backend está em execução.";
  return `Erro inesperado (HTTP ${status}).`;
}

export async function request<T>(path: string, init?: RequestInit, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(init?.headers);
  if (API_KEY) headers.set("X-API-Key", API_KEY);
  const token = obterSessao()?.token;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...init, headers, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("A requisição demorou demais e foi cancelada.", 0);
    }
    throw new ApiError("Não foi possível conectar ao servidor. Verifique se o backend está em execução.", 0);
  } finally {
    clearTimeout(timer);
  }

  const body: unknown = await response.json().catch(() => null);
  // Sessão expirada/inválida: volta para a tela de login.
  if (response.status === 401 && token) encerrarSessao();
  if (!response.ok) {
    throw new ApiError(mensagemDoErro(body, response.status), response.status, codigoDoErro(body));
  }
  return body as T;
}

export function mensagemDeErro(error: unknown): string {
  return error instanceof ApiError ? error.message : "Ocorreu um erro inesperado. Tente novamente.";
}
