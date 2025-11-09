from langchain_ollama import ChatOllama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
import os
import time

# Force Ollama to use GPU by setting environment variable
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['OLLAMA_NUM_GPU'] = '1'

# from langchain.document_loaders import PyPDFLoader
# from langchain.document_transformers import EmbeddingsClusteringFilter
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import PyPDFLoader, UnstructuredHTMLLoader
from langchain_community.document_transformers import EmbeddingsClusteringFilter
from langchain_huggingface import HuggingFaceEmbeddings

DEFAULT_MODEL = "llama3.2:latest"

model_name = "BAAI/bge-base-en-v1.5"
model_kwargs = {"device": "cuda"}
encode_kwargs = {"normalize_embeddings": True}
try:
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )
    print("running on GPU")
except Exception as e:
    model_kwargs = {"device": "cpu"}
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )
    print("running on CPU")


prompt = PromptTemplate(
    input_variables=["text"],
    template="Summarize this financial text form polish GPW stock in no more than 200 words and use financial language:\n\n{text}, answer me in Polish language",
)

# Global LLM cache to avoid reloading model for each file
_llm_cache = {}

def get_cached_llm(model_name: str, num_predict: int) -> ChatOllama:
    """Get or create cached LLM instance to avoid reloading model multiple times."""
    cache_key = f"{model_name}_{num_predict}"
    if cache_key not in _llm_cache:
        print(f"Creating new LLM instance for {model_name} (num_predict={num_predict})")
        _llm_cache[cache_key] = ChatOllama(
            model=model_name,
            temperature=0,
            num_predict=num_predict,
            num_gpu=-1,  # Use all available GPUs for maximum performance
            num_ctx=4096,  # Pełny kontekst (domyślnie) - zwiększone do pełnego obciążenia GPU
            num_thread=None,  # Let Ollama decide optimal thread count (don't limit CPU)
        )
        print(f"✅ LLM configured: num_gpu=-1, num_ctx=4096, num_thread=None")
    return _llm_cache[cache_key]


def extract(file_path: str):
    """
    Extract text from PDF or HTML file.
    
    Args:
        file_path: Path to the file (PDF or HTML)
    
    Returns:
        List of Document objects with extracted text
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        loader = PyPDFLoader(file_path)
    elif file_extension in ['.html', '.htm']:
        loader = UnstructuredHTMLLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}. Supported: .pdf, .html, .htm")
    
    pages = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(pages)
    return texts


def summarize_document_with_kmeans_clustering(file_path: str, model_name: str = DEFAULT_MODEL):
    """
    Summarize a document (PDF or HTML) using k-means clustering and an Ollama model.
    
    Args:
        file_path: Path to the document file (PDF or HTML)
        model_name: Name of the Ollama model to use (default: DEFAULT_MODEL)
    
    Returns:
        String containing the summary or error message
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    file_type = "PDF" if file_extension == '.pdf' else "HTML"
    
    print(f"\n{'='*60}")
    print(f"📄 Przetwarzanie {file_type}: {os.path.basename(file_path)}")
    total_start = time.time()
    
    # 1. Ładowanie dokumentu
    step_start = time.time()
    if file_extension == '.pdf':
        loader = PyPDFLoader(file_path)
    elif file_extension in ['.html', '.htm']:
        loader = UnstructuredHTMLLoader(file_path)
    else:
        return f"❌ Unsupported file type: {file_extension}"
    
    pages = loader.load()
    print(f"⏱️  [1/4] Wczytanie {file_type} ({len(pages)} stron/sekcji): {time.time() - step_start:.2f}s")
    
    # 2. Podział na chunki
    step_start = time.time()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
    texts = text_splitter.split_documents(pages)
    print(f"⏱️  [2/4] Podział na {len(texts)} chunków: {time.time() - step_start:.2f}s")

    # Check if document has any text
    if len(texts) == 0:
        print(f"⚠️  Dokument pusty lub bez tekstu (tylko obrazy/skanowane)")
        print(f"{'='*60}\n")
        return f"❌ Brak tekstu do przetworzenia w: {os.path.basename(file_path)}"

    if len(pages) <= 2:
        num_clusters = 1
        num_predict = 50
    elif len(pages) >= 40:
        num_clusters = 9
        num_predict = 1200
    else:
        num_clusters = 5
        num_predict = 600
    
    # 3. K-means clustering
    step_start = time.time()
    doc_filter = EmbeddingsClusteringFilter(
        embeddings=embeddings, num_clusters=num_clusters, num_closest=1
    )
    result = doc_filter.transform_documents(documents=texts)
    print(f"⏱️  [3/4] K-means clustering ({num_clusters} klastrów): {time.time() - step_start:.2f}s")
    
    # Use cached LLM instance instead of creating new one each time
    llm = get_cached_llm(model_name, num_predict)

    try:
        # 4. Generowanie podsumowania przez LLM
        step_start = time.time()
        print(f"🤖 [4/4] Generowanie podsumowania przez LLM ({model_name})...")
        
        # Direct LLM invocation instead of chain for better GPU utilization
        # Concatenate all documents into one prompt
        combined_text = "\n\n".join([doc.page_content for doc in result])
        full_prompt = prompt.format(text=combined_text)
        
        print(f"📝 Prompt length: {len(full_prompt)} characters")
        
        # Direct invoke for maximum GPU usage
        response = llm.invoke(full_prompt)
        
        llm_time = time.time() - step_start
        print(f"⏱️  [4/4] Generowanie przez LLM: {llm_time:.2f}s")
        
        # Extract text from response
        if hasattr(response, 'content'):
            summary = response.content
        else:
            summary = str(response)
            
        total_time = time.time() - total_start
        print(f"✅ CAŁKOWITY CZAS: {total_time:.2f}s")
        print(f"{'='*60}\n")
        
        return f"#### Model: {model_name} | Liczba stron: {len(pages)} ####\n{summary}"
    except Exception as e:
        print(f"❌ BŁĄD: {e}")
        print(f"{'='*60}\n")
        return f"#### zbyt mały dokument, {len(pages)} stron w raporcie #### {e}"


