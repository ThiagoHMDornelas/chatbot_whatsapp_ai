from langchain_core.documents import Document

import vectorstore


def test_load_documents_le_arquivos_txt(tmp_path, monkeypatch):
    arquivo = tmp_path / 'manual.txt'
    arquivo.write_text('O notebook possui 8GB de memoria RAM.', encoding='utf-8')

    monkeypatch.setattr(vectorstore, 'RAG_FILES_DIR', str(tmp_path))

    docs = vectorstore.load_documents()

    assert len(docs) == 1
    assert '8GB' in docs[0].page_content


def test_load_documents_ignora_arquivos_desconhecidos(tmp_path, monkeypatch):
    (tmp_path / 'imagem.png').write_bytes(b'\x89PNG')
    (tmp_path / 'manual.txt').write_text('Conteudo de teste.', encoding='utf-8')

    monkeypatch.setattr(vectorstore, 'RAG_FILES_DIR', str(tmp_path))

    docs = vectorstore.load_documents()

    assert len(docs) == 1


def test_get_vectorstore_reaproveita_quando_ja_tem_documentos(monkeypatch):
    class FakeChromaComDocs:
        def __init__(self, embedding_function=None, persist_directory=None):
            pass

        def get(self, limit=None, include=None):
            return {'ids': ['1']}

        def add_documents(self, documents):
            raise AssertionError('nao deveria reindexar quando ja ha documentos')

    def nao_deveria_carregar():
        raise AssertionError('nao deveria carregar documentos')

    monkeypatch.setattr(vectorstore, 'Chroma', FakeChromaComDocs)
    monkeypatch.setattr(vectorstore, 'OpenAIEmbeddings', lambda: object())
    monkeypatch.setattr(vectorstore, 'load_documents', nao_deveria_carregar)

    vectorstore.get_vectorstore()


def test_get_vectorstore_indexa_quando_vazio(monkeypatch):
    class FakeChromaVazio:
        ultimo = None

        def __init__(self, embedding_function=None, persist_directory=None):
            pass

        def get(self, limit=None, include=None):
            return {'ids': []}

        def add_documents(self, documents):
            FakeChromaVazio.ultimo = documents

    monkeypatch.setattr(vectorstore, 'Chroma', FakeChromaVazio)
    monkeypatch.setattr(vectorstore, 'OpenAIEmbeddings', lambda: object())
    monkeypatch.setattr(
        vectorstore,
        'load_documents',
        lambda: [Document(page_content='O notebook tem 8GB de RAM.')],
    )

    vectorstore.get_vectorstore()

    assert FakeChromaVazio.ultimo
