import type { Status } from "../types/financeiro";
import { Icon } from "./Icon";

export type Mensagem = { tipo: "sucesso" | "erro"; texto: string } | null;

export function Feedback({ mensagem }: { mensagem: Mensagem }) {
  if (!mensagem) return null;
  const sucesso = mensagem.tipo === "sucesso";
  return (
    <div className={`alert ${sucesso ? "alert-success" : "alert-error"}`} role={sucesso ? "status" : "alert"}>
      <Icon name={sucesso ? "check" : "alert"} />
      <span>{mensagem.texto}</span>
    </div>
  );
}

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`status-badge ${status === "ATIVO" ? "ok" : "off"}`}>{status}</span>;
}

// Ação "Excluir" da tabela: exclusão LÓGICA (status passa a INATIVO). Registro excluído mostra "Reativar".
export function BotaoExcluir({
  status,
  descricao,
  disabled,
  onClick,
}: {
  status: Status;
  descricao: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  const ativo = status === "ATIVO";
  function clicar() {
    if (ativo && !window.confirm(`Excluir ${descricao}?

O registro ficará INATIVO e poderá ser reativado depois.`)) return;
    onClick();
  }
  return (
    <button
      type="button"
      className={`btn btn-sm ${ativo ? "btn-danger-soft" : "btn-ok-soft"}`}
      disabled={disabled}
      onClick={clicar}
    >
      <Icon name={ativo ? "trash" : "refresh"} size={15} />
      {ativo ? "Excluir" : "Reativar"}
    </button>
  );
}
