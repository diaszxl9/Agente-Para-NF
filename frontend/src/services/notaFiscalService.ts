import type { ExtracaoResponse } from "../types/notaFiscal";
import { request } from "./api";

// O backend encerra a extração em até GEMINI_TEMPO_MAXIMO_SECONDS (240 s por padrão), contando todas as chamadas
// ao Gemini e as retentativas. A tela espera um pouco mais, para receber a mensagem de erro do servidor em vez de
// desistir antes dele. Se aumentar o limite no backend, aumente aqui também.
const EXTRACTION_TIMEOUT_MS = 260_000;

// Enviado pelo backend quando o Gemini recusa a chave durante a extração.
export const CODIGO_CHAVE_RECUSADA = "gemini_api_key_recusada";

export interface Limites {
  max_upload_mb: number;
}

export function obterLimites(): Promise<Limites> {
  return request<Limites>("/api/notas-fiscais/limites");
}

export function extrairNotaFiscal(arquivo: File, geminiApiKey: string): Promise<ExtracaoResponse> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  return request<ExtracaoResponse>(
    "/api/notas-fiscais/extrair",
    { method: "POST", body: form, headers: { "X-Gemini-Api-Key": geminiApiKey } },
    EXTRACTION_TIMEOUT_MS,
  );
}
