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
