from langchain_ollama import ChatOllama
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate

# from langchain.document_loaders import PyPDFLoader
# from langchain.document_transformers import EmbeddingsClusteringFilter
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import PyPDFLoader
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


def extract(file_path: str):
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(pages)
    return texts


def summarize_document_with_kmeans_clustering(file_path: str, model_name: str = DEFAULT_MODEL):
    """
    Summarize a PDF document using k-means clustering and an Ollama model.
    
    Args:
        file_path: Path to the PDF file
        model_name: Name of the Ollama model to use (default: DEFAULT_MODEL)
    
    Returns:
        String containing the summary or error message
    """
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
    texts = text_splitter.split_documents(pages)

    if len(pages) <= 2:
        doc_filter = EmbeddingsClusteringFilter(
            embeddings=embeddings, num_clusters=1, num_closest=1
        )
        llm = ChatOllama(model=model_name, temperature=0, num_predict=50)
    elif len(pages) >= 40:
        doc_filter = EmbeddingsClusteringFilter(
            embeddings=embeddings, num_clusters=9, num_closest=1
        )
        llm = ChatOllama(model=model_name, temperature=0, num_predict=1200)
    else:
        doc_filter = EmbeddingsClusteringFilter(
            embeddings=embeddings, num_clusters=5, num_closest=1
        )
        llm = ChatOllama(model=model_name, temperature=0, num_predict=600)

    try:
        result = doc_filter.transform_documents(documents=texts)
        checker_chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt)
        summary = checker_chain.run(result)
        return f"#### Model: {model_name} | Liczba stron: {len(pages)} ####\n{summary}"
    except Exception as e:
        return f"#### zbyt mały dokument, {len(pages)} stron w raporcie #### {e}"


