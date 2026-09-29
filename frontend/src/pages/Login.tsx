import { useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { mensagemDeErro } from "../services/api";
import { login } from "../services/authService";

export function LoginPage() {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [entrando, setEntrando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function entrar(e: FormEvent) {
    e.preventDefault();
    if (entrando) return;
    setEntrando(true);
    setErro(null);
    try {
      await login(usuario, senha);
    } catch (err) {
      setErro(mensagemDeErro(err));
      setEntrando(false);
    }
  }

  return (
    <div className="page page-login">
      <header className="page-header center">
        <h1>Extração de Dados de Nota Fiscal</h1>
        <p>Entre para continuar</p>
      </header>

      <form className="card" onSubmit={entrar}>
        <div className="form-field">
          <label htmlFor="usuario">Usuário</label>
          <input
            id="usuario"
            className="input"
            autoComplete="username"
            autoFocus
            required
            value={usuario}
            disabled={entrando}
            onChange={(e) => setUsuario(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label htmlFor="senha">Senha</label>
          <input
            id="senha"
            className="input"
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            disabled={entrando}
            onChange={(e) => setSenha(e.target.value)}
          />
        </div>

        <button type="submit" className="btn btn-primary btn-block" disabled={entrando}>
          {entrando ? (
            <>
              <span className="spinner" aria-hidden="true" /> Entrando...
            </>
          ) : (
            "Entrar"
          )}
        </button>

        {erro && (
          <div className="alert alert-error" role="alert">
            <Icon name="alert" />
            <span>{erro}</span>
          </div>
        )}
      </form>
    </div>
  );
}
