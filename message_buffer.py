import asyncio
from collections import defaultdict

import redis.asyncio as redis

from chains import get_conversational_rag_chain
from config import (
    BUFFER_KEY_SUFIX,
    BUFFER_TTL,
    DEBOUNCE_SECONDS,
    REDIS_URL,
)
from evolution_api import send_whatsapp_message


debounce_tasks = defaultdict(asyncio.Task)

_redis_client = None
_rag_chain = None


def log(*args):
    print('[BUFFER]', *args)


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


async def buffer_message(chat_id: str, message: str):
    redis_client = get_redis_client()
    buffer_key = f'{chat_id}{BUFFER_KEY_SUFIX}'

    await redis_client.rpush(buffer_key, message)
    await redis_client.expire(buffer_key, BUFFER_TTL)

    log(f'Mensagem adicionada ao buffer de {chat_id}: {message}')

    current_task = debounce_tasks.get(chat_id)
    if current_task:
        current_task.cancel()
        log(f'Debounce resetado para {chat_id}')

    debounce_tasks[chat_id] = asyncio.create_task(handle_debounce(chat_id))


async def handle_debounce(chat_id: str):
    try:
        log(f'Iniciando debounce para {chat_id}')
        await asyncio.sleep(float(DEBOUNCE_SECONDS))

        redis_client = get_redis_client()
        buffer_key = f'{chat_id}{BUFFER_KEY_SUFIX}'
        messages = await redis_client.lrange(buffer_key, 0, -1)

        full_message = ' '.join(messages).strip()
        if full_message:
            log(f'Enviando mensagem agrupada para {chat_id}: {full_message}')
            answer = get_rag_chain().invoke(
                {'input': full_message},
                config={'configurable': {'session_id': chat_id}},
            )['answer']

            await send_whatsapp_message(number=chat_id, text=answer)

        await redis_client.delete(buffer_key)

    except asyncio.CancelledError:
        log(f'Debounce cancelado para {chat_id}')
    except Exception as error:
        log(f'Erro ao processar mensagem de {chat_id}: {error}')
    finally:
        if debounce_tasks.get(chat_id) is asyncio.current_task():
            debounce_tasks.pop(chat_id, None)
