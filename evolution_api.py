import logging

import httpx

from config import (
    EVOLUTION_API_URL,
    EVOLUTION_INSTANCE_NAME,
    EVOLUTION_AUTHENTICATION_API_KEY,
)


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30.0


async def send_whatsapp_message(number: str, text: str) -> None:
    url = f'{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}'
    headers = {
        'apikey': EVOLUTION_AUTHENTICATION_API_KEY,
        'Content-Type': 'application/json',
    }
    payload = {
        'number': number,
        'text': text,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as error:
        logger.error('Falha ao enviar mensagem para %s: %s', number, error)
