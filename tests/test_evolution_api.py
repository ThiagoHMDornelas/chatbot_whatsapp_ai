import asyncio

import evolution_api


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def test_send_whatsapp_message_envia_payload(monkeypatch):
    capturado = {}

    class ClientSucesso(FakeAsyncClient):
        async def post(self, url, json=None, headers=None):
            capturado.update(url=url, json=json, headers=headers)

            class Resposta:
                @staticmethod
                def raise_for_status():
                    return None

            return Resposta()

    monkeypatch.setattr(evolution_api.httpx, 'AsyncClient', ClientSucesso)

    asyncio.run(evolution_api.send_whatsapp_message('5511999999999@s.whatsapp.net', 'Ola'))

    assert capturado['json'] == {'number': '5511999999999@s.whatsapp.net', 'text': 'Ola'}
    assert 'apikey' in capturado['headers']
    assert '/message/sendText/' in capturado['url']


def test_send_whatsapp_message_nao_propaga_erro(monkeypatch):
    class ClientErro(FakeAsyncClient):
        async def post(self, *args, **kwargs):
            raise evolution_api.httpx.ConnectError('sem conexao')

    monkeypatch.setattr(evolution_api.httpx, 'AsyncClient', ClientErro)

    asyncio.run(evolution_api.send_whatsapp_message('5511999999999@s.whatsapp.net', 'Ola'))
