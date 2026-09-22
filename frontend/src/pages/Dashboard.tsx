import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon, type IconName } from "../components/Icon";
import { mensagemDeErro } from "../services/api";
import { carregarDashboard } from "../services/cadastrosService";
import type { DashboardResumo } from "../types/cadastros";

const CARDS: { chave: keyof DashboardResumo; titulo: string; icon: IconName; to: string }[] = [
  { chave: "fornecedores", titulo: "Fornecedores", icon: "truck", to: "/cadastros/fornecedores" },
  { chave: "clientes", titulo: "Clientes", icon: "users", to: "/cadastros/clientes" },
  { chave: "contas_pagar", titulo: "Contas a Pagar", icon: "arrowUp", to: "/financeiro/contas-a-pagar" },
  { chave: "contas_receber", titulo: "Contas a Receber", icon: "arrowDown", to: "/financeiro/contas-a-receber" },
];

export function DashboardPage() {
  const [resumo, setResumo] = useState<DashboardResumo | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    carregarDashboard()
      .then(setResumo)
      .catch((e) => setErro(mensagemDeErro(e)));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Dashboard</h1>
        <p>Visão geral dos registros ativos no sistema</p>
      </header>

      {erro && (
        <div className="alert alert-warn" role="status">
          <Icon name="alert" />
          <span>Não foi possível carregar os totais: {erro}</span>
        </div>
      )}

      <div className="stat-grid">
        {CARDS.map((card) => (
          <Link to={card.to} className="stat-card" key={card.chave}>
            <span className="stat-icon">
              <Icon name={card.icon} size={22} />
            </span>
            <div>
              <div className="stat-label">{card.titulo}</div>
              <div className="stat-value">{resumo ? resumo[card.chave] : "—"}</div>
            </div>
          </Link>
        ))}
      </div>

      <section className="card">
        <h2 className="card-title">Extração de notas fiscais com IA</h2>
        <p className="card-hint">Envie o PDF de uma nota fiscal e obtenha os dados estruturados e a classificação da despesa.</p>
        <Link to="/nota-fiscal" className="btn btn-primary">
          Extrair Nota Fiscal
        </Link>
      </section>
    </div>
  );
}
