import { useEffect, useState } from "react";
import { LoginPage } from "./pages/Login";
import { NotaFiscalPage } from "./pages/NotaFiscal";
import { encerrarSessao, obterSessao, observarSessao } from "./services/session";

export default function App() {
  const [sessao, setSessao] = useState(obterSessao);

  useEffect(() => observarSessao(setSessao), []);

  // Sem sessão válida, a tela de extração não é renderizada (e o backend recusa as chamadas com 401).
  if (!sessao) {
    return (
      <div className="content">
        <LoginPage />
      </div>
    );
  }

  return (
    <div className="content">
      <div className="session-bar">
        <span className="muted small">
          Conectado como <strong>{sessao.usuario}</strong>
        </span>
        <button type="button" className="btn btn-ghost" onClick={encerrarSessao}>
          Sair
        </button>
      </div>
      <NotaFiscalPage />
    </div>
  );
}
