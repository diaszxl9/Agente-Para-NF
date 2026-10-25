-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "TipoPessoa" AS ENUM ('CLIENTE', 'FORNECEDOR', 'FATURADO');

-- CreateEnum
CREATE TYPE "TipoClassificacao" AS ENUM ('RECEITA', 'DESPESA');

-- CreateEnum
CREATE TYPE "TipoMovimento" AS ENUM ('PAGAR', 'RECEBER');

-- CreateEnum
CREATE TYPE "Status" AS ENUM ('ATIVO', 'INATIVO');

-- CreateEnum
CREATE TYPE "SituacaoParcela" AS ENUM ('ABERTA', 'QUITADA');

-- CreateTable
CREATE TABLE "pessoas" (
    "id" SERIAL NOT NULL,
    "tipo" "TipoPessoa" NOT NULL,
    "razao_social" VARCHAR(255) NOT NULL,
    "fantasia" VARCHAR(255),
    "documento" VARCHAR(14) NOT NULL,
    "status" "Status" NOT NULL DEFAULT 'ATIVO',
    "data_cadastro" TIMESTAMPTZ(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "pessoas_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "classificacao" (
    "id" SERIAL NOT NULL,
    "tipo" "TipoClassificacao" NOT NULL,
    "descricao" VARCHAR(160) NOT NULL,
    "chave" VARCHAR(160) NOT NULL,
    "status" "Status" NOT NULL DEFAULT 'ATIVO',
    "data_cadastro" TIMESTAMPTZ(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "classificacao_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "movimentocontas" (
    "id" SERIAL NOT NULL,
    "tipo" "TipoMovimento" NOT NULL,
    "pessoa_id" INTEGER NOT NULL,
    "faturado_id" INTEGER,
    "numero_nota" VARCHAR(60),
    "data_emissao" DATE,
    "descricao" VARCHAR(500) NOT NULL,
    "valor_total" DECIMAL(14,2) NOT NULL,
    "status" "Status" NOT NULL DEFAULT 'ATIVO',
    "data_cadastro" TIMESTAMPTZ(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "movimentocontas_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "movimento_classificacao" (
    "movimento_id" INTEGER NOT NULL,
    "classificacao_id" INTEGER NOT NULL,

    CONSTRAINT "movimento_classificacao_pkey" PRIMARY KEY ("movimento_id","classificacao_id")
);

-- CreateTable
CREATE TABLE "parcelacontas" (
    "id" SERIAL NOT NULL,
    "movimento_id" INTEGER NOT NULL,
    "numero" INTEGER NOT NULL,
    "identificacao" VARCHAR(120) NOT NULL,
    "data_vencimento" DATE NOT NULL,
    "valor" DECIMAL(14,2) NOT NULL,
    "situacao" "SituacaoParcela" NOT NULL DEFAULT 'ABERTA',

    CONSTRAINT "parcelacontas_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "pessoas_tipo_documento_key" ON "pessoas"("tipo", "documento");

-- CreateIndex
CREATE UNIQUE INDEX "classificacao_tipo_chave_key" ON "classificacao"("tipo", "chave");

-- CreateIndex
CREATE INDEX "movimentocontas_tipo_idx" ON "movimentocontas"("tipo");

-- CreateIndex
CREATE INDEX "movimentocontas_pessoa_id_numero_nota_idx" ON "movimentocontas"("pessoa_id", "numero_nota");

-- CreateIndex
CREATE UNIQUE INDEX "parcelacontas_movimento_id_numero_key" ON "parcelacontas"("movimento_id", "numero");

-- AddForeignKey
ALTER TABLE "movimentocontas" ADD CONSTRAINT "movimentocontas_pessoa_id_fkey" FOREIGN KEY ("pessoa_id") REFERENCES "pessoas"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "movimentocontas" ADD CONSTRAINT "movimentocontas_faturado_id_fkey" FOREIGN KEY ("faturado_id") REFERENCES "pessoas"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "movimento_classificacao" ADD CONSTRAINT "movimento_classificacao_movimento_id_fkey" FOREIGN KEY ("movimento_id") REFERENCES "movimentocontas"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "movimento_classificacao" ADD CONSTRAINT "movimento_classificacao_classificacao_id_fkey" FOREIGN KEY ("classificacao_id") REFERENCES "classificacao"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "parcelacontas" ADD CONSTRAINT "parcelacontas_movimento_id_fkey" FOREIGN KEY ("movimento_id") REFERENCES "movimentocontas"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- Restrições de domínio (CHECK): o schema do Prisma não as declara, então ficam aqui na migration.
ALTER TABLE "pessoas" ADD CONSTRAINT "pessoas_documento_check" CHECK ("documento" ~ '^([0-9]{11}|[0-9]{14})$');
ALTER TABLE "movimentocontas" ADD CONSTRAINT "movimentocontas_valor_total_check" CHECK ("valor_total" > 0);
ALTER TABLE "parcelacontas" ADD CONSTRAINT "parcelacontas_numero_check" CHECK ("numero" >= 1);
ALTER TABLE "parcelacontas" ADD CONSTRAINT "parcelacontas_valor_check" CHECK ("valor" > 0);
