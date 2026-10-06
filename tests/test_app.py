from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import app as app_module
from app import app, extract_text_message


def test_extract_text_message_com_conversation():
    payload = {
        'event': 'messages.upsert',
        'data': {
            'key': {'remoteJid': '5511999999999@s.whatsapp.net', 'fromMe': False},
            'message': {'conversation': 'Ola'},
        },
    }
    assert extract_text_message(payload) == ('5511999999999@s.whatsapp.net', 'Ola')


def test_extract_text_message_com_extended_text():
    payload = {
        'data': {
            'key': {'remoteJid': '5511999999999@s.whatsapp.net'},
            'message': {'extendedTextMessage': {'text': 'Bom dia'}},
        },
    }
    assert extract_text_message(payload) == ('5511999999999@s.whatsapp.net', 'Bom dia')


def test_extract_text_message_ignora_grupo():
    payload = {
        'data': {
            'key': {'remoteJid': '123456789@g.us'},
            'message': {'conversation': 'Oi'},
        },
    }
    assert extract_text_message(payload) == (None, None)


def test_extract_text_message_ignora_mensagem_propria():
    payload = {
        'data': {
            'key': {'remoteJid': '5511999999999@s.whatsapp.net', 'fromMe': True},
            'message': {'conversation': 'Oi'},
        },
    }
    assert extract_text_message(payload) == (None, None)


def test_extract_text_message_sem_mensagem():
    payload = {'event': 'connection.update', 'data': {'state': 'open'}}
    assert extract_text_message(payload) == (None, None)


def test_health():
    client = TestClient(app)
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_webhook_envia_para_o_buffer(monkeypatch):
    buffer_mock = AsyncMock()
    monkeypatch.setattr(app_module, 'buffer_message', buffer_mock)

    client = TestClient(app)
    payload = {
        'event': 'messages.upsert',
        'data': {
            'key': {'remoteJid': '5511999999999@s.whatsapp.net', 'fromMe': False},
            'message': {'conversation': 'Ola'},
        },
    }
    response = client.post('/webhook', json=payload)

    assert response.status_code == 200
    buffer_mock.assert_awaited_once_with(
        chat_id='5511999999999@s.whatsapp.net',
        message='Ola',
    )


def test_webhook_ignora_evento_sem_mensagem(monkeypatch):
    buffer_mock = AsyncMock()
    monkeypatch.setattr(app_module, 'buffer_message', buffer_mock)

    client = TestClient(app)
    response = client.post('/webhook', json={'event': 'connection.update', 'data': {'state': 'open'}})

    assert response.status_code == 200
    buffer_mock.assert_not_awaited()
