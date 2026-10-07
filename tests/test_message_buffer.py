import asyncio

import message_buffer


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def rpush(self, key, value):
        self.data.setdefault(key, []).append(value)

    async def expire(self, key, ttl):
        return True

    async def lrange(self, key, start, end):
        return list(self.data.get(key, []))

    async def delete(self, key):
        self.data.pop(key, None)


class FakeChain:
    def __init__(self, answer):
        self.answer = answer

    def invoke(self, payload, config=None):
        return {'answer': self.answer}


def test_handle_debounce_envia_resposta(monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.data['chat_msg_buffer'] = ['Ola', 'tudo bem?']

    monkeypatch.setattr(message_buffer, 'get_redis_client', lambda: fake_redis)
    monkeypatch.setattr(message_buffer, 'get_rag_chain', lambda: FakeChain('resposta'))
    monkeypatch.setattr(message_buffer, 'BUFFER_KEY_SUFIX', '_msg_buffer')
    monkeypatch.setattr(message_buffer, 'DEBOUNCE_SECONDS', '0')

    enviados = {}

    async def fake_send(number, text):
        enviados['number'] = number
        enviados['text'] = text

    monkeypatch.setattr(message_buffer, 'send_whatsapp_message', fake_send)

    asyncio.run(message_buffer.handle_debounce('chat'))

    assert enviados == {'number': 'chat', 'text': 'resposta'}
    assert 'chat_msg_buffer' not in fake_redis.data


def test_handle_debounce_sem_mensagens_nao_envia(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(message_buffer, 'get_redis_client', lambda: fake_redis)
    monkeypatch.setattr(message_buffer, 'BUFFER_KEY_SUFIX', '_msg_buffer')
    monkeypatch.setattr(message_buffer, 'DEBOUNCE_SECONDS', '0')

    enviados = []

    async def fake_send(number, text):
        enviados.append((number, text))

    monkeypatch.setattr(message_buffer, 'send_whatsapp_message', fake_send)

    asyncio.run(message_buffer.handle_debounce('chat'))

    assert enviados == []


def test_handle_debounce_nao_apaga_mensagem_que_chegou_durante_o_processamento(monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.data['chat_msg_buffer'] = ['primeira']

    monkeypatch.setattr(message_buffer, 'get_redis_client', lambda: fake_redis)
    monkeypatch.setattr(message_buffer, 'BUFFER_KEY_SUFIX', '_msg_buffer')
    monkeypatch.setattr(message_buffer, 'DEBOUNCE_SECONDS', '0')

    class ChainQueAdicionaMensagem:
        def invoke(self, payload, config=None):
            fake_redis.data.setdefault('chat_msg_buffer', []).append('segunda')
            return {'answer': 'ok'}

    monkeypatch.setattr(message_buffer, 'get_rag_chain', lambda: ChainQueAdicionaMensagem())

    async def fake_send(number, text):
        return None

    monkeypatch.setattr(message_buffer, 'send_whatsapp_message', fake_send)

    asyncio.run(message_buffer.handle_debounce('chat'))

    assert fake_redis.data.get('chat_msg_buffer') == ['segunda']
