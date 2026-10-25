import { existsSync } from "node:fs";
import { defineConfig } from "prisma/config";

// Lê o DATABASE_URL do .env da raiz do projeto (o mesmo usado pelo backend). Em CI/Render, a variável já vem do ambiente.
if (!process.env.DATABASE_URL && existsSync("../.env")) {
  process.loadEnvFile("../.env");
}

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
  },
  datasource: {
    // Comandos que não acessam o banco (validate, migrate diff) funcionam mesmo sem DATABASE_URL.
    url: process.env.DATABASE_URL ?? "",
  },
});
