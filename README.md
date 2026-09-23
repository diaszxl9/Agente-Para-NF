# Gestão Financeira + Extração de Notas Fiscais com IA

Aplicação web para extrair dados de notas fiscais em PDF com o Google Gemini, classificar a despesa e
visualizar o resultado (formatado e em JSON). Base para o módulo financeiro (cadastros, contas a pagar/receber).

- **Frontend:** React + TypeScript + Vite + React Router (`frontend/`)
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy (`backend/`)
- **IA:** Google Gemini (chave somente no backend)
- **Banco principal:** MySQL · **MongoDB:** opcional (documentos brutos)

```
Frontend (React) --HTTP/REST--> FastAPI --> MySQL
                                   |------> Gemini
                                   '------> MongoDB (opcional)
```

## Como rodar

Pré-requisitos: Python 3.11+, Node 20+, MySQL 8 e uma chave do Gemini.

Os comandos abaixo são para **PowerShell (Windows)**, sempre a partir da raiz do projeto. Os equivalentes para
Linux/macOS estão logo depois.

### Primeira vez (instalação)

```powershell
# 1) Configuração: copie o .env e preencha GEMINI_API_KEY e DATABASE_URL
Copy-Item .env.example .env
# No MySQL: CREATE DATABASE gestao_financeira CHARACTER SET utf8mb4;

# 2) Backend: cria o ambiente virtual e instala as dependências
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..

# 3) Frontend: instala as dependências
cd frontend
npm install
cd ..
```

### Dia a dia (iniciar o projeto)

Abra **dois terminais** na raiz do projeto e confira se o MySQL está ligado.

```powershell
# Terminal 1: backend em http://localhost:8000 (documentação em /docs)
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
# Terminal 2: frontend em http://localhost:5173
cd frontend
npm run dev
```

Chamar o Python do `.venv` diretamente (`.venv\Scripts\python.exe -m ...`) dispensa ativar o ambiente virtual. Se
preferir ativar, use `.venv\Scripts\Activate.ps1`. Depois disso, `uvicorn app.main:app --reload --port 8000` também
funciona. Se o PowerShell bloquear o script, rode uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Linux/macOS

```bash
cp .env.example .env
cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# Para iniciar (um terminal para cada)
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

### Observações

- As tabelas e as categorias de despesa iniciais são criadas automaticamente na primeira conexão com o MySQL.
- O `.env` fica na **raiz** do projeto, não em `backend/`.
- O Vite encaminha `/api` para `http://127.0.0.1:8000` (altere com `VITE_PROXY_TARGET` ou defina `VITE_API_URL`).
- Os avisos `Banco de dados indisponível` e `API_KEY não configurada` na inicialização não impedem o backend de subir:
  o primeiro indica que o MySQL está desligado ou que o `DATABASE_URL` está errado; o segundo está explicado em
  [Autenticação da API](#autenticação-da-api).

### Problemas comuns

| Erro | Causa | Solução |
| --- | --- | --- |
| `No module named 'fastapi'` / `uvicorn` não reconhecido | Dependências não instaladas no `.venv` | `cd backend` e depois `.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `No module named pip` | `.venv` criado incompleto | `.venv\Scripts\python.exe -m ensurepip --upgrade` e instale as dependências de novo |
| `No module named 'app'` | Comando executado fora de `backend/` | Rode o uvicorn de dentro da pasta `backend` |
| Porta 8000 em uso | Outro backend já está rodando | Feche o outro terminal ou use `--port 8001` (e ajuste `VITE_PROXY_TARGET`) |

## Autenticação da API

Por padrão (`API_KEY` vazia no `.env`) a API fica **aberta**, sem autenticação — adequado apenas para uso local. Para
protegê-la (recomendado antes de expor o backend em qualquer rede além do seu próprio computador), defina `API_KEY` no
`.env` da raiz; toda rota em `/api` (exceto `/api/health`) passa a exigir o header `X-API-Key` com o mesmo valor.

No frontend, defina `VITE_API_KEY` (em `frontend/.env`) com o mesmo valor para que as requisições enviem o header
automaticamente. Importante: como é uma chave compartilhada exposta no bundle do navegador, ela impede acesso casual/
scanners automatizados, mas **não substitui** um sistema de login por usuário — não é segredo perante quem tem acesso
ao frontend.

## Rate limiting da extração

`POST /api/notas-fiscais/extrair` chama a API paga do Gemini a cada requisição, então tem um limite de taxa próprio
(`RATE_LIMIT_EXTRACAO` no `.env`, padrão `20/minute`), aplicado por API key quando `API_KEY` está configurada, ou por
IP quando não está. Ao estourar o limite, a resposta é `429` e o Gemini **não é chamado**. Ajuste o valor conforme o
volume real de uso (ex.: `100/hour` para lotes maiores).

A extração (`/nota-fiscal`) **não depende do MySQL para funcionar**: se o banco estiver fora do ar, o backend usa as
categorias padrão. Já os cadastros e o dashboard exigem o MySQL.

## Fluxo da extração

`POST /api/notas-fiscais/extrair` (`multipart/form-data`, campo `arquivo`)

1. Valida o arquivo: extensão `.pdf`, tipo, assinatura `%PDF-`, não vazio, tamanho máximo (`MAX_UPLOAD_MB`).
2. Monta o prompt com as **categorias de despesa ativas cadastradas** (`tipos_despesa`) e envia o PDF ao Gemini
   (temperatura 0, resposta em JSON).
3. A resposta **nunca é confiada diretamente**: é parseada (com 1 nova tentativa se vier JSON inválido), validada com
   Pydantic e sanitizada (CNPJ/CPF, datas, números, textos). Categorias fora da lista cadastrada são descartadas.
4. Regras aplicadas no backend: campo não encontrado = `null`; sem parcelas informadas = 1 parcela com o valor total;
   avisos são devolvidos quando há inconsistências (CNPJ/CPF com dígito verificador inválido, soma das parcelas
   diferente do total, categoria não cadastrada etc.).
5. Resposta: `{ dados, avisos, arquivo, modelo, documento_id }`. O JSON de `dados` segue a estrutura do enunciado, com o
   campo extra `subcategoria` em `despesas`.

Com `MONGODB_URL` definido, o documento processado (nome, hash, resposta bruta do Gemini, JSON final, status) é gravado
na coleção `documentos_nf`. Falhas do Mongo são ignoradas — o MySQL segue como fonte principal.

## Modelo de dados (MySQL)

`fornecedores`, `clientes`, `faturados`, `tipos_despesa` (categoria = `grupo`, subcategoria = `nome`), `tipos_receita`,
`notas_fiscais`, `itens_nota`, `contas_pagar`, `contas_receber`, `parcelas` (de conta a pagar **ou** a receber),
`conta_pagar_despesas`, `conta_receber_receitas`. Com PKs, FKs, índices, constraints e timestamps.

Nenhum cadastro é excluído fisicamente: a API não tem `DELETE`; existem `PATCH /{id}/inativar` e `/{id}/reativar`.

## Status por fase

| Fase | Escopo | Situação |
| --- | --- | --- |
| 1 | Upload → FastAPI → Gemini → classificação → JSON → tela | Implementada |
| 2 | CRUD de Fornecedores, Clientes, Faturados, Tipos de Despesa/Receita (inativação lógica) | Implementada |
| 3 | Contas a pagar/receber, parcelas | Tabelas prontas; telas/endpoints pendentes |
| 4 | Nota extraída → preencher conta a pagar | Pendente |

## Testes

```powershell
# Backend: SQLite em memória, Gemini simulado
cd backend
.venv\Scripts\python.exe -m pytest
cd ..

# Frontend: typecheck + build
cd frontend
npm run build
cd ..
```
