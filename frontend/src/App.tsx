import { useEffect, useState } from "react";
import { Icon, type IconName } from "./components/Icon";
import { ClassificacoesPage } from "./pages/Classificacoes";
import { ContasPage } from "./pages/Contas";
import { LoginPage } from "./pages/Login";
import { NotaFiscalPage } from "./pages/NotaFiscal";
import { PessoasPage } from "./pages/Pessoas";
import { encerrarSessao, obterSessao, observarSessao } from "./services/session";

interface Rota {
  id: string;
  label: string;
  icon: IconName;
  grupo: string;
}

const ROTAS: Rota[] = [
  { id: "extracao", label: "Extração de NF", icon: "file", grupo: "Notas Fiscais" },
  { id: "fornecedores", label: "Fornecedores", icon: "truck", grupo: "Pessoas" },
  { id: "clientes", label: "Clientes", icon: "users", grupo: "Pessoas" },
  { id: "faturados", label: "Faturados", icon: "user", grupo: "Pessoas" },
  { id: "receitas", label: "Tipos de Receita", icon: "tag", grupo: "Classificação" },
  { id: "despesas", label: "Tipos de Despesa", icon: "tag", grupo: "Classificação" },
  { id: "pagar", label: "Contas a Pagar", icon: "arrowUp", grupo: "Financeiro" },
  { id: "receber", label: "Contas a Receber", icon: "arrowDown", grupo: "Financeiro" },
];

function rotaAtual(): string {
  const id = window.location.hash.replace(/^#\/?/, "");
  return ROTAS.some((r) => r.id === id) ? id : "extracao";
}

function Pagina({ rota }: { rota: string }) {
  switch (rota) {
    case "fornecedores":
      return <PessoasPage tipo="FORNECEDOR" />;
    case "clientes":
      return <PessoasPage tipo="CLIENTE" />;
    case "faturados":
      return <PessoasPage tipo="FATURADO" />;
    case "receitas":
      return <ClassificacoesPage tipo="RECEITA" />;
    case "despesas":
      return <ClassificacoesPage tipo="DESPESA" />;
    case "pagar":
      return <ContasPage tipo="PAGAR" />;
    case "receber":
      return <ContasPage tipo="RECEBER" />;
    default:
      return null;
  }
}

export default function App() {
  const [sessao, setSessao] = useState(obterSessao);
  const [rota, setRota] = useState(rotaAtual);
  const [menuAberto, setMenuAberto] = useState(false);

  useEffect(() => observarSessao(setSessao), []);

  useEffect(() => {
    const aoMudar = () => {
      setRota(rotaAtual());
      setMenuAberto(false);
    };
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);

  // Sem sessão válida, nenhuma tela do sistema é renderizada (e o backend recusa as chamadas com 401).
  if (!sessao) {
    return (
      <div className="content">
        <LoginPage />
      </div>
    );
  }

  const grupos = [...new Set(ROTAS.map((r) => r.grupo))];

  return (
    <div className={`layout${menuAberto ? " menu-aberto" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Icon name="database" size={20} />
          <span>Gestão Financeira</span>
        </div>
        <nav className="sidebar-nav">
          {grupos.map((g) => (
            <div key={g} className="sidebar-group">
              <span className="sidebar-group-title">{g}</span>
              {ROTAS.filter((r) => r.grupo === g).map((r) => (
                <a key={r.id} href={`#/${r.id}`} className={`sidebar-link${rota === r.id ? " active" : ""}`}
                  aria-current={rota === r.id ? "page" : undefined}>
                  <Icon name={r.icon} size={17} />
                  {r.label}
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="muted small">
            Conectado como <strong>{sessao.usuario}</strong>
          </span>
          <button type="button" className="btn btn-ghost" onClick={encerrarSessao}>
            Sair
          </button>
        </div>
      </aside>
      <div className="sidebar-backdrop" onClick={() => setMenuAberto(false)} />

      <main className="content">
        <button type="button" className="icon-btn menu-toggle" aria-label="Abrir menu" onClick={() => setMenuAberto(true)}>
          <Icon name="menu" />
        </button>
        {/* A tela de extração fica sempre montada: trocar de menu não perde a API Key nem o resultado. */}
        <div hidden={rota !== "extracao"}>
          <NotaFiscalPage />
        </div>
        {rota !== "extracao" && <Pagina rota={rota} />}
      </main>
    </div>
  );
}
