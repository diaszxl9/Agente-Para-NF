import { request } from "./api";

export interface ValidacaoApiKey {
  valida: boolean;
  mensagem: string;
}

// A chave vai em header para o backend, que faz a chamada de teste ao Gemini; ela não é salva em lugar nenhum.
export function validarGeminiApiKey(apiKey: string): Promise<ValidacaoApiKey> {
  return request<ValidacaoApiKey>("/api/gemini/validar", {
    method: "POST",
    headers: { "X-Gemini-Api-Key": apiKey },
  });
}
