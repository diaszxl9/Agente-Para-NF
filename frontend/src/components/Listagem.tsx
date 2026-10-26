import { useCallback, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { mensagemDeErro } from "../services/api";
import type { Status } from "../types/financeiro";
import { Icon } from "./Icon";

/*
 * Padrão de layout das telas de cadastro:
 *  - a tabela abre já carregada com TODOS (somente status ATIVO); a BUSCA traz ativos e inativos;
 *  - a busca aceita mais de um elemento (termos separados por espaço, todos precisam casar);
 *  - clique no cabeçalho ordena pela coluna;
 *  - ações da linha: Editar / Excluir (lógico = inativar). Excluídos encontrados pela busca podem ser reativados.
 */

export type FiltroConsulta = { busca?: string; status?: Status };
type Consulta = { busca: string } | { todos: true };

export function useListagem<T>(consultar: (filtro: FiltroConsulta) => Promise<T[]>) {
  const [lista, setLista] = useState<T[] | null>(null);
  const [consulta, setConsulta] = useState<Consulta | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const requisicao = useRef(0); // descarta respostas de consultas antigas (ex.: troca de tela no meio da busca)

  const executar = useCallback(
    async (c: Consulta) => {
      const id = ++requisicao.current;
      setConsulta(c);
      setCarregando(true);
      setErro(null);
      try {
        const r = await consultar("busca" in c ? { busca: c.busca } : { status: "ATIVO" });
        if (id === requisicao.current) setLista(r);
      } catch (e) {
        if (id === requisicao.current) setErro(mensagemDeErro(e));
      } finally {
        if (id === requisicao.current) setCarregando(false);
      }
    },
    [consultar],
  );

  const limpar = useCallback(() => {
    requisicao.current++;
    setLista(null);
    setConsulta(null);
    setErro(null);
    setCarregando(false);
  }, []);

  const todos = useCallback(() => executar({ todos: true }), [executar]);

  // Ao abrir a tela (ou trocar o tipo), descarta a lista anterior e já carrega os registros ativos.
  const iniciar = useCallback(() => {
    limpar();
    void todos();
  }, [limpar, todos]);

  return {
    lista,
    carregando,
    erro,
    buscar: (busca: string) => executar({ busca }),
    todos,
    iniciar,
    // Depois de salvar/excluir, repete a última consulta (se houver) para a tabela refletir a alteração.
    recarregar: () => (consulta ? executar(consulta) : Promise.resolve()),
    limpar,
  };
}

export function BarraBusca({
  placeholder,
  carregando,
  onBuscar,
  onTodos,
}: {
  placeholder: string;
  carregando: boolean;
  onBuscar: (busca: string) => void;
  onTodos: () => void;
}) {
  const [termo, setTermo] = useState("");
  function enviar(e: FormEvent) {
    e.preventDefault();
    if (termo.trim()) onBuscar(termo.trim());
  }
  return (
    <form className="toolbar-actions" onSubmit={enviar} role="search">
      <div className="search">
        <Icon name="search" size={16} />
        <input className="input" placeholder={placeholder} value={termo} maxLength={100}
          onChange={(e) => setTermo(e.target.value)} aria-label="Buscar" />
      </div>
      <button type="submit" className="btn btn-sm btn-primary" disabled={carregando || !termo.trim()}>
        <Icon name="search" size={15} /> Buscar
      </button>
      <button type="button" className="btn btn-sm btn-secondary" disabled={carregando}
        onClick={() => { setTermo(""); onTodos(); }}>
        Todos
      </button>
    </form>
  );
}

export type Ordem<K extends string> = { coluna: K; asc: boolean };
export type Colunas<T, K extends string> = Record<K, (item: T) => string | number>;

const comparador = new Intl.Collator("pt-BR", { numeric: true, sensitivity: "base" });

/** `colunas` deve ser uma constante fora do componente (identidade estável). */
export function useOrdenacao<T, K extends string>(lista: T[], colunas: Colunas<T, K>, inicial: NoInfer<K>) {
  const [ordem, setOrdem] = useState<Ordem<K>>({ coluna: inicial, asc: true });
  const ordenada = useMemo(() => {
    const valor = colunas[ordem.coluna];
    return [...lista].sort((a, b) => {
      const va = valor(a);
      const vb = valor(b);
      const r = typeof va === "number" && typeof vb === "number" ? va - vb : comparador.compare(String(va), String(vb));
      return ordem.asc ? r : -r;
    });
  }, [lista, colunas, ordem]);
  const ordenarPor = (coluna: K) => setOrdem((o) => ({ coluna, asc: o.coluna === coluna ? !o.asc : true }));
  return { ordenada, ordem, ordenarPor };
}

export function ThOrdenavel<K extends string>({
  coluna,
  ordem,
  onOrdenar,
  className,
  children,
}: {
  coluna: K;
  ordem: Ordem<K>;
  onOrdenar: (coluna: K) => void;
  className?: string;
  children: ReactNode;
}) {
  const ativa = ordem.coluna === coluna;
  return (
    <th className={className} aria-sort={ativa ? (ordem.asc ? "ascending" : "descending") : "none"}>
      <button type="button" className={`th-sort${ativa ? " active" : ""}`} onClick={() => onOrdenar(coluna)}
        title="Ordenar por esta coluna">
        {children}
        <span className="th-sort-icon" aria-hidden="true">{ativa ? (ordem.asc ? "▲" : "▼") : "↕"}</span>
      </button>
    </th>
  );
}

/** Linha exibida no corpo da tabela quando ela ainda não foi carregada ou a consulta não trouxe registros. */
export function LinhaVazia({ colunas, carregada, carregando }: { colunas: number; carregada: boolean; carregando: boolean }) {
  return (
    <tr>
      <td colSpan={colunas} className="table-empty">
        {carregando
          ? "Carregando..."
          : carregada
            ? "Nenhum registro encontrado."
            : "Faça uma busca ou clique em TODOS para carregar os registros."}
      </td>
    </tr>
  );
}
