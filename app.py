import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from config import WEBHOOK_TOKEN
from message_buffer import buffer_message, get_rag_chain


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        get_rag_chain()
    except Exception as error:
        logger.warning('Nao foi possivel pre-aquecer a chain RAG: %s', error)
    yield


app = FastAPI(title='Chatbot WhatsApp AI', lifespan=lifespan)


def extract_text_message(payload: dict):
    """Extrai (chat_id, texto) de um webhook do Evolution API.

    Retorna (None, None) quando nao for uma mensagem de texto valida
    (evento sem mensagem, mensagem enviada pelo proprio bot, grupos ou status).
    """
    data = payload.get('data') or {}
    key = data.get('key') or {}

    chat_id = key.get('remoteJid')
    if not chat_id or key.get('fromMe'):
        return None, None

    if chat_id.endswith('@g.us') or chat_id == 'status@broadcast':
        return None, None

    message = data.get('message') or {}
    text = message.get('conversation') or (message.get('extendedTextMessage') or {}).get('text')

    if not text:
        return None, None

    return chat_id, text.strip()


def webhook_autorizado(request: Request) -> bool:
    if not WEBHOOK_TOKEN:
        return True
    token = request.query_params.get('token') or request.headers.get('x-webhook-token')
    return token == WEBHOOK_TOKEN


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.post('/webhook')
async def webhook(request: Request):
    if not webhook_autorizado(request):
        raise HTTPException(status_code=401, detail='unauthorized')

    payload = await request.json()

    event = payload.get('event')
    if event and event != 'messages.upsert':
        return {'status': 'ignored', 'event': event}

    chat_id, text = extract_text_message(payload)
    if chat_id and text:
        await buffer_message(chat_id=chat_id, message=text)

    return {'status': 'ok'}
