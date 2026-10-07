import asyncio
import logging

import redis.asyncio as redis

from chains import get_conversational_rag_chain
from config import (
    BUFFER_KEY_SUFIX,
    BUFFER_TTL,
    DEBOUNCE_SECONDS,
    REDIS_URL,
)
from evolution_api import send_whatsapp_message


logger = logging.getLogger(__name__)

debounce_tasks = {}
processing_chats = set()

_redis_client = None
_rag_chain = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def get_rag_chain():
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = get_conversational_rag_chain()
    return _rag_chain


def _buffer_key(chat_id: str) -> str:
    return f'{chat_id}{BUFFER_KEY_SUFIX}'


async def buffer_message(chat_id: str, message: str):
    redis_client = get_redis_client()
    buffer_key = _buffer_key(chat_id)

    await redis_client.rpush(buffer_key, message)
    await redis_client.expire(buffer_key, BUFFER_TTL)

    logger.info('[BUFFER] Mensagem adicionada ao buffer de %s: %s', chat_id, message)

    current_task = debounce_tasks.get(chat_id)
    if current_task and chat_id not in processing_chats:
        current_task.cancel()
        logger.info('[BUFFER] Debounce resetado para %s', chat_id)

    debounce_tasks[chat_id] = asyncio.create_task(handle_debounce(chat_id))


async def handle_debounce(chat_id: str):
    buffer_key = _buffer_key(chat_id)
    try:
        logger.info('[BUFFER] Iniciando debounce para %s', chat_id)
        await asyncio.sleep(float(DEBOUNCE_SECONDS))
        processing_chats.add(chat_id)

        redis_client = get_redis_client()
        messages = await redis_client.lrange(buffer_key, 0, -1)
        await redis_client.delete(buffer_key)

        full_message = ' '.join(messages).strip()
        if full_message:
            logger.info('[BUFFER] Enviando mensagem agrupada para %s: %s', chat_id, full_message)
            result = await asyncio.to_thread(
                get_rag_chain().invoke,
                {'input': full_message},
                config={'configurable': {'session_id': chat_id}},
            )
            await send_whatsapp_message(number=chat_id, text=result['answer'])

    except asyncio.CancelledError:
        logger.info('[BUFFER] Debounce cancelado para %s', chat_id)
    except Exception as error:
        logger.error('[BUFFER] Erro ao processar mensagem de %s: %s', chat_id, error)
    finally:
        processing_chats.discard(chat_id)
        if debounce_tasks.get(chat_id) is asyncio.current_task():
            debounce_tasks.pop(chat_id, None)
