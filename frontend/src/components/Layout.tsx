import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Icon, type IconName } from "./Icon";

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const MENU: NavGroup[] = [
  { title: "", items: [{ to: "/", label: "Dashboard", icon: "dashboard" }] },
  {
    title: "Cadastros",
    items: [
      { to: "/cadastros/fornecedores", label: "Fornecedores", icon: "truck" },
      { to: "/cadastros/clientes", label: "Clientes", icon: "users" },
      { to: "/cadastros/faturados", label: "Faturados", icon: "user" },
      { to: "/cadastros/tipos-receita", label: "Tipos de Receita", icon: "trendUp" },
      { to: "/cadastros/tipos-despesa", label: "Tipos de Despesa", icon: "tag" },
    ],
  },
  {
    title: "Financeiro",
    items: [
      { to: "/financeiro/contas-a-pagar", label: "Contas a Pagar", icon: "arrowUp" },
      { to: "/financeiro/contas-a-receber", label: "Contas a Receber", icon: "arrowDown" },
    ],
  },
  {
    title: "Inteligência Artificial",
    items: [{ to: "/nota-fiscal", label: "Extrair Nota Fiscal", icon: "sparkles" }],
  },
];

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="icon-btn" onClick={() => setOpen((v) => !v)} aria-label="Abrir menu" aria-expanded={open}>
          <Icon name="menu" size={22} />
        </button>
        <span className="brand-text">Gestão Financeira</span>
      </header>

      {open && <div className="scrim" onClick={() => setOpen(false)} />}

      <aside className={`sidebar${open ? " open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">
            <Icon name="file" size={18} />
          </span>
          <span className="brand-text">Gestão Financeira</span>
        </div>
        <nav aria-label="Menu principal">
          {MENU.map((group) => (
            <div className="nav-group" key={group.title || "root"}>
              {group.title && <div className="nav-title">{group.title}</div>}
              {group.items.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.to === "/"} className="nav-link">
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
