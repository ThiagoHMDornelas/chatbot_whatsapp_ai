from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app, extract_text_message


@pytest.fixture(autouse=True)
def _sem_webhook_token_por_padrao(monkeypatch):
    monkeypatch.setattr(app_module, 'WEBHOOK_TOKEN', None)


def _payload_messages_upsert():
    return {
        'event': 'messages.upsert',
        'data': {
            'key': {'remoteJid': '5511999999999@s.whatsapp.net', 'fromMe': False},
            'message': {'conversation': 'Ola'},
        },
    }


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
    response = client.post('/webhook', json=_payload_messages_upsert())

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


def test_webhook_sem_token_retorna_401(monkeypatch):
    monkeypatch.setattr(app_module, 'WEBHOOK_TOKEN', 'segredo')
    buffer_mock = AsyncMock()
    monkeypatch.setattr(app_module, 'buffer_message', buffer_mock)

    client = TestClient(app)
    response = client.post('/webhook', json=_payload_messages_upsert())

    assert response.status_code == 401
    buffer_mock.assert_not_awaited()


def test_webhook_token_invalido_retorna_401(monkeypatch):
    monkeypatch.setattr(app_module, 'WEBHOOK_TOKEN', 'segredo')
    buffer_mock = AsyncMock()
    monkeypatch.setattr(app_module, 'buffer_message', buffer_mock)

    client = TestClient(app)
    response = client.post('/webhook?token=errado', json=_payload_messages_upsert())

    assert response.status_code == 401
    buffer_mock.assert_not_awaited()


def test_webhook_token_valido_na_url(monkeypatch):
    monkeypatch.setattr(app_module, 'WEBHOOK_TOKEN', 'segredo')
    buffer_mock = AsyncMock()
    monkeypatch.setattr(app_module, 'buffer_message', buffer_mock)

    client = TestClient(app)
    response = client.post('/webhook?token=segredo', json=_payload_messages_upsert())

    assert response.status_code == 200
    buffer_mock.assert_awaited_once()


def test_webhook_token_valido_no_header(monkeypatch):
    monkeypatch.setattr(app_module, 'WEBHOOK_TOKEN', 'segredo')
    buffer_mock = AsyncMock()
    monkeypatch.setattr(app_module, 'buffer_message', buffer_mock)

    client = TestClient(app)
    response = client.post(
        '/webhook',
        json=_payload_messages_upsert(),
        headers={'x-webhook-token': 'segredo'},
    )

    assert response.status_code == 200
    buffer_mock.assert_awaited_once()
