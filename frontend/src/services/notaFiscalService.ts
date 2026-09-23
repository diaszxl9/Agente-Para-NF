import type { ExtracaoResponse } from "../types/notaFiscal";
import { request } from "./api";

// Deve cobrir o pior caso do backend: 2 chamadas ao Gemini (nova tentativa se o JSON vier inválido) de até
// GEMINI_TIMEOUT_SECONDS (120 s) cada, mais uma margem. Com 180 s a tela desistia antes do servidor terminar.
const EXTRACTION_TIMEOUT_MS = 260_000;

export function extrairNotaFiscal(arquivo: File): Promise<ExtracaoResponse> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  return request<ExtracaoResponse>(
    "/api/notas-fiscais/extrair",
    { method: "POST", body: form },
    EXTRACTION_TIMEOUT_MS,
  );
}
