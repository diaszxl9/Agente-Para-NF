import type { ReactNode } from "react";
import type { NotaFiscalExtraida } from "../types/notaFiscal";
import { formatCurrency, formatDate, formatQuantity } from "../utils/format";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd className={value ? undefined : "muted"}>{value ?? "Não informado"}</dd>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="data-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export function ExtractedView({ dados }: { dados: NotaFiscalExtraida }) {
  const { fornecedor, faturado, nota_fiscal: nf, itens, parcelas, despesas } = dados;

  return (
    <div className="data-sections">
      <Section title="Fornecedor">
        <dl className="fields">
          <Field label="Razão Social" value={fornecedor.razao_social} />
          <Field label="Fantasia" value={fornecedor.fantasia} />
          <Field label="CNPJ" value={fornecedor.cnpj} />
        </dl>
      </Section>

      <Section title="Faturado">
        <dl className="fields">
          <Field label="Nome Completo" value={faturado.nome_completo} />
          <Field label="CPF" value={faturado.cpf} />
        </dl>
      </Section>

      <Section title="Nota Fiscal">
        <dl className="fields">
          <Field label="Número" value={nf.numero} />
          <Field label="Data de Emissão" value={formatDate(nf.data_emissao)} />
        </dl>
      </Section>

      <Section title="Produtos">
        {itens.length === 0 ? (
          <p className="muted">Nenhum produto identificado.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Descrição</th>
                  <th className="num">Quantidade</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item, i) => (
                  <tr key={i}>
                    <td>{item.descricao}</td>
                    <td className="num">{formatQuantity(item.quantidade) ?? <span className="muted">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Financeiro">
        <dl className="fields">
          <Field label="Quantidade de Parcelas" value={String(parcelas.length)} />
          <Field label="Valor Total" value={formatCurrency(dados.valor_total)} />
        </dl>
        {parcelas.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Parcela</th>
                  <th>Vencimento</th>
                  <th className="num">Valor</th>
                </tr>
              </thead>
              <tbody>
                {parcelas.map((p) => (
                  <tr key={p.numero}>
                    <td>{p.numero}</td>
                    <td>{formatDate(p.data_vencimento) ?? <span className="muted">Não informado</span>}</td>
                    <td className="num">{formatCurrency(p.valor) ?? <span className="muted">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Classificação">
        {despesas.length === 0 ? (
          <p className="muted">Despesa não classificada.</p>
        ) : (
          <div className="badges">
            {despesas.map((d, i) => (
              <div className="class-badge" key={i}>
                <strong>{d.categoria ?? "Sem categoria"}</strong>
                {d.subcategoria && <span>{d.subcategoria}</span>}
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
