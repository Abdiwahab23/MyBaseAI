import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import PGVector
from langchain_core.prompts import ChatPromptTemplate
from django.conf import settings

# Global instances for caching to drastically speed up response times
_embeddings_cache = {}
_llm_cache = {}
_vectorstores = {}

def get_user_api_key(user_id):
    if user_id:
        from chatbot.models import UserSettings
        try:
            settings = UserSettings.objects.get(user_id=user_id)
            if settings.gemini_api_key:
                return settings.gemini_api_key
        except UserSettings.DoesNotExist:
            pass
    return os.getenv("GEMINI_API_KEY")

def get_embeddings(user_id=None, force_default=False):
    global _embeddings_cache
    api_key = os.getenv("GEMINI_API_KEY") if force_default else get_user_api_key(user_id)
    if api_key not in _embeddings_cache:
        _embeddings_cache[api_key] = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=api_key, max_retries=3)
    return _embeddings_cache[api_key]

def get_llm(user_id=None, force_default=False):
    global _llm_cache
    api_key = os.getenv("GEMINI_API_KEY") if force_default else get_user_api_key(user_id)
    if api_key not in _llm_cache:
        _llm_cache[api_key] = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.3, max_retries=3)
    return _llm_cache[api_key]

def _get_pg_connection():
    conn = os.getenv("DATABASE_URL")
    if conn and conn.startswith("postgres://"):
        conn = conn.replace("postgres://", "postgresql+psycopg2://")
    elif conn and conn.startswith("postgresql://"):
        conn = conn.replace("postgresql://", "postgresql+psycopg2://")
    return conn

def get_vectorstore(user_id=None, force_default_key=False):
    global _vectorstores
    collection_name = f"user_{user_id}" if user_id else "default_collection"
    
    if collection_name not in _vectorstores:
        try:
            _vectorstores[collection_name] = PGVector(
                connection_string=_get_pg_connection(),
                embedding_function=get_embeddings(user_id, force_default_key),
                collection_name=collection_name,
                use_jsonb=True
            )
        except Exception as e:
            print(f"Error connecting to PGVector: {e}")
            return None
    return _vectorstores.get(collection_name)

def process_document(file_path, user_id=None):
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    
    global _vectorstores
    collection_name = f"user_{user_id}" if user_id else "default_collection"
    
    try:
        _vectorstores[collection_name] = PGVector.from_documents(
            documents=splits,
            embedding=get_embeddings(user_id),
            collection_name=collection_name,
            connection_string=_get_pg_connection(),
            use_jsonb=True
        )
    except Exception as e:
        # Fallback to default API key if user's custom key is invalid
        _vectorstores[collection_name] = PGVector.from_documents(
            documents=splits,
            embedding=get_embeddings(user_id, force_default=True),
            collection_name=collection_name,
            connection_string=_get_pg_connection(),
            use_jsonb=True
        )
        
    return True

def _get_answer_internal(query, session_history=None, user_id=None, force_default_key=False):
    from django.contrib.auth.models import User
    company_name = "our company"
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            company_name = user.get_full_name() or user.username
        except User.DoesNotExist:
            pass

    vectorstore = get_vectorstore(user_id, force_default_key)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) if vectorstore else None
    llm = get_llm(user_id, force_default_key)
    
    if retriever:
        docs = retriever.invoke(query)
        context = "\n\n".join(doc.page_content for doc in docs)
        
        system_prompt = (
            f"You are a friendly and helpful AI customer support assistant for {company_name}. "
            f"You should respond naturally and politely to greetings (e.g., 'hi', 'assalamu alaikum'), small talk, or expressions of gratitude (e.g., 'thank you'). "
            f"When answering questions about {company_name} or their products/services, you must ONLY use the provided company documents in the Context below. "
            f"If a user asks a question that cannot be answered using the Context, politely explain that you are only trained to answer questions about {company_name} based on the knowledge base. "
            f"Keep your answers concise and friendly, using three sentences maximum.\n\n"
            f"Context:\n{{context}}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        chain = prompt | llm
        response = chain.invoke({"context": context, "input": query})
        return response.content
    else:
        system_prompt = (
            f"You are a friendly and helpful AI customer support assistant for {company_name}. "
            f"Currently, the company hasn't uploaded any specific knowledge base documents. "
            f"You should respond naturally and politely to greetings (e.g., 'hi', 'assalamu alaikum'), small talk, or expressions of gratitude (e.g., 'thank you'). "
            f"If the user asks a specific question, politely explain that you are only trained to answer questions about {company_name}, but the knowledge base is currently empty."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        chain = prompt | llm
        response = chain.invoke({"input": query})
        return response.content

def get_answer(query, session_history=None, user_id=None):
    try:
        return _get_answer_internal(query, session_history, user_id, force_default_key=False)
    except Exception as e:
        # Fallback to default API key
        return _get_answer_internal(query, session_history, user_id, force_default_key=True)
