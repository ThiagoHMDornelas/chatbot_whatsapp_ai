# AGENTS.md — chatbot_whatsapp_ai

Chatbot de atendimento para WhatsApp com RAG: entrega via Evolution API, respostas geradas com LangChain/OpenAI a partir de manuais em `rag_files/` (PDF/TXT) indexados no Chroma. FastAPI 0.135.1 · LangChain 1.2.12 / LangGraph 1.1.2 · ChromaDB 1.5.9 · Redis (buffer + memória) · Evolution API v2.3.7 · Python 3.11 · Docker.

## Contexto em camadas
`SOUL.md` (regras globais do agente) → `AGENTS.md` da pasta da linguagem (regras comuns) → este arquivo (particularidades do projeto). Em conflito, vale o mais específico (este arquivo), exceto em regras de segurança/global.

## Fluxo principal

Evolution API → `POST /webhook` (autenticado por `WEBHOOK_TOKEN`) → `extract_text_message` filtra (só texto, ignora `fromMe`, grupos `@g.us`, `status@broadcast`, eventos que não `messages.upsert`) → `message_buffer.buffer_message` (debounce no Redis) → chain RAG (`chains.py`) → `evolution_api.send_whatsapp_message` → WhatsApp.

## Arquitetura

| Módulo | Papel | Particularidades |
|---|---|---|
| `app.py` | FastAPI (`/webhook`, `/health`) | `lifespan` pré-aquece a chain RAG no boot (falha loga warning, não derruba o app); auth do webhook por `?token=` ou header `x-webhook-token`; sem `WEBHOOK_TOKEN` no `.env`, webhook fica **aberto** |
| `message_buffer.py` | Debounce/agrupamento | Redis list por chat (`rpush`, TTL `BUFFER_TTL=300`); task `asyncio` por chat cancelada a cada mensagem nova (`DEBOUNCE_SECONDS=5` de silêncio); `processing_chats` (set em memória) evita reprocessamento; chain roda em `asyncio.to_thread` |
| `chains.py` | Chain RAG conversacional | `create_history_aware_retriever` + `create_stuff_documents_chain` + `create_retrieval_chain` (`langchain_classic`); `RunnableWithMessageHistory` com `session_id = chat_id`; saída em `result['answer']` |
| `memory.py` | Histórico por contato | `RedisChatMessageHistory` (`CACHE_REDIS_URI`) |
| `vectorstore.py` | Indexação/knowledge base | Chroma persistente em `VECTOR_STORE_PATH`; **auto-indexa na primeira chamada** se vazio: lê `RAG_FILES_DIR` (PDF/`PyPDFLoader`, TXT/`TextLoader`), split 1000/200, `OpenAIEmbeddings` |
| `evolution_api.py` | Envio de mensagens | `httpx` async, `POST /message/sendText/<EVOLUTION_INSTANCE_NAME>`, header `apikey`; timeout 30s |
| `config.py` | Variáveis + defaults | Todos os settings centralizados; prompts têm defaults embutidos (sobrescrevíveis por env) |
| `rag_files/` | Fonte do conhecimento | Volume do Docker compartilhado com o host |
| `tests/` + `pytest.ini` | Suíte pytest | `pythonpath = .`, `testpaths = tests` |

Configuração da instância do WhatsApp (QR Code, webhook): ver a seção de execução do README.

## Testes e lint

- Suíte obrigatória antes de entregar: **`pytest -ra --tb=short`** (exatamente como no CI); seleção pontual de testes via `-k`.
- Lint com flake8 (`.flake8`, ignora E501).
- CI (`.github/workflows/tests.yml`, Python 3.11, `ubuntu-24.04`): flake8 + pytest. Testes não exigem rede real: `OPENAI_API_KEY` no CI é placeholder `sk-ci-placeholder`.

## Banco de dados / integrações

- **PostgreSQL 15** é do lado da **Evolution API** (persistência de instâncias/mensagens/chats, `DATABASE_*` do `.env`) — o bot não usa banco relacional.
- **Redis** (`redis://redis:6379/6`) é usado por dois lados: cache da Evolution e, do bot, buffer de debounce (`BUFFER_KEY_SUFIX`) e histórico de conversa (db 0 no CI, db 6 no `.env`).
- A dependência de rede em produção: OpenAI (embeddings + LLM) e Evolution API.

## Variáveis de ambiente (.env.example)

- OpenAI: `OPENAI_API_KEY` (obrigatória), `OPENAI_MODEL_NAME` (default `gpt-4o-mini`), `OPENAI_MODEL_TEMPERATURE` (0)
- Prompts sobrescrevíveis: `AI_CONTEXTUALIZE_PROMPT`, `AI_SYSTEM_PROMPT`
- RAG: `VECTOR_STORE_PATH=vectorstore`, `RAG_FILES_DIR=rag_files`
- Evolution: `EVOLUTION_API_URL` (default `http://evolution-api:8080`), `EVOLUTION_INSTANCE_NAME`, `AUTHENTICATION_API_KEY`, `CONFIG_SESSION_PHONE_VERSION`
- Evolution PostgreSQL/Redis: `DATABASE_*`, `CACHE_REDIS_*`
- Buffer: `BUFFER_KEY_SUFIX=_msg_buffer`, `DEBOUNCE_SECONDS=5`, `BUFFER_TTL=300`
- Webhook: `WEBHOOK_TOKEN` (opcional)

## Docker e estados

- Volumes que precisam persistir: `vectorstore_data` ↔ `/app/vectorstore` (índice Chroma) e `./rag_files` ↔ `/app/rag_files`.
- Healthcheck do bot aponta para `/health`; Evolution só sobe depois de postgres/redis saudáveis.
- Trocar o domínio do bot = trocar arquivos em `rag_files/` e **limpar `vectorstore_data/`** (o auto-index só dispara com vectorstore vazio).
- Alterações no webhook, debounce e prompts exigem testes correspondentes (conferência de boundary).

## Convenções

- Secrets **sempre** em `.env` (nunca hardcode); mantenha o `.env.example` atualizado e o `.env` fora do versionamento.
- Mensagens de UI/validação em português do Brasil, revisadas (acentuação e concordância).
- Não commitar/pushar por conta própria: as alterações ficam prontas para o usuário revisar e commitar.
- Preservar encoding dos arquivos ao editar (não converter ANSI ↔ UTF-8 sem pedido explícito).
