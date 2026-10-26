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
import {
  alterarStatusClassificacao,
  atualizarClassificacao,
  criarClassificacao,
  listarClassificacoes,
} from "../services/financeiroService";
import type { Classificacao, TipoClassificacao } from "../types/financeiro";

const COLUNAS: Colunas<Classificacao, "id" | "descricao" | "tipo" | "status"> = {
  id: (c) => c.id,
  descricao: (c) => c.descricao,
  tipo: (c) => c.tipo,
  status: (c) => c.status,
};

export function ClassificacoesPage({ tipo }: { tipo: TipoClassificacao }) {
  const nome = tipo === "DESPESA" ? "Tipo de Despesa" : "Tipo de Receita";
  const [descricao, setDescricao] = useState("");
  const [editando, setEditando] = useState<number | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState<Mensagem>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const consultar = useCallback((f: FiltroConsulta) => listarClassificacoes(tipo, f.status, f.busca), [tipo]);
  const listagem = useListagem(consultar);
  const { ordenada, ordem, ordenarPor } = useOrdenacao(listagem.lista ?? [], COLUNAS, "descricao");
  const { iniciar } = listagem;

  useEffect(() => {
    setDescricao("");
    setEditando(null);
    setMensagem(null);
    iniciar();
  }, [tipo, iniciar]);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (salvando) return;
    setSalvando(true);
    setMensagem(null);
    try {
      // STATUS oculto: o cadastro nasce ATIVO e a edição altera somente a descrição.
      const c = editando ? await atualizarClassificacao(editando, descricao) : await criarClassificacao(tipo, descricao);
      setMensagem({ tipo: "sucesso", texto: `${nome} "${c.descricao}" ${editando ? "atualizado" : "cadastrado"} (ID ${c.id}).` });
      setDescricao("");
      setEditando(null);
      await listagem.recarregar();
    } catch (err) {
      setMensagem({ tipo: "erro", texto: mensagemDeErro(err) });
    } finally {
      setSalvando(false);
    }
  }

  async function excluirOuReativar(c: Classificacao) {
    setMensagem(null);
    try {
      const r = await alterarStatusClassificacao(c.id, c.status === "INATIVO");
      setMensagem({ tipo: "sucesso", texto: `${nome} "${r.descricao}" ${r.status === "ATIVO" ? "reativado" : "excluído (inativado)"}.` });
      if (editando === c.id) cancelarEdicao();
      await listagem.recarregar();
    } catch (err) {
      setMensagem({ tipo: "erro", texto: mensagemDeErro(err) });
    }
  }

  function editar(c: Classificacao) {
    setEditando(c.id);
    setDescricao(c.descricao);
    setMensagem(null);
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function cancelarEdicao() {
    setEditando(null);
    setDescricao("");
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Manter {nome}</h1>
        <p>Classificações usadas nas contas a {tipo === "DESPESA" ? "pagar" : "receber"}. A exclusão é lógica: o registro fica INATIVO.</p>
      </header>

      <form className="card" onSubmit={salvar} ref={formRef}>
        <h2 className="card-title">{editando ? `Editar ${nome.toLowerCase()} #${editando}` : `Novo ${nome.toLowerCase()}`}</h2>
        <div className="key-row">
          <input className="input" required maxLength={160} aria-label="Descrição" placeholder="Descrição"
            value={descricao} onChange={(e) => setDescricao(e.target.value)} />
          {editando && (
            <button type="button" className="btn btn-secondary" onClick={cancelarEdicao}>
              Cancelar
            </button>
          )}
          <button type="submit" className="btn btn-primary" disabled={salvando}>
            <Icon name={editando ? "check" : "plus"} size={16} />
            {editando ? "Salvar" : "Cadastrar"}
          </button>
        </div>
        <Feedback mensagem={mensagem} />
      </form>

      <section className="card">
        <div className="toolbar">
          <h2 className="card-title">{tipo === "DESPESA" ? "Tipos de Despesa" : "Tipos de Receita"}</h2>
          <BarraBusca placeholder="Descrição (vários termos)" carregando={listagem.carregando}
            onBuscar={listagem.buscar} onTodos={listagem.todos} />
        </div>
        <p className="muted small">TODOS lista os registros ativos. A busca também encontra os excluídos, que podem ser reativados.</p>
        <Feedback mensagem={listagem.erro ? { tipo: "erro", texto: listagem.erro } : null} />
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <ThOrdenavel coluna="id" ordem={ordem} onOrdenar={ordenarPor}>ID</ThOrdenavel>
                <ThOrdenavel coluna="descricao" ordem={ordem} onOrdenar={ordenarPor}>Descrição</ThOrdenavel>
                <ThOrdenavel coluna="tipo" ordem={ordem} onOrdenar={ordenarPor}>Tipo</ThOrdenavel>
                <ThOrdenavel coluna="status" ordem={ordem} onOrdenar={ordenarPor}>Status</ThOrdenavel>
                <th className="num">Ações</th>
              </tr>
            </thead>
            <tbody>
              {ordenada.length === 0 ? (
                <LinhaVazia colunas={5} carregada={listagem.lista !== null} carregando={listagem.carregando} />
              ) : (
                ordenada.map((c) => (
                  <tr key={c.id} className={c.status === "INATIVO" ? "row-inactive" : undefined}>
                    <td>{c.id}</td>
                    <td><strong>{c.descricao}</strong></td>
                    <td>{c.tipo}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td className="num">
                      <div className="row-actions">
                        <button type="button" className="btn btn-sm btn-secondary" disabled={c.status === "INATIVO"}
                          onClick={() => editar(c)}>
                          <Icon name="edit" size={15} /> Editar
                        </button>
                        <BotaoExcluir status={c.status} descricao={`${nome.toLowerCase()} "${c.descricao}"`}
                          onClick={() => excluirOuReativar(c)} />
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
