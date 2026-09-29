// Sessão de login (somente o token de acesso, nunca a Gemini API Key). Fica no sessionStorage: sobrevive a um
// recarregamento da página e some ao fechar a aba.
const STORAGE_KEY = "nf-sessao";

export interface Sessao {
  token: string;
  usuario: string;
  expiraEm: number; // epoch em segundos
}

type Listener = (sessao: Sessao | null) => void;
const listeners = new Set<Listener>();

function ler(): Sessao | null {
  try {
    const bruto = sessionStorage.getItem(STORAGE_KEY);
    const sessao = bruto ? (JSON.parse(bruto) as Sessao) : null;
    return sessao && sessao.expiraEm * 1000 > Date.now() ? sessao : null;
  } catch {
    return null;
  }
}

let atual: Sessao | null = ler();

export function obterSessao(): Sessao | null {
  if (atual && atual.expiraEm * 1000 <= Date.now()) encerrarSessao();
  return atual;
}

export function iniciarSessao(sessao: Sessao) {
  atual = sessao;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(sessao));
  } catch {
    // Sem storage (ex.: modo privado restrito): a sessão vale só enquanto a página estiver aberta.
  }
  listeners.forEach((l) => l(atual));
}

export function encerrarSessao() {
  atual = null;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignorado
  }
  listeners.forEach((l) => l(null));
}

export function observarSessao(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
