import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent } from "react";
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
  alterarSituacaoParcela,
  alterarStatusConta,
  atualizarConta,
  criarConta,
  listarClassificacoes,
  listarContas,
  listarPessoas,
} from "../services/financeiroService";
import type { Classificacao, Movimento, Pessoa, TipoMovimento } from "../types/financeiro";
import { formatCurrency, formatDate } from "../utils/format";

type LinhaParcela = { data_vencimento: string; valor: string };

const novoForm = () => ({
  pessoa_id: "",
  faturado_id: "",
  numero_nota: "",
  data_emissao: "",
  descricao: "",
  valor_total: "",
  classificacao_ids: [] as number[],
  parcelas: [{ data_vencimento: "", valor: "" }] as LinhaParcela[],
});

const formDoMovimento = (m: Movimento) => ({
  pessoa_id: String(m.pessoa.id),
  faturado_id: m.faturado ? String(m.faturado.id) : "",
  numero_nota: m.numero_nota ?? "",
  data_emissao: m.data_emissao ?? "",
  descricao: m.descricao,
  valor_total: String(m.valor_total),
  classificacao_ids: m.classificacoes.map((c) => c.id),
  parcelas: m.parcelas.map((p) => ({ data_vencimento: p.data_vencimento, valor: String(p.valor) })),
});

const COLUNAS: Colunas<Movimento, "id" | "pessoa" | "descricao" | "classificacao" | "valor" | "parcelas" | "status"> = {
  id: (m) => m.id,
  pessoa: (m) => m.pessoa.razao_social,
  descricao: (m) => m.descricao,
  classificacao: (m) => m.classificacoes.map((c) => c.descricao).join(", "),
  valor: (m) => m.valor_total,
  parcelas: (m) => m.parcelas.length,
  status: (m) => m.status,
};

function numero(texto: string): number {
  const t = texto.trim();
  return Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t);
}

export function ContasPage({ tipo }: { tipo: TipoMovimento }) {
  const pagar = tipo === "PAGAR";
  const [pessoas, setPessoas] = useState<Pessoa[]>([]);
  const [faturados, setFaturados] = useState<Pessoa[]>([]);
  const [classificacoes, setClassificacoes] = useState<Classificacao[]>([]);
  const [form, setForm] = useState(novoForm);
  const [editando, setEditando] = useState<Movimento | null>(null);
  const [aberto, setAberto] = useState<number | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState<Mensagem>(null);
  const [mensagemLista, setMensagemLista] = useState<Mensagem>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const consultar = useCallback((f: FiltroConsulta) => listarContas(tipo, f.status, f.busca), [tipo]);
  const listagem = useListagem(consultar);
  const { ordenada, ordem, ordenarPor } = useOrdenacao(listagem.lista ?? [], COLUNAS, "id");
  const { iniciar } = listagem;

  useEffect(() => {
    setForm(novoForm());
    setEditando(null);
    setMensagem(null);
    setMensagemLista(null);
    iniciar();
    // Somente cadastros ATIVOS podem ser usados em um novo movimento.
    const principais = pagar
      ? listarPessoas("FORNECEDOR", "ATIVO")
      : Promise.all([listarPessoas("CLIENTE", "ATIVO"), listarPessoas("FATURADO", "ATIVO")]).then(([c, f]) => [...c, ...f]);
    Promise.all([principais, listarPessoas("FATURADO", "ATIVO"), listarClassificacoes(pagar ? "DESPESA" : "RECEITA", "ATIVO")])
      .then(([p, f, c]) => {
        setPessoas(p);
        setFaturados(f);
        setClassificacoes(c);
      })
      .catch((e) => setMensagem({ tipo: "erro", texto: mensagemDeErro(e) }));
  }, [tipo, pagar, iniciar]);

  function alterarParcela(i: number, campo: keyof LinhaParcela, valor: string) {
    setForm((f) => ({ ...f, parcelas: f.parcelas.map((p, j) => (j === i ? { ...p, [campo]: valor } : p)) }));
  }

  function dividirIgualmente() {
    const total = numero(form.valor_total);
    const n = form.parcelas.length;
    if (!(total > 0) || n === 0) return;
    const base = Math.floor((total / n) * 100) / 100;
    const ultima = Math.round((total - base * (n - 1)) * 100) / 100;
    setForm((f) => ({
      ...f,
      parcelas: f.parcelas.map((p, i) => ({ ...p, valor: String(i === n - 1 ? ultima : base) })),
    }));
  }

  function alternarClassificacao(id: number) {
    setForm((f) => ({
      ...f,
      classificacao_ids: f.classificacao_ids.includes(id)
        ? f.classificacao_ids.filter((c) => c !== id)
        : [...f.classificacao_ids, id],
    }));
  }

  const total = numero(form.valor_total);
  const soma = Math.round(form.parcelas.reduce((s, p) => s + (numero(p.valor) || 0), 0) * 100) / 100;

  function validar(): string | null {
    if (!form.pessoa_id) return pagar ? "Selecione o fornecedor." : "Selecione o cliente/faturado.";
    if (!form.descricao.trim()) return "Informe a descrição do movimento.";
    if (!(total > 0)) return "Informe um valor total maior que zero.";
    if (form.classificacao_ids.length === 0) return "Selecione ao menos uma classificação.";
    for (const [i, p] of form.parcelas.entries()) {
      if (!p.data_vencimento) return `Informe o vencimento da parcela ${i + 1}.`;
      if (!(numero(p.valor) > 0)) return `Informe um valor válido para a parcela ${i + 1}.`;
    }
    if (Math.abs(soma - total) > 0.01) return `A soma das parcelas (${formatCurrency(soma)}) difere do valor total (${formatCurrency(total)}).`;
    return null;
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (salvando) return;
    const problema = validar();
    if (problema) {
      setMensagem({ tipo: "erro", texto: problema });
      return;
    }
    setSalvando(true);
    setMensagem(null);
    try {
      const dados = {
        pessoa_id: Number(form.pessoa_id),
        faturado_id: form.faturado_id ? Number(form.faturado_id) : null,
        numero_nota: form.numero_nota.trim() || null,
        data_emissao: form.data_emissao || null,
        descricao: form.descricao,
        valor_total: total,
        classificacao_ids: form.classificacao_ids,
        parcelas: form.parcelas.map((p) => ({ data_vencimento: p.data_vencimento, valor: numero(p.valor) })),
      };
      // STATUS oculto: o movimento nasce ATIVO e a edição não o altera.
      const m = editando ? await atualizarConta(editando.id, dados) : await criarConta({ tipo, ...dados });
      setMensagem({
        tipo: "sucesso",
        texto: editando
          ? `Movimento ID ${m.id} atualizado com ${m.parcelas.length} parcela(s).`
          : `Registro lançado com sucesso. Movimento ID ${m.id} com ${m.parcelas.length} parcela(s).`,
      });
      setForm(novoForm());
      setEditando(null);
      await listagem.recarregar();
    } catch (err) {
      setMensagem({ tipo: "erro", texto: mensagemDeErro(err) });
    } finally {
      setSalvando(false);
    }
  }

  async function executar(acao: () => Promise<Movimento>, sucesso: (m: Movimento) => string) {
    setMensagemLista(null);
    try {
      const m = await acao();
      setMensagemLista({ tipo: "sucesso", texto: sucesso(m) });
      if (editando?.id === m.id) cancelarEdicao();
      await listagem.recarregar();
    } catch (err) {
      setMensagemLista({ tipo: "erro", texto: mensagemDeErro(err) });
    }
  }

  function editar(m: Movimento) {
    setEditando(m);
    setForm(formDoMovimento(m));
    setMensagem(null);
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function cancelarEdicao() {
    setEditando(null);
    setForm(novoForm());
  }

  // Na edição, a pessoa/classificação já vinculada continua selecionável mesmo que tenha sido inativada depois.
  const opcoesPessoas = editando && !pessoas.some((p) => p.id === editando.pessoa.id) ? [...pessoas, editando.pessoa] : pessoas;
  const faturadoAtual = editando?.faturado;
  const opcoesFaturados =
    faturadoAtual && !faturados.some((p) => p.id === faturadoAtual.id) ? [...faturados, faturadoAtual] : faturados;
  const opcoesClassificacoes = [
    ...classificacoes,
    ...(editando?.classificacoes.filter((c) => !classificacoes.some((x) => x.id === c.id)) ?? []),
  ];

  return (
    <div className="page">
      <header className="page-header">
        <h1>Contas a {pagar ? "Pagar" : "Receber"}</h1>
        <p>Cada movimento pode ter uma ou várias classificações e uma ou várias parcelas.</p>
      </header>

      <form className="card" onSubmit={salvar} noValidate ref={formRef}>
        <h2 className="card-title">
          {editando ? `Editar conta a ${pagar ? "pagar" : "receber"} #${editando.id}` : `Nova conta a ${pagar ? "pagar" : "receber"}`}
        </h2>
        <div className="form-grid">
          <div className="form-field span-2">
            <label htmlFor="pessoa">{pagar ? "Fornecedor" : "Cliente / Faturado"}</label>
            <select id="pessoa" className="input" value={form.pessoa_id} onChange={(e) => setForm({ ...form, pessoa_id: e.target.value })}>
              <option value="">Selecione...</option>
              {opcoesPessoas.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.razao_social} · {p.documento}{pagar ? "" : ` (${p.tipo.toLowerCase()})`}
                </option>
              ))}
            </select>
          </div>
          {pagar && (
            <div className="form-field span-2">
              <label htmlFor="faturado">Faturado (opcional)</label>
              <select id="faturado" className="input" value={form.faturado_id} onChange={(e) => setForm({ ...form, faturado_id: e.target.value })}>
                <option value="">Nenhum</option>
                {opcoesFaturados.map((p) => (
                  <option key={p.id} value={p.id}>{p.razao_social} · {p.documento}</option>
                ))}
              </select>
            </div>
          )}
          <div className="form-field span-2">
            <label htmlFor="descricao">Descrição / identificação do movimento</label>
            <input id="descricao" className="input" maxLength={500} value={form.descricao}
              onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </div>
          <div className="form-field">
            <label htmlFor="nota">Nº do documento</label>
            <input id="nota" className="input" maxLength={60} value={form.numero_nota}
              onChange={(e) => setForm({ ...form, numero_nota: e.target.value })} />
          </div>
          <div className="form-field">
            <label htmlFor="emissao">Data de emissão</label>
            <input id="emissao" type="date" className="input" value={form.data_emissao}
              onChange={(e) => setForm({ ...form, data_emissao: e.target.value })} />
          </div>
          <div className="form-field">
            <label htmlFor="valor">Valor total (R$)</label>
            <input id="valor" className="input" inputMode="decimal" placeholder="0,00" value={form.valor_total}
              onChange={(e) => setForm({ ...form, valor_total: e.target.value })} />
          </div>
        </div>

        <div className="form-field">
          <label>{pagar ? "Tipos de despesa" : "Tipos de receita"}</label>
          {opcoesClassificacoes.length === 0 ? (
            <p className="muted small">Nenhuma classificação ativa. Cadastre em "Tipos de {pagar ? "Despesa" : "Receita"}".</p>
          ) : (
            <div className="chips">
              {opcoesClassificacoes.map((c) => (
                <label key={c.id} className={`chip${form.classificacao_ids.includes(c.id) ? " selected" : ""}`}>
                  <input type="checkbox" checked={form.classificacao_ids.includes(c.id)} onChange={() => alternarClassificacao(c.id)} />
                  {c.descricao}
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="form-field">
          <div className="toolbar">
            <label>Parcelas</label>
            <div className="toolbar-actions">
              <button type="button" className="btn btn-sm btn-secondary" onClick={dividirIgualmente}>Dividir valor igualmente</button>
              <button type="button" className="btn btn-sm btn-secondary"
                onClick={() => setForm({ ...form, parcelas: [...form.parcelas, { data_vencimento: "", valor: "" }] })}>
                <Icon name="plus" size={15} /> Parcela
              </button>
            </div>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Parcela</th>
                  <th>Vencimento</th>
                  <th>Valor (R$)</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {form.parcelas.map((p, i) => (
                  <tr key={i}>
                    <td>{i + 1}/{form.parcelas.length}</td>
                    <td><input type="date" className="input" aria-label={`Vencimento da parcela ${i + 1}`} value={p.data_vencimento}
                      onChange={(e) => alterarParcela(i, "data_vencimento", e.target.value)} /></td>
                    <td><input className="input" inputMode="decimal" aria-label={`Valor da parcela ${i + 1}`} placeholder="0,00" value={p.valor}
                      onChange={(e) => alterarParcela(i, "valor", e.target.value)} /></td>
                    <td className="num">
                      <button type="button" className="icon-btn" aria-label="Remover parcela" disabled={form.parcelas.length === 1}
                        onClick={() => setForm({ ...form, parcelas: form.parcelas.filter((_, j) => j !== i) })}>
                        <Icon name="x" size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={`small ${total > 0 && Math.abs(soma - total) > 0.01 ? "text-danger" : "muted"}`}>
            Soma das parcelas: {formatCurrency(soma)}{total > 0 ? ` de ${formatCurrency(total)}` : ""}
          </p>
        </div>

        <div className="form-actions">
          {editando && (
            <button type="button" className="btn btn-secondary" onClick={cancelarEdicao}>
              Cancelar
            </button>
          )}
          <button type="submit" className={`btn btn-primary${editando ? "" : " btn-block"}`} disabled={salvando}>
            {salvando ? (
              <><span className="spinner" aria-hidden="true" /> SALVANDO...</>
            ) : editando ? (
              "SALVAR ALTERAÇÕES"
            ) : (
              "LANÇAR CONTA"
            )}
          </button>
        </div>
        <Feedback mensagem={mensagem} />
      </form>

      <section className="card">
        <div className="toolbar">
          <h2 className="card-title">Movimentos lançados</h2>
          <BarraBusca placeholder="Pessoa, documento, nº nota, descrição, classificação" carregando={listagem.carregando}
            onBuscar={listagem.buscar} onTodos={listagem.todos} />
        </div>
        <p className="muted small">TODOS lista os registros ativos. A busca também encontra os excluídos, que podem ser reativados.</p>
        <Feedback mensagem={listagem.erro ? { tipo: "erro", texto: listagem.erro } : mensagemLista} />
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <ThOrdenavel coluna="id" ordem={ordem} onOrdenar={ordenarPor}>ID</ThOrdenavel>
                <ThOrdenavel coluna="pessoa" ordem={ordem} onOrdenar={ordenarPor}>{pagar ? "Fornecedor" : "Cliente"}</ThOrdenavel>
                <ThOrdenavel coluna="descricao" ordem={ordem} onOrdenar={ordenarPor}>Descrição</ThOrdenavel>
                <ThOrdenavel coluna="classificacao" ordem={ordem} onOrdenar={ordenarPor}>Classificação</ThOrdenavel>
                <ThOrdenavel coluna="valor" ordem={ordem} onOrdenar={ordenarPor} className="num">Valor</ThOrdenavel>
                <ThOrdenavel coluna="parcelas" ordem={ordem} onOrdenar={ordenarPor}>Parcelas</ThOrdenavel>
                <ThOrdenavel coluna="status" ordem={ordem} onOrdenar={ordenarPor}>Status</ThOrdenavel>
                <th className="num">Ações</th>
              </tr>
            </thead>
            <tbody>
              {ordenada.length === 0 && (
                <LinhaVazia colunas={8} carregada={listagem.lista !== null} carregando={listagem.carregando} />
              )}
              {ordenada.map((m) => (
                <Fragment key={m.id}>
                  <tr className={m.status === "INATIVO" ? "row-inactive" : undefined}>
                    <td>{m.id}</td>
                    <td>
                      <strong>{m.pessoa.razao_social}</strong>
                      <div className="muted small">{m.pessoa.documento}</div>
                    </td>
                    <td>
                      {m.descricao}
                      {m.numero_nota && <div className="muted small">Nº {m.numero_nota}</div>}
                      {m.faturado && <div className="muted small">Faturado: {m.faturado.razao_social}</div>}
                    </td>
                    <td>{m.classificacoes.map((c) => c.descricao).join(", ")}</td>
                    <td className="num">{formatCurrency(m.valor_total)}</td>
                    <td>
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAberto(aberto === m.id ? null : m.id)}>
                        {m.parcelas.length} {aberto === m.id ? "▲" : "▼"}
                      </button>
                    </td>
                    <td><StatusBadge status={m.status} /></td>
                    <td className="num">
                      <div className="row-actions">
                        <button type="button" className="btn btn-sm btn-secondary" disabled={m.status === "INATIVO"}
                          onClick={() => editar(m)}>
                          <Icon name="edit" size={15} /> Editar
                        </button>
                        <BotaoExcluir status={m.status} descricao={`o movimento ID ${m.id}`}
                          onClick={() => executar(() => alterarStatusConta(m.id, m.status === "INATIVO"),
                            (r) => `Movimento ID ${r.id} ${r.status === "ATIVO" ? "reativado" : "excluído (inativado)"}.`)} />
                      </div>
                    </td>
                  </tr>
                  {aberto === m.id && (
                    <tr className="row-detail">
                      <td colSpan={8}>
                        <table className="table table-inner">
                          <thead>
                            <tr>
                              <th>Identificação</th>
                              <th>Vencimento</th>
                              <th className="num">Valor</th>
                              <th>Situação</th>
                              <th className="num" />
                            </tr>
                          </thead>
                          <tbody>
                            {m.parcelas.map((p) => (
                              <tr key={p.id}>
                                <td>{p.identificacao}</td>
                                <td>{formatDate(p.data_vencimento)}</td>
                                <td className="num">{formatCurrency(p.valor)}</td>
                                <td><span className={`status-badge ${p.situacao === "QUITADA" ? "ok" : "warn"}`}>{p.situacao}</span></td>
                                <td className="num">
                                  <button type="button" className="btn btn-sm btn-secondary" disabled={m.status === "INATIVO"}
                                    onClick={() => executar(() => alterarSituacaoParcela(p.id, p.situacao === "ABERTA"),
                                      () => `Parcela ${p.identificacao} ${p.situacao === "ABERTA" ? "quitada" : "reaberta"}.`)}>
                                    {p.situacao === "ABERTA" ? (pagar ? "Quitar" : "Receber") : "Reabrir"}
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
