import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { BotaoExcluir, Feedback, StatusBadge, type Mensagem } from "../components/Feedback";
import { Icon } from "../components/Icon";
import {
  BarraBusca,
  LinhaVazia,
  ThOrdenavel,
  useListagem,
  useOrdenacao,
  type Colunas,
  type FiltroConsulta,
} from "../components/Listagem";
import { mensagemDeErro } from "../services/api";
import { alterarStatusPessoa, atualizarPessoa, criarPessoa, listarPessoas } from "../services/financeiroService";
import type { Pessoa, TipoPessoa } from "../types/financeiro";

const TITULOS: Record<TipoPessoa, { titulo: string; singular: string; documento: string }> = {
  FORNECEDOR: { titulo: "Fornecedores", singular: "Fornecedor", documento: "CNPJ/CPF" },
  CLIENTE: { titulo: "Clientes", singular: "Cliente", documento: "CPF/CNPJ" },
  FATURADO: { titulo: "Faturados", singular: "Faturado", documento: "CPF/CNPJ" },
};

const VAZIO = { razao_social: "", fantasia: "", documento: "" };

const COLUNAS: Colunas<Pessoa, "id" | "nome" | "documento" | "status"> = {
  id: (p) => p.id,
  nome: (p) => p.razao_social,
  documento: (p) => p.documento.replace(/\D/g, ""),
  status: (p) => p.status,
};

export function PessoasPage({ tipo }: { tipo: TipoPessoa }) {
  const textos = TITULOS[tipo];
  const [form, setForm] = useState(VAZIO);
  const [editando, setEditando] = useState<number | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState<Mensagem>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const consultar = useCallback((f: FiltroConsulta) => listarPessoas(tipo, f.status, f.busca), [tipo]);
  const listagem = useListagem(consultar);
  const { ordenada, ordem, ordenarPor } = useOrdenacao(listagem.lista ?? [], COLUNAS, "nome");
  const { iniciar } = listagem;

  useEffect(() => {
    setForm(VAZIO);
    setEditando(null);
    setMensagem(null);
    iniciar();
  }, [tipo, iniciar]);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (salvando) return;
    setSalvando(true);
    setMensagem(null);
    // O STATUS não faz parte do formulário: no cadastro o backend grava ATIVO e a edição não o altera.
    const dados = { razao_social: form.razao_social, fantasia: form.fantasia || null, documento: form.documento };
    try {
      const p = editando ? await atualizarPessoa(editando, dados) : await criarPessoa(tipo, dados);
      setMensagem({ tipo: "sucesso", texto: `${textos.singular} ${editando ? "atualizado" : "cadastrado"} (ID ${p.id}).` });
      setForm(VAZIO);
      setEditando(null);
      await listagem.recarregar();
    } catch (err) {
      setMensagem({ tipo: "erro", texto: mensagemDeErro(err) });
    } finally {
      setSalvando(false);
    }
  }

  async function excluirOuReativar(p: Pessoa) {
    setMensagem(null);
    try {
      const r = await alterarStatusPessoa(p.id, p.status === "INATIVO");
      setMensagem({ tipo: "sucesso", texto: `${textos.singular} "${r.razao_social}" ${r.status === "ATIVO" ? "reativado" : "excluído (inativado)"}.` });
      if (editando === p.id) cancelarEdicao();
      await listagem.recarregar();
    } catch (err) {
      setMensagem({ tipo: "erro", texto: mensagemDeErro(err) });
    }
  }

  function editar(p: Pessoa) {
    setEditando(p.id);
    setForm({ razao_social: p.razao_social, fantasia: p.fantasia ?? "", documento: p.documento });
    setMensagem(null);
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function cancelarEdicao() {
    setEditando(null);
    setForm(VAZIO);
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Manter {textos.singular}</h1>
        <p>A exclusão é lógica: o registro fica INATIVO e pode ser reativado.</p>
      </header>

      <form className="card" onSubmit={salvar} ref={formRef}>
        <h2 className="card-title">{editando ? `Editar ${textos.singular.toLowerCase()} #${editando}` : `Novo ${textos.singular.toLowerCase()}`}</h2>
        <div className="form-grid">
          <div className="form-field span-2">
            <label htmlFor="razao">{tipo === "FORNECEDOR" ? "Razão Social" : "Razão Social / Nome"}</label>
            <input id="razao" className="input" required maxLength={255} value={form.razao_social}
              onChange={(e) => setForm({ ...form, razao_social: e.target.value })} />
          </div>
          <div className="form-field">
            <label htmlFor="fantasia">Nome Fantasia</label>
            <input id="fantasia" className="input" maxLength={255} value={form.fantasia}
              onChange={(e) => setForm({ ...form, fantasia: e.target.value })} />
          </div>
          <div className="form-field">
            <label htmlFor="documento">{textos.documento}</label>
            <input id="documento" className="input" required maxLength={30} inputMode="numeric"
              placeholder="Somente números ou formatado" value={form.documento}
              onChange={(e) => setForm({ ...form, documento: e.target.value })} />
          </div>
        </div>
        <div className="form-actions">
          {editando && (
            <button type="button" className="btn btn-secondary" onClick={cancelarEdicao}>
              Cancelar
            </button>
          )}
          <button type="submit" className="btn btn-primary" disabled={salvando}>
            <Icon name={editando ? "check" : "plus"} size={16} />
            {editando ? "Salvar alterações" : "Cadastrar"}
          </button>
        </div>
        <Feedback mensagem={mensagem} />
      </form>

      <section className="card">
        <div className="toolbar">
          <h2 className="card-title">{textos.titulo}</h2>
          <BarraBusca placeholder="Nome, fantasia ou documento (vários termos)" carregando={listagem.carregando}
            onBuscar={listagem.buscar} onTodos={listagem.todos} />
        </div>
        <p className="muted small">TODOS lista os registros ativos. A busca também encontra os excluídos, que podem ser reativados.</p>
        <Feedback mensagem={listagem.erro ? { tipo: "erro", texto: listagem.erro } : null} />
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <ThOrdenavel coluna="id" ordem={ordem} onOrdenar={ordenarPor}>ID</ThOrdenavel>
                <ThOrdenavel coluna="nome" ordem={ordem} onOrdenar={ordenarPor}>Razão Social / Nome</ThOrdenavel>
                <ThOrdenavel coluna="documento" ordem={ordem} onOrdenar={ordenarPor}>{textos.documento}</ThOrdenavel>
                <ThOrdenavel coluna="status" ordem={ordem} onOrdenar={ordenarPor}>Status</ThOrdenavel>
                <th className="num">Ações</th>
              </tr>
            </thead>
            <tbody>
              {ordenada.length === 0 ? (
                <LinhaVazia colunas={5} carregada={listagem.lista !== null} carregando={listagem.carregando} />
              ) : (
                ordenada.map((p) => (
                  <tr key={p.id} className={p.status === "INATIVO" ? "row-inactive" : undefined}>
                    <td>{p.id}</td>
                    <td>
                      <strong>{p.razao_social}</strong>
                      {p.fantasia && <div className="muted small">{p.fantasia}</div>}
                    </td>
                    <td className="nowrap">{p.documento}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td className="num">
                      <div className="row-actions">
                        <button type="button" className="btn btn-sm btn-secondary" disabled={p.status === "INATIVO"} onClick={() => editar(p)}>
                          <Icon name="edit" size={15} /> Editar
                        </button>
                        <BotaoExcluir status={p.status} descricao={`${textos.singular.toLowerCase()} "${p.razao_social}"`}
                          onClick={() => excluirOuReativar(p)} />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
