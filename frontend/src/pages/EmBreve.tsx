import { Link } from "react-router-dom";

export function EmBrevePage({ titulo, descricao }: { titulo: string; descricao: string }) {
  return (
    <div className="page">
      <header className="page-header">
        <h1>{titulo}</h1>
        <p>{descricao}</p>
      </header>
      <section className="card empty-state">
        <h2 className="card-title">Módulo previsto para a próxima fase</h2>
        <p className="card-hint">
          As tabelas de contas, parcelas e vínculos já existem no banco. A tela e a integração com a extração de
          notas fiscais serão implementadas nas próximas fases.
        </p>
        <Link to="/nota-fiscal" className="btn btn-secondary">
          Ir para Extrair Nota Fiscal
        </Link>
      </section>
    </div>
  );
}
