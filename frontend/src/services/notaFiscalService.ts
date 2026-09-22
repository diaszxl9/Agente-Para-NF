import type { ExtracaoResponse } from "../types/notaFiscal";
import { request } from "./api";

const EXTRACTION_TIMEOUT_MS = 180_000;

export function extrairNotaFiscal(arquivo: File): Promise<ExtracaoResponse> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  return request<ExtracaoResponse>(
    "/api/notas-fiscais/extrair",
    { method: "POST", body: form },
    EXTRACTION_TIMEOUT_MS,
  );
}
