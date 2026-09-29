import { request } from "./api";
import { iniciarSessao } from "./session";

interface LoginResponse {
  token: string;
  usuario: string;
  expira_em: number;
}

export async function login(usuario: string, senha: string): Promise<void> {
  const r = await request<LoginResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, senha }),
  });
  iniciarSessao({ token: r.token, usuario: r.usuario, expiraEm: r.expira_em });
}
