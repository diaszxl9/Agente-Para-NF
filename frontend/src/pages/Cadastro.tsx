import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { Tabs } from "../components/Tabs";
import { mensagemDeErro } from "../services/api";
import { alterarSituacao, atualizar, criar, listar } from "../services/cadastrosService";
import type { CadastroConfig, CadastroRegistro, StatusFiltro } from "../types/cadastros";

interface Editor {
  registro: CadastroRegistro | null;
}

export function CadastroPage({ config }: { config: CadastroConfig }) {
  const [status, setStatus] = useState<StatusFiltro>("ativos");
  const [busca, setBusca] = useState("");
  const [registros, setRegistros] = useState<CadastroRegistro[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setRegistros(await listar(config.endpoint, status, busca));
    } catch (e) {
      setRegistros([]);
      setErro(mensagemDeErro(e));
    } finally {
      setCarregando(false);
    }
  }, [config.endpoint, status, busca]);

  useEffect(() => {
    const timer = setTimeout(carregar, busca ? 300 : 0);
    return () => clearTimeout(timer);
  }, [carregar, busca]);

  async function alternar(registro: CadastroRegistro) {
    const acao = registro.ativo ? "inativar" : "reativar";
    if (registro.ativo && !window.confirm(`Deseja ${acao} este registro? Ele poderá ser reativado depois.`)) return;
    try {
      await alterarSituacao(config.endpoint, registro.id, !registro.ativo);
      await carregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>{config.titulo}</h1>
          <p>{config.subtitulo}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setEditor({ registro: null })}>
          <Icon name="plus" /> Novo {config.singular}
        </button>
      </header>

      <section className="card">
        <div className="toolbar">
          <Tabs
            tabs={[
              { id: "ativos", label: "Ativos" },
              { id: "inativos", label: "Inativos" },
              { id: "todos", label: "Todos" },
            ]}
            active={status}
            onChange={setStatus}
          />
          <label className="search">
            <Icon name="search" size={16} />
            <input placeholder="Buscar..." value={busca} onChange={(e) => setBusca(e.target.value)} />
          </label>
        </div>

        {erro && (
          <div className="alert alert-error" role="alert">
            <Icon name="alert" />
            <span>{erro}</span>
          </div>
        )}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                {config.campos.map((c) => (
                  <th key={c.name}>{c.label}</th>
                ))}
                <th>Situação</th>
                <th className="actions-col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {carregando && (
                <tr>
                  <td colSpan={config.campos.length + 2} className="muted center">
                    Carregando...
                  </td>
                </tr>
              )}
              {!carregando && registros.length === 0 && !erro && (
                <tr>
                  <td colSpan={config.campos.length + 2} className="muted center">
                    Nenhum registro encontrado.
                  </td>
                </tr>
              )}
              {!carregando &&
                registros.map((r) => (
                  <tr key={r.id} className={r.ativo ? undefined : "row-inactive"}>
                    {config.campos.map((c) => (
                      <td key={c.name}>{r[c.name] ?? <span className="muted">—</span>}</td>
                    ))}
                    <td>
                      <span className={`pill ${r.ativo ? "pill-ok" : "pill-off"}`}>{r.ativo ? "Ativo" : "Inativo"}</span>
                    </td>
                    <td className="actions-col">
                      <button className="btn btn-ghost" onClick={() => setEditor({ registro: r })}>
                        Editar
                      </button>
                      <button className="btn btn-ghost" onClick={() => alternar(r)}>
                        {r.ativo ? "Inativar" : "Reativar"}
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      {editor && (
        <FormularioModal
          config={config}
          registro={editor.registro}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null);
            carregar();
          }}
        />
      )}
    </div>
  );
}

interface FormularioProps {
  config: CadastroConfig;
  registro: CadastroRegistro | null;
  onClose: () => void;
  onSaved: () => void;
}

function FormularioModal({ config, registro, onClose, onSaved }: FormularioProps) {
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(config.campos.map((c) => [c.name, String(registro?.[c.name] ?? "")])),
  );
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setSalvando(true);
    setErro(null);
    const payload = Object.fromEntries(config.campos.map((c) => [c.name, valores[c.name].trim() || null]));
    try {
      if (registro) await atualizar(config.endpoint, registro.id, payload);
      else await criar(config.endpoint, payload);
      onSaved();
    } catch (err) {
      setErro(mensagemDeErro(err));
      setSalvando(false);
    }
  }

  return (
    <div className="modal-scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal" onSubmit={salvar} role="dialog" aria-modal="true" aria-label={config.singular}>
        <h2 className="card-title">
          {registro ? "Editar" : "Novo"} {config.singular}
        </h2>
        {config.campos.map((c) => (
          <label className="form-field" key={c.name}>
            <span>
              {c.label}
              {c.required && " *"}
            </span>
            <input
              value={valores[c.name]}
              required={c.required}
              maxLength={c.maxLength}
              placeholder={c.placeholder}
              onChange={(e) => setValores({ ...valores, [c.name]: e.target.value })}
            />
          </label>
        ))}
        {erro && (
          <div className="alert alert-error" role="alert">
            <Icon name="alert" />
            <span>{erro}</span>
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={salvando}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={salvando}>
            {salvando ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </form>
    </div>
  );
}
