# Chatbot WhatsApp AI (RAG)

![Testes](https://github.com/ThiagoHMDornelas/chatbot_whatsapp_ai/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688)
![LangChain](https://img.shields.io/badge/LangChain-1.2-1C3C3C)
![Evolution API](https://img.shields.io/badge/Evolution%20API-2.3.7-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Chatbot de atendimento para WhatsApp com **IA generativa e RAG** (Retrieval-Augmented Generation). O projeto simula o **suporte técnico de um notebook**: as respostas são geradas a partir de uma base de conhecimento (manuais em PDF/TXT) indexada em um banco vetorial, mantendo o contexto da conversa por contato.

## Sumário

- [Visão geral](#visão-geral)
- [Como funciona](#como-funciona)
  - [Agrupamento de mensagens (debounce)](#agrupamento-de-mensagens-debounce)
- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Configuração](#configuração)
- [Base de conhecimento (RAG)](#base-de-conhecimento-rag)
- [Executar com Docker](#executar-com-docker)
  - [Passo a passo (via shell)](#passo-a-passo-via-shell--powershell)
  - [Criar instância, conectar e configurar o webhook via API](#criar-instância-conectar-e-configurar-o-webhook-via-api)
  - [Usando o Docker Desktop](#usando-o-docker-desktop-interface-gráfica)
  - [Problemas comuns](#problemas-comuns)
- [Segurança do webhook (WEBHOOK_TOKEN)](#segurança-do-webhook-webhook_token)
- [Executar localmente](#executar-localmente)
- [Endpoints](#endpoints)
- [Testes](#testes)
- [Licença](#licença)

## Visão geral

O **Chatbot WhatsApp AI** recebe mensagens pelo WhatsApp, interpreta a dúvida do cliente consultando uma base de conhecimento (por padrão, o manual de um notebook) e responde de forma objetiva. A arquitetura separa responsabilidades:

- A **Evolution API** conecta o número de WhatsApp e entrega os eventos por *webhook*.
- O **bot** (FastAPI) recebe o webhook, agrupa mensagens enviadas em sequência e responde via RAG.
- O **Redis** guarda a memória de cada conversa e o *buffer* de mensagens (agrupamento com *debounce*).
- O **PostgreSQL** é usado pela Evolution API para persistir instâncias e dados.

## Como funciona

```
Cliente (WhatsApp)
      │  envia mensagem
      ▼
Evolution API ──► POST /webhook ──► Bot (FastAPI)
      ▲                                  │
      │                                  ├─ agrupa mensagens (buffer + debounce no Redis)
      │                                  ├─ recupera contexto (memória no Redis)
      │                                  ├─ consulta o vectorstore (RAG sobre os manuais)
      │                                  └─ gera a resposta (OpenAI)
      └──────────── envia resposta ◄─────┘
```

1. O cliente envia uma ou mais mensagens no WhatsApp.
2. A Evolution API dispara o evento `MESSAGES_UPSERT` para o webhook do bot (`POST /webhook`).
3. O bot adiciona a mensagem a um *buffer* no Redis e reinicia um *debounce* de alguns segundos — mensagens enviadas em sequência são agrupadas em uma única pergunta.
4. A pergunta é enviada para a *chain* RAG, que contextualiza com o histórico da conversa, busca os trechos relevantes no vectorstore e gera a resposta com o modelo da OpenAI.
5. A resposta é enviada de volta ao cliente pela Evolution API.

### Agrupamento de mensagens (debounce)

Para não responder a cada mensagem fragmentada, o bot aguarda um período de silêncio (`DEBOUNCE_SECONDS`) e junta tudo o que chegou nesse intervalo em **uma única pergunta**. Esse tempo é um equilíbrio:

- **Janela maior** (ex.: 10s): agrupa melhor mensagens digitadas em pedaços, mas a resposta demora mais e perguntas distintas enviadas em sequência podem virar uma só.
- **Janela menor** (ex.: 3s): resposta mais rápida e perguntas separadas, mas fragmentos digitados devagar podem gerar respostas separadas.

> O bot **sempre espera o tempo inteiro de silêncio** antes de responder — por isso um valor muito alto deixa a conversa lenta. O padrão é **5s** (bom equilíbrio). Para ajustar, mude `DEBOUNCE_SECONDS` no `.env` e recrie o bot (`docker compose up -d`).

## Funcionalidades

- Atendimento automático no WhatsApp com IA (OpenAI)
- **RAG** sobre documentos próprios (PDF e TXT) usando Chroma (banco vetorial)
- **Memória de conversa** por contato (histórico persistido no Redis)
- **Agrupamento de mensagens** com *debounce* (evita responder a cada mensagem fragmentada)
- Descarta grupos, status e mensagens enviadas pelo próprio bot
- Recebe e responde de forma assíncrona (FastAPI + httpx)
- Fluxo completo orquestrado com Docker Compose (bot + Evolution API + PostgreSQL + Redis)

## Tecnologias

- Python 3.11
- FastAPI + Uvicorn
- LangChain (RAG, memória de conversa e prompts)
- OpenAI (embeddings + chat)
- Chroma (banco de dados vetorial)
- Evolution API v2.3.7 (integração WhatsApp)
- Redis (memória e *buffer*)
- PostgreSQL (persistência da Evolution API)
- Docker e Docker Compose
- pytest (testes) e flake8 (lint)
- GitHub Actions (CI)

## Estrutura do projeto

```
chatbot_whatsapp_ai/
├── app.py                # servidor FastAPI: webhook do WhatsApp e health check
├── message_buffer.py     # buffer de mensagens + debounce (Redis)
├── chains.py             # montagem da chain RAG (retriever + LLM)
├── vectorstore.py        # carregamento/indexação dos documentos (Chroma)
├── memory.py             # histórico de conversa por sessão (Redis)
├── evolution_api.py      # envio de mensagens pela Evolution API (httpx)
├── prompts.py            # prompts de contextualização e de resposta
├── config.py             # leitura das variáveis de ambiente
├── rag_files/            # base de conhecimento (PDF/TXT) — inclui o manual de exemplo
├── tests/                # testes automatizados (pytest)
├── .github/workflows/    # pipeline de CI (GitHub Actions)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore         # arquivos ignorados no build da imagem
├── .env.example          # exemplo de variáveis de ambiente
├── pytest.ini
├── requirements.txt
└── requirements_dev.txt
```

## Pré-requisitos

- Docker Desktop instalado e em execução (engine)
- Docker Compose (já vem com o Docker Desktop)
- Git instalado (para clonar o repositório)
- Um editor de texto (para criar o `.env`)
- Uma chave de API da OpenAI (`OPENAI_API_KEY`)
- Um navegador (para o Manager da Evolution API)

## Configuração

Copie o arquivo de exemplo e preencha os valores:

    copy .env.example .env        # Windows
    cp .env.example .env          # Linux/macOS

Principais variáveis:

| Variável | Descrição |
|---|---|
| `OPENAI_API_KEY` | Chave da API da OpenAI (obrigatória) |
| `OPENAI_MODEL_NAME` | Modelo de chat (padrão `gpt-4o-mini`) |
| `OPENAI_MODEL_TEMPERATURE` | Temperatura do modelo (padrão `0`) |
| `AI_CONTEXTUALIZE_PROMPT` / `AI_SYSTEM_PROMPT` | Prompts de contextualização e de resposta (opcionais — há padrões no `config.py`) |
| `VECTOR_STORE_PATH` | Caminho do banco vetorial (padrão `vectorstore`) |
| `RAG_FILES_DIR` | Pasta com os documentos da base (padrão `rag_files`) |
| `EVOLUTION_API_URL` | URL da Evolution API (no Compose: `http://evolution-api:8080`) |
| `EVOLUTION_INSTANCE_NAME` | Nome da instância/canal no WhatsApp |
| `AUTHENTICATION_API_KEY` | Chave de autenticação da Evolution API |
| `CACHE_REDIS_URI` | Conexão do Redis usada pelo bot e pela Evolution |
| `BUFFER_KEY_SUFIX` / `DEBOUNCE_SECONDS` / `BUFFER_TTL` | Ajustes do buffer de mensagens |
| `WEBHOOK_TOKEN` | Token opcional para validar o `/webhook` (se vazio, não valida) |

> O `.env` contém segredos e **não é versionado**. Use sempre o `.env.example` como referência.

## Base de conhecimento (RAG)

O bot responde com base nos documentos presentes na pasta `rag_files/`. Por padrão, já existe um manual de exemplo (`rag_files/laptop_manual.pdf`) que simula o **suporte de um notebook** — é só subir o projeto e conversar com o bot.

Para usar sua própria documentação:

1. Coloque arquivos `.pdf` ou `.txt` dentro de `rag_files/`.
2. Na **primeira execução** (banco vetorial vazio), o bot lê os documentos, divide em trechos (*chunks* de 1000 caracteres com sobreposição de 200) e indexa no Chroma.
3. O índice é persistido em `vectorstore/` (no Docker, no volume `./vectorstore_data`). Nas execuções seguintes, ele é reaproveitado — não há reindexação desnecessária.

**Reindexar** (depois de adicionar ou trocar documentos):

    docker compose down
    Remove-Item -Recurse -Force .\vectorstore_data    # Windows
    rm -rf ./vectorstore_data                          # Linux/macOS
    docker compose up -d

Assim o banco vetorial é reconstruído a partir dos arquivos atuais de `rag_files/`.

## Executar com Docker

A forma recomendada de rodar o projeto completo (bot + Evolution API + PostgreSQL + Redis). Sobe tudo já configurado pelo Docker Compose.

> **Importante:** o Docker Desktop sozinho **não** faz o setup inicial. Ele é o *engine* + painel de gerenciamento. Criar o `.env` e rodar `docker compose up --build` são feitos pelo **terminal**; criar a instância/QR/webhook da Evolution API é feito pelo **navegador** (Manager) ou pela API. O Docker Desktop é ótimo para acompanhar logs, iniciar/parar e abrir um terminal dentro do container **depois** que a stack subiu.

Portas utilizadas: `8090` (bot), `8080` (Evolution API), `5432` (PostgreSQL) e `6379` (Redis) — precisam estar livres.

### Passo a passo (via shell / PowerShell)

**1. Clone o repositório**

```powershell
git clone https://github.com/ThiagoHMDornelas/chatbot_whatsapp_ai.git
cd chatbot_whatsapp_ai
```

> O `git clone` cria a pasta `chatbot_whatsapp_ai` dentro da pasta atual, e o `cd` entra nela. Se você **já está dentro** da pasta do projeto, **pule o `cd`**; se clonou com outro nome (`git clone <url> meu-nome`), use `cd meu-nome`. Para conferir onde está: `Get-Location`.

**2. Crie o arquivo de ambiente**

```powershell
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
```

> Atenção: se você **já tem** um `.env` na pasta, o comando acima vai **sobrescrevê-lo** e você perde as chaves. Nesse caso, **pule este passo** e apenas edite o `.env` existente.

Abra o `.env` em um editor e preencha **no mínimo**:

| Variável | O que colocar |
|---|---|
| `OPENAI_API_KEY` | sua chave da OpenAI (`sk-...`) |
| `AUTHENTICATION_API_KEY` | uma chave secreta qualquer (será a chave global da Evolution API) |
| `EVOLUTION_INSTANCE_NAME` | nome da instância/canal, ex.: `ChatPyCode` |

Mantenha `EVOLUTION_API_URL=http://evolution-api:8080` e `CACHE_REDIS_URI=redis://redis:6379/6` (hostnames da rede interna do Docker).

> Dica: se a chave tiver caracteres como `!`, `@` ou `#`, mantenha o valor **entre aspas** no `.env` (ex.: `AUTHENTICATION_API_KEY='!minhaChave@'`).

**3. Suba a stack.** Na primeira execução o Docker baixa as imagens (Evolution API, PostgreSQL e Redis) e compila a imagem do bot — isso pode levar alguns minutos:

```powershell
docker compose up --build -d
```

**4. Confira os containers:**

```powershell
docker compose ps
```

Espere `postgres` e `redis` como `healthy` e `bot`/`evolution-api` como `Up`.

| Serviço | Container | Porta | Acesso |
|---|---|---|---|
| `bot` | `bot` | 8090 → 8000 | `http://localhost:8090` |
| `evolution-api` | `evolution_api` | 8080 | `http://localhost:8080` |
| `postgres` | `postgres_chat` | 5432 | — |
| `redis` | `redis` | 6379 | — |

> O bot expõe a porta **8090** no host (mapeada para a `8000` do container). Se ela estiver em uso, troque o mapeamento no `docker-compose.yml` — ex.: `8091:8000` (host:container) — e acesse em `http://localhost:8091`. O endereço interno usado pelo webhook **não muda**: continua `http://bot:8000/webhook` (porta do container).

**5. Valide a Evolution API:**

```powershell
Invoke-RestMethod http://localhost:8080/
```

Deve retornar uma resposta de boas-vindas com `status: 200` e a versão. Também é possível abrir o **Manager** no navegador:

    http://localhost:8080/manager

**6. Crie a instância e conecte o WhatsApp (pelo Manager):**

1. Abra `http://localhost:8080/manager`
2. Crie uma instância com o **mesmo nome** definido em `EVOLUTION_INSTANCE_NAME` (ex.: `ChatPyCode`) e preencha:

   - **Canal / Channel**: escolha **WhatsApp** (integração **Baileys**, via QR Code). **Não** use "WhatsApp Business / Cloud API" — esse exige conta Meta Business e configuração à parte.
   - **Token**: **mantenha o valor já preenchido** (ou deixe em branco) — é o token da instância. O bot **não** usa esse token; ele se autentica pela chave global (`AUTHENTICATION_API_KEY` do `.env`).
   - **Number**: **deixe em branco** (só é usado na integração WhatsApp Business / Cloud API).

3. Clique em **Save** para criar a instância. A tela de cadastro **não** mostra o QR Code — ele aparece **depois**, na lista de instâncias: clique na instância (ou na ação de **conectar / QR Code**).
4. Leia o **QR Code** com o WhatsApp que fará o atendimento.

> Se o Manager não exibir o QR Code, obtenha-o pela API: `Invoke-RestMethod -Uri "http://localhost:8080/instance/connect/<instancia>" -Headers @{ apikey = "<AUTHENTICATION_API_KEY>" }` — o QR vem em `base64`.

> **Sobre o número conectado:** ao ler o QR Code, a Evolution API passa a operar o **mesmo número do celular** como *dispositivo vinculado* (multidispositivo, igual ao WhatsApp Web). Assim, toda mensagem recebida aparece **no celular e também chega ao bot**, e as respostas do bot saem **por esse mesmo número**. O bot ignora mensagens enviadas por você (`fromMe`), então não responde a si mesmo. Para separar o atendimento automático do uso pessoal, use **outro número** e crie uma nova instância.

**7. Configure o webhook da instância** (no Manager, no **menu à esquerda → Events**):

- **Enabled**: ative o webhook
- **URL**: `http://bot:8000/webhook` (endereço do bot dentro da rede Docker). Se você definiu `WEBHOOK_TOKEN` no `.env`, use `http://bot:8000/webhook?token=<valor>`.
- **Webhook by events**: desligado (*off*)
- **Events**: marque apenas `MESSAGES_UPSERT`
- Clique em **Save**

**8. Valide o bot:**

```powershell
Invoke-RestMethod http://localhost:8090/health
```

Esperado: `{"status":"ok"}`.

**9. Teste o atendimento:**

1. Envie uma mensagem de texto para o número conectado (ex.: *"Como ligo o notebook?"*)
2. O `debounce` é de ~5s: mensagens enviadas em sequência geram **uma** resposta. Aguarde.
3. Acompanhe o processamento pelos logs:

```powershell
docker compose logs -f bot
```

Você verá linhas `[BUFFER]` (mensagem no buffer, agrupamento e envio da resposta). Se o bot responder com base no manual, o **RAG está funcionando** — na primeira execução o manual é indexado automaticamente.

**10. Comandos úteis:**

```powershell
docker compose logs -f bot            # logs do bot
docker compose logs -f evolution-api  # logs da Evolution API
docker compose restart bot            # reinicia o bot
docker compose down                   # para e remove os containers
docker compose down -v                # remove também os volumes (banco/cache/RAG)
```

### Criar instância, conectar e configurar o webhook via API

Alternativa ao Manager (útil para automatizar ou depurar). Defina as variáveis no terminal usando os valores do seu `.env`:

```powershell
$apiKey   = "<valor de AUTHENTICATION_API_KEY do .env>"
$instance = "<valor de EVOLUTION_INSTANCE_NAME do .env>"

# 1) Health check
Invoke-RestMethod http://localhost:8080/

# 2) Criar a instância
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/instance/create" `
  -Headers @{ apikey = $apiKey } -ContentType "application/json" `
  -Body (@{ instanceName = $instance; qrcode = $true; integration = "WHATSAPP-BAILEYS" } | ConvertTo-Json)

# 3) Obter o QR Code para conectar
Invoke-RestMethod -Uri "http://localhost:8080/instance/connect/$instance" -Headers @{ apikey = $apiKey }

# 4) Conferir o estado da conexão (deve ficar "open")
Invoke-RestMethod -Uri "http://localhost:8080/instance/connectionState/$instance" -Headers @{ apikey = $apiKey }

# 5) Configurar o webhook
$body = @{
  webhook = @{
    enabled         = $true
    url             = "http://bot:8000/webhook"
    webhookByEvents = $false
    webhookBase64   = $false
    events          = @("MESSAGES_UPSERT")
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://localhost:8080/webhook/set/$instance" `
  -Headers @{ apikey = $apiKey } -ContentType "application/json" -Body $body

# 6) Conferir o webhook configurado
Invoke-RestMethod -Uri "http://localhost:8080/webhook/find/$instance" -Headers @{ apikey = $apiKey }
```

> Se você definiu `WEBHOOK_TOKEN` no `.env`, no passo 5 use `url = "http://bot:8000/webhook?token=<valor>"`.

> O QR Code retornado vem no formato `base64`. O jeito mais simples de ler é pelo **Manager** (passos 6 e 7 acima); alternativamente, salve o `base64` em um arquivo `.png`.

### Usando o Docker Desktop (interface gráfica)

Depois que a stack estiver no ar (passo 3), o Docker Desktop ajuda a operar. Na aba **Containers** você verá o grupo `chatbot_whatsapp_ai` com os quatro serviços (`bot`, `evolution-api`, `postgres`, `redis`):

- **Logs**: clique em um container → aba *Logs* (equivale a `docker compose logs`).
- **Start / Stop / Restart**: botões no topo do container ou do grupo.
- **Terminal no container**: botão *Exec* (útil para depurar dentro do container).
- **Abrir no navegador**: clique na porta publicada (ex.: `8090:8000` ou `8080:8080`).
- **Limpeza**: *Delete* remove o grupo de containers; em **Volumes** você apaga o banco/cache/RAG.

O que **não** dá para fazer pela interface gráfica (precisa do terminal/editor/navegador):

- Criar ou editar o `.env`
- Rodar `docker compose up --build` em um clone novo
- Criar a instância, ler o QR Code e configurar o webhook da Evolution API (isso é no navegador, via Manager, ou pela API)

### Problemas comuns

- **O bot não responde**
  - Veja os logs: `docker compose logs -f bot` e `docker compose logs -f evolution-api`
  - Confira a conexão: `Invoke-RestMethod -Uri "http://localhost:8080/instance/connectionState/$instance" -Headers @{ apikey = $apiKey }` deve retornar `open`
  - Confirme o webhook: `Invoke-RestMethod -Uri "http://localhost:8080/webhook/find/$instance" -Headers @{ apikey = $apiKey }` deve apontar para `http://bot:8000/webhook` (com `?token=<valor>` se você usa `WEBHOOK_TOKEN`) e o evento `MESSAGES_UPSERT`
- **O webhook retorna `401`** → você definiu `WEBHOOK_TOKEN` no `.env`, mas a URL do webhook na Evolution não inclui o `?token=<valor>` (ou o valor está errado)
- **Aparece `Nao foi possivel pre-aquecer a chain RAG` no log** → verifique a `OPENAI_API_KEY` e se há créditos na OpenAI
- **Aparece `Connection error.` nos logs do bot** → o container não conseguiu acessar a internet (normalmente a API da OpenAI). Causa comum: **antivírus/firewall** bloqueando o Docker (também pode ser VPN ou proxy corporativo). Libere o acesso dos containers a `api.openai.com` ou desative temporariamente o bloqueio e reinicie com `docker compose restart bot`. Para diagnosticar: `docker compose exec bot python -c "import httpx; print(httpx.get('https://api.openai.com/v1/models', timeout=10).status_code)"`
- **Erro de porta em uso** (`8090`, `8080`, `5432`, `6379`) → pare o serviço que ocupa a porta ou ajuste o mapeamento no `docker-compose.yml`
- **A Evolution API cai depois de um tempo** → confira `CONFIG_SESSION_PHONE_VERSION`; a versão do WhatsApp Web muda com frequência e pode ser necessário atualizá-la
- **Reindexar o RAG** (após trocar os documentos) → `docker compose down`, apague a pasta `vectorstore_data/` e rode `docker compose up -d`

## Segurança do webhook (WEBHOOK_TOKEN)

O endpoint `POST /webhook` é a **porta de entrada** do bot: é por ele que a Evolution API avisa quando chega uma mensagem. Como esse endereço aceita requisições HTTP, **qualquer pessoa que consiga alcançá-lo pode enviar um evento falso** — e o bot, ao receber, consultaria a OpenAI (gastando seus tokens) e enviaria uma resposta pelo WhatsApp.

Para proteger isso, o bot aceita um **token de segurança** definido em `WEBHOOK_TOKEN`:

- **`WEBHOOK_TOKEN` vazio (padrão)** → o webhook fica **aberto**, sem validação. Serve para uso local/desenvolvimento.
- **`WEBHOOK_TOKEN` definido** → o bot só aceita requisições que tragam o token correto. Sem o token (ou com o valor errado), responde **HTTP 401** e ignora a requisição.

O token pode ser enviado de duas formas:

- **Na URL** (mais simples): `http://bot:8000/webhook?token=<valor>`
- **No cabeçalho HTTP**: `X-Webhook-Token: <valor>`

### Como ativar

1. Defina um segredo no `.env` (qualquer texto difícil de adivinhar):

       WEBHOOK_TOKEN=um-segredo-bem-grande-e-dificil

2. Recrie o bot para carregar a variável:

       docker compose up -d

3. Atualize a **URL do webhook na Evolution API** para incluir o token (Manager → menu à esquerda → **Events**, ou pela API):

       http://bot:8000/webhook?token=um-segredo-bem-grande-e-dificil

   Pela API, use o mesmo `webhook/set` do passo 7, trocando apenas o campo `url` (veja [Criar a instância e conectar via API](#criar-instância-conectar-e-configurar-o-webhook-via-api)).

4. Pronto. A partir daí, **só a Evolution** (que conhece o token) consegue acionar o bot. Requisições sem o token recebem **401**.

> **O token é um segredo:** não coloque no código nem no Git (o `.env` já é ignorado). Se ele vazar, troque o valor no `.env`, recrie o bot e atualize a URL na Evolution.

> **Alternativa sem token:** se preferir não usar, basta **não expor** a porta do bot para fora — por exemplo, mapeando apenas para o host local (`"127.0.0.1:8090:8000"`) ou removendo a publicação da porta. Assim o webhook só é acessível de dentro da rede do Docker.

## Executar localmente

Caso queira rodar o bot fora do Docker (mantendo a infraestrutura nos containers):

1. Suba apenas os serviços de apoio:

       docker compose up -d evolution-api postgres redis

2. No `.env`, aponte `EVOLUTION_API_URL` para `http://localhost:8080` e `CACHE_REDIS_URI` para `redis://localhost:6379/6`.

3. Instale as dependências e rode o servidor:

       python -m venv .venv
       .venv\Scripts\activate        # Windows
       pip install -r requirements.txt
       uvicorn app:app --host 0.0.0.0 --port 8000

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/webhook` | Recebe os eventos da Evolution API (mensagens recebidas) |
| GET | `/health` | Verificação de saúde do serviço |

## Testes

A suíte cobre a interpretação dos eventos de webhook, o fluxo de recebimento de mensagens (buffer/debounce), o carregamento de documentos, a memória de sessão e o envio pela Evolution API — tudo com *mocks*, sem chamadas reais à OpenAI/Redis/WhatsApp:

    pytest

O **lint** do código é feito com `flake8` (configuração em `.flake8`):

    flake8

O pytest e o flake8 também rodam automaticamente a cada `push` e `pull request` via **GitHub Actions** (`.github/workflows/tests.yml`). O resultado é exibido no badge no topo deste README.

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
