"""
Summarization Module
Handles document summarization using K-means clustering and LLM.
"""

from langchain_ollama import ChatOllama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader, UnstructuredHTMLLoader
from langchain_community.document_transformers import EmbeddingsClusteringFilter
from langchain_huggingface import HuggingFaceEmbeddings
import os
import sys
import time

# Add parent directory to path for database imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_connection import get_downloaded_file_by_name, update_file_summary


# Force Ollama to use GPU
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['OLLAMA_NUM_GPU'] = '1'

# Use absolute path based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_PATH = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "REPORTS")

DEFAULT_MODEL = "llama3.2:latest"

# Initialize embeddings model
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


# Summarization prompt template
prompt = PromptTemplate(
    input_variables=["text"],
    template="Summarize this financial text form polish GPW stock in no more than 200 words and use financial language:\n\n{text}, answer me in Polish language",
)


# Global LLM cache to avoid reloading model
_llm_cache = {}


def get_cached_llm(model_name: str, num_predict: int) -> ChatOllama:
    """
    Get or create cached LLM instance to avoid reloading model multiple times.
    
    Args:
        model_name: Name of Ollama model
        num_predict: Maximum tokens to predict
    
    Returns:
        ChatOllama instance
    """
    cache_key = f"{model_name}_{num_predict}"
    if cache_key not in _llm_cache:
        print(f"Creating new LLM instance for {model_name} (num_predict={num_predict})")
        _llm_cache[cache_key] = ChatOllama(
            model=model_name,
            temperature=0,
            num_predict=num_predict,
            num_gpu=-1,  # Use all available GPUs
            num_ctx=4096,  # Full context for maximum GPU utilization
            num_thread=None,  # Let Ollama decide optimal thread count
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
    
    Uses optimized LLM settings for maximum GPU utilization:
    - num_gpu=-1 (all GPUs)
    - num_ctx=4096 (full context)
    - Direct llm.invoke() instead of chain for better performance
    
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
    
    # 1. Load document
    step_start = time.time()
    if file_extension == '.pdf':
        loader = PyPDFLoader(file_path)
    elif file_extension in ['.html', '.htm']:
        loader = UnstructuredHTMLLoader(file_path)
    else:
        return f"❌ Unsupported file type: {file_extension}"
    
    pages = loader.load()
    print(f"⏱️  [1/4] Wczytanie {file_type} ({len(pages)} stron/sekcji): {time.time() - step_start:.2f}s")
    
    # 2. Split into chunks
    step_start = time.time()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
    texts = text_splitter.split_documents(pages)
    print(f"⏱️  [2/4] Podział na {len(texts)} chunków: {time.time() - step_start:.2f}s")

    # Check if document has any text
    if len(texts) == 0:
        print(f"⚠️  Dokument pusty lub bez tekstu (tylko obrazy/skanowane)")
        print(f"{'='*60}\n")
        return f"❌ Brak tekstu do przetworzenia w: {os.path.basename(file_path)}"

    # Determine optimal cluster count based on document size
    if len(pages) <= 2:
        num_clusters = 1
        num_predict = 50
    elif len(pages) >= 40:
        num_clusters = 9
        num_predict = 1200
    else:
        num_clusters = 5
        num_predict = 600
    
    # 3. K-means clustering to select representative chunks
    step_start = time.time()
    doc_filter = EmbeddingsClusteringFilter(
        embeddings=embeddings, num_clusters=num_clusters, num_closest=1
    )
    result = doc_filter.transform_documents(documents=texts)
    print(f"⏱️  [3/4] K-means clustering ({num_clusters} klastrów): {time.time() - step_start:.2f}s")
    
    # Use cached LLM instance
    llm = get_cached_llm(model_name, num_predict)

    try:
        # 4. Generate summary with LLM
        step_start = time.time()
        print(f"🤖 [4/4] Generowanie podsumowania przez LLM ({model_name})...")
        
        # Direct LLM invocation for better GPU utilization
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


def get_summaries(files: list, company: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Generate summaries for all PDF and HTML files.
    Saves each summary to database (downloaded_files.summary_text).
    
    Args:
        files: List of filenames to summarize
        company: Company name
        model_name: Ollama model to use
    
    Returns:
        Concatenated string of all summaries
    """
    text = ""
    # Filter for both PDF and HTML files
    document_files = [f for f in files if f.endswith((".pdf", ".html", ".htm"))]
    
    if not document_files:
        return "*No documents to summarize*"
    
    print(f"Processing {len(document_files)} document files for {company}...")
    
    for i, f in enumerate(document_files, 1):
        path = os.path.join(REPORTS_PATH, company, f)
        text += f"\n## File {i}/{len(document_files)}: {f} ##\n"
        if os.path.exists(path):
            print(f"  Summarizing {i}/{len(document_files)}: {f}...")
            try:
                summary = summarize_document_with_kmeans_clustering(path, model_name)
                text += summary + "\n"
                
                # Save summary to database
                file_record = get_downloaded_file_by_name(company.lower(), f)
                if file_record:
                    update_file_summary(file_record['id'], summary)
                    print(f"  ✓ Streszczenie zapisane do bazy (file_id={file_record['id']})")
                else:
                    print(f"  ⚠ Nie znaleziono pliku w bazie: {f}")
                    
            except Exception as e:
                text += f"Error processing {f}: {str(e)}\n"
                print(f"  ❌ Błąd: {e}")
        else:
            text += f"File not found: {path}\n"
    
    return text


def generate_collective_summary_with_llm(
    individual_summaries: str,
    company: str,
    model_name: str
) -> str:
    """
    Generate collective meta-summary using LLM based on all individual summaries.
    
    Creates a comprehensive summary that:
    1. Extracts key information from all reports
    2. Identifies trends and changes
    3. Provides concrete numbers and facts
    4. Uses professional financial language
    
    Args:
        individual_summaries: Concatenated text of all individual summaries
        company: Company name
        model_name: Ollama model to use
    
    Returns:
        Collective summary text generated by LLM
    """
    print(f"\n🤖 Generowanie zbiorczego raportu przez LLM ({model_name})...")
    print(f"   Analiza streszczeń dla {company}...")
    
    try:
        llm = get_cached_llm(model_name, num_predict=1500)
        
        prompt = f"""Na podstawie poniższych pojedynczych streszczeń raportów giełdowych dla firmy {company}, 
stwórz JEDNO ZBIORCZE PODSUMOWANIE (około 300-500 słów) które:

1. Wyciąga najważniejsze informacje ze wszystkich raportów
2. Identyfikuje kluczowe trendy i zmiany
3. Podaje konkretne liczby i fakty
4. Jest napisane profesjonalnym językiem finansowym
5. Odpowiada na pytanie: Jak wiedzie się firmie?

Pojedyncze streszczenia raportów:

{individual_summaries}

ZBIORCZY RAPORT (po polsku):"""
        
        response = llm.invoke(prompt)
        collective_summary = response.content if hasattr(response, 'content') else str(response)
        
        print(f"✅ Zbiorczy raport wygenerowany przez LLM")
        return collective_summary
        
    except Exception as e:
        print(f"❌ Błąd generowania zbiorczego raportu: {e}")
        return f"❌ Nie udało się wygenerować zbiorczego raportu: {e}\n\n{individual_summaries}"
