import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "../components/Layout";
import { CadastroPage } from "../pages/Cadastro";
import { DashboardPage } from "../pages/Dashboard";
import { EmBrevePage } from "../pages/EmBreve";
import { NotaFiscalPage } from "../pages/NotaFiscal";
import type { CadastroConfig } from "../types/cadastros";

const CADASTROS: Record<string, CadastroConfig> = {
  fornecedores: {
    titulo: "Fornecedores",
    singular: "Fornecedor",
    subtitulo: "Manter fornecedores",
    endpoint: "fornecedores",
    campos: [
      { name: "razao_social", label: "Razão Social", required: true, maxLength: 255 },
      { name: "nome_fantasia", label: "Nome Fantasia", maxLength: 255 },
      { name: "cnpj", label: "CNPJ", placeholder: "00.000.000/0000-00", maxLength: 18 },
    ],
  },
  clientes: {
    titulo: "Clientes",
    singular: "Cliente",
    subtitulo: "Manter clientes",
    endpoint: "clientes",
    campos: [
      { name: "nome", label: "Nome", required: true, maxLength: 255 },
      { name: "cpf_cnpj", label: "CPF/CNPJ", maxLength: 18 },
    ],
  },
  faturados: {
    titulo: "Faturados",
    singular: "Faturado",
    subtitulo: "Manter faturados (quem recebe a nota fiscal)",
    endpoint: "faturados",
    campos: [
      { name: "nome_completo", label: "Nome Completo", required: true, maxLength: 255 },
      { name: "cpf", label: "CPF", placeholder: "000.000.000-00", maxLength: 14 },
    ],
  },
  "tipos-receita": {
    titulo: "Tipos de Receita",
    singular: "Tipo de Receita",
    subtitulo: "Manter tipos de receita",
    endpoint: "tipos-receita",
    campos: [{ name: "nome", label: "Nome", required: true, maxLength: 160 }],
  },
  "tipos-despesa": {
    titulo: "Tipos de Despesa",
    singular: "Tipo de Despesa",
    subtitulo: "Categorias usadas pela IA para classificar as despesas das notas fiscais",
    endpoint: "tipos-despesa",
    campos: [
      { name: "grupo", label: "Categoria", required: true, maxLength: 120, placeholder: "Ex.: MANUTENÇÃO E OPERAÇÃO" },
      { name: "nome", label: "Subcategoria", required: true, maxLength: 160 },
    ],
  },
};

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="nota-fiscal" element={<NotaFiscalPage />} />
        {Object.entries(CADASTROS).map(([slug, config]) => (
          <Route key={slug} path={`cadastros/${slug}`} element={<CadastroPage key={slug} config={config} />} />
        ))}
        <Route
          path="financeiro/contas-a-pagar"
          element={<EmBrevePage titulo="Contas a Pagar" descricao="Registrar contas a pagar com despesas e parcelas" />}
        />
        <Route
          path="financeiro/contas-a-receber"
          element={<EmBrevePage titulo="Contas a Receber" descricao="Registrar contas a receber com receitas e parcelas" />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
