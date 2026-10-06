import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from config import RAG_FILES_DIR, VECTOR_STORE_PATH


def load_documents():
    os.makedirs(RAG_FILES_DIR, exist_ok=True)

    docs = []
    files = sorted(
        filename
        for filename in os.listdir(RAG_FILES_DIR)
        if filename.endswith('.pdf') or filename.endswith('.txt')
    )

    for filename in files:
        file_path = os.path.join(RAG_FILES_DIR, filename)
        loader = PyPDFLoader(file_path) if filename.endswith('.pdf') else TextLoader(file_path)
        docs.extend(loader.load())

    return docs


def _has_documents(vectorstore: Chroma) -> bool:
    return bool(vectorstore.get()['ids'])


def get_vectorstore():
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=VECTOR_STORE_PATH,
    )

    if not _has_documents(vectorstore):
        docs = load_documents()
        if docs:
            splits = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            ).split_documents(docs)
            vectorstore.add_documents(splits)

    return vectorstore
