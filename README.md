# Extração de Notas Fiscais com IA

Aplicação web que lê notas fiscais em PDF com o Google Gemini, classifica a despesa e mostra o resultado
(formatado e em JSON).

- **Frontend:** React + TypeScript + Vite (`frontend/`)
- **Backend:** Python + FastAPI + Pydantic (`backend/`)
- **IA:** Google Gemini (a API Key é informada pelo usuário na tela; o backend a usa nas chamadas e não a armazena)

```
Frontend (React) --HTTP/REST--> FastAPI --> Gemini
```

## Como testar

Credenciais de teste (somente para avaliação; configuráveis por `AUTH_USUARIO` / `AUTH_SENHA`):

| Usuário | Senha |
| --- | --- |
| `professor` | `avaliacao123` |

1. Acessar a aplicação;
2. Fazer login com as credenciais acima;
3. Informar uma Gemini API Key válida (gere uma em https://aistudio.google.com/apikey);
4. Clicar em "Validar API Key";
5. Selecionar um PDF de nota fiscal;
6. Clicar em "Extrair Dados";
7. Visualizar os dados extraídos.

O botão "Extrair Dados" só é habilitado depois que a API Key é validada. A chave fica apenas na memória da tela
(não é salva no navegador nem no servidor): ao recarregar a página ou clicar em "Sair", é preciso informá-la de novo.

## Como rodar

Pré-requisitos: Python 3.11+ e Node 20+. A chave do Gemini é informada na tela, não no `.env`.

Os comandos abaixo são para **PowerShell (Windows)**, sempre a partir da raiz do projeto. Os equivalentes para
Linux/macOS estão logo depois.

### Primeira vez (instalação)

```powershell
# 1) Configuração: copie o .env (os valores padrão já funcionam localmente)
Copy-Item .env.example .env

# 2) Backend: cria o ambiente virtual E instala todas as dependências (recria o .venv se estiver incompleto)
powershell -ExecutionPolicy Bypass -File backend\setup.ps1

# 3) Frontend: instala as dependências
cd frontend
npm install
cd ..
```

> **Por que não basta `python -m venv .venv`?** Esse comando só **cria um ambiente virtual vazio**: ele nunca instala
> pacotes. As dependências vêm do `pip install -r requirements.txt`, e o arquivo fica em `backend/`. O `setup.ps1` faz
> os dois passos, confere se o `pip` existe, roda `pip check` e importa a aplicação para provar que ficou funcional.
> Pode rodá-lo de novo sempre que quiser; ele também repara um `.venv` que ficou pela metade.

### Dia a dia (iniciar o projeto)

Abra **dois terminais** na raiz do projeto.

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
bash backend/setup.sh
cd frontend && npm install && cd ..

# Para iniciar (um terminal para cada)
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

### Observações

- O `.env` fica na **raiz** do projeto, não em `backend/`.
- O Vite encaminha `/api` para `http://127.0.0.1:8000` (altere com `VITE_PROXY_TARGET` ou defina `VITE_API_URL`).
- O aviso `API_KEY não configurada` na inicialização não impede o backend de subir; ele está explicado em
  [Autenticação da API](#autenticação-da-api).

### Variáveis de ambiente

Backend (`.env` na raiz, ou variáveis do serviço de hospedagem). Todas têm valor padrão; veja `.env.example`.

| Variável | Para que serve |
| --- | --- |
| `AUTH_USUARIO` / `AUTH_SENHA` | Credenciais de login (padrão: as de teste acima) |
| `AUTH_SECRET` | Segredo que assina as sessões. **Defina em produção** (ex.: `openssl rand -hex 32`); sem ele, as sessões caem a cada reinício do servidor |
| `AUTH_SESSAO_HORAS` | Duração da sessão de login (padrão `8`) |
| `CORS_ORIGINS` | Origem(ns) do frontend, ex.: `https://meu-front.exemplo.com` |
| `GEMINI_MODEL` | Modelo do Gemini usado na validação e na extração |
| `GEMINI_TIMEOUT_SECONDS` / `GEMINI_TEMPO_MAXIMO_SECONDS` | Limite de cada chamada ao Gemini (padrão `120`) e da extração inteira, somando retentativas (padrão `240`). O frontend espera até 260 s; se aumentar o limite total, ajuste `EXTRACTION_TIMEOUT_MS` em `frontend/src/services/notaFiscalService.ts` |
| `GEMINI_MAX_TENTATIVAS` | Tentativas em erros 5xx transitórios do Gemini (padrão `4`) |
| `MAX_UPLOAD_MB`, `RATE_LIMIT_*`, `API_KEY` | Limites e proteção opcional, descritos abaixo |

Frontend (no build): `VITE_API_URL` com a URL pública do backend quando frontend e backend estiverem em domínios
diferentes (ex.: `VITE_API_URL=https://meu-back.exemplo.com npm run build`). Localmente não é necessário.

### Problemas comuns

| Erro | Causa | Solução |
| --- | --- | --- |
| `No module named 'fastapi'` / `uvicorn` não reconhecido | Só rodou `python -m venv`, que não instala pacotes | `powershell -ExecutionPolicy Bypass -File backend\setup.ps1` |
| `No module named pip`, ou `Acesso negado` ao criar o `.venv` | Criação interrompida: antivírus/indexador/VS Code seguraram o `python.exe` recém-copiado | Feche terminais e o editor que usam o `.venv` e rode o `setup.ps1` de novo (ele apaga o `.venv` incompleto e tenta até 3 vezes). Se persistir, exclua a pasta do projeto do antivírus |
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

## Fluxo da extração

`POST /api/notas-fiscais/extrair` (`multipart/form-data`, campo `arquivo`)

1. Valida o arquivo: extensão `.pdf`, tipo, assinatura `%PDF-`, não vazio, tamanho máximo (`MAX_UPLOAD_MB`).
2. Monta o prompt com as **categorias de despesa** de `backend/app/services/categorias.py` e envia o PDF ao Gemini
   (temperatura 0, resposta em JSON).
3. A resposta **nunca é confiada diretamente**: é parseada (com 1 nova tentativa se vier JSON inválido), validada com
   Pydantic e sanitizada (CNPJ/CPF, datas, números, textos). Categorias fora da lista são descartadas.
4. Regras aplicadas no backend: campo não encontrado = `null`; sem parcelas informadas = 1 parcela com o valor total.
5. Resposta: `{ dados, arquivo, modelo }`. O JSON de `dados` segue a estrutura do enunciado, com o
   campo extra `subcategoria` em `despesas`.

## Testes

```powershell
# Backend: Gemini simulado
cd backend
.venv\Scripts\python.exe -m pytest
cd ..

# Frontend: typecheck + build
cd frontend
npm run build
cd ..
```
