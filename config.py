import os

from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL_NAME = os.getenv('OPENAI_MODEL_NAME')
OPENAI_MODEL_TEMPERATURE = os.getenv('OPENAI_MODEL_TEMPERATURE')

DEFAULT_CONTEXTUALIZE_PROMPT = (
    'Dado um histórico de conversa e a pergunta mais recente do usuário, que pode '
    'fazer referência ao contexto anterior, formule uma pergunta independente, que '
    'possa ser compreendida sem o histórico da conversa. NÃO responda à pergunta — '
    'apenas reformule se necessário; caso contrário, retorne a pergunta como está.'
)

DEFAULT_SYSTEM_PROMPT = (
    'Você é um assistente virtual que irá responder dúvidas dos clientes. Use os '
    'seguintes trechos de contexto recuperado para responder à pergunta. Se você não '
    'souber a resposta, diga que não sabe. Use no máximo três frases e mantenha a '
    'resposta concisa. {context}'
)

AI_CONTEXTUALIZE_PROMPT = os.getenv('AI_CONTEXTUALIZE_PROMPT') or DEFAULT_CONTEXTUALIZE_PROMPT
AI_SYSTEM_PROMPT = os.getenv('AI_SYSTEM_PROMPT') or DEFAULT_SYSTEM_PROMPT

VECTOR_STORE_PATH = os.getenv('VECTOR_STORE_PATH')
RAG_FILES_DIR = os.getenv('RAG_FILES_DIR')

EVOLUTION_API_URL = os.getenv('EVOLUTION_API_URL')
EVOLUTION_INSTANCE_NAME = os.getenv('EVOLUTION_INSTANCE_NAME')
EVOLUTION_AUTHENTICATION_API_KEY = os.getenv('AUTHENTICATION_API_KEY')

REDIS_URL = os.getenv('CACHE_REDIS_URI')

BUFFER_KEY_SUFIX = os.getenv('BUFFER_KEY_SUFIX')
DEBOUNCE_SECONDS = os.getenv('DEBOUNCE_SECONDS')
BUFFER_TTL = os.getenv('BUFFER_TTL')

WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN')
