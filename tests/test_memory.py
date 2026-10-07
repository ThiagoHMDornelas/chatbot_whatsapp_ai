import memory


def test_get_session_history_cria_historico_com_sessao(monkeypatch):
    capturado = {}

    class FakeHistory:
        def __init__(self, session_id, url):
            capturado['session_id'] = session_id
            capturado['url'] = url

    monkeypatch.setattr(memory, 'RedisChatMessageHistory', FakeHistory)
    monkeypatch.setattr(memory, 'REDIS_URL', 'redis://localhost:6379/6')

    memory.get_session_history('chat-1')

    assert capturado == {'session_id': 'chat-1', 'url': 'redis://localhost:6379/6'}
