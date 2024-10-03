# Import required libraries
from crawl4ai import WebCrawler
import hashlib
import hmac
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
from typing import List, Dict
import os
from dotenv import load_dotenv  # To load the environment variables from .env
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
from pytubefix import YouTube
from pathlib import Path
from llama_parse import LlamaParse
import nest_asyncio
import langchain
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate


# Define the function to crawl the URL and return content
def extract_content_from_url(url: str) -> str:
    """
    Extracts content from the given URL and returns it in markdown format.
    
    Args:
        url (str): The URL to crawl and extract content from.
    
    Returns:
        str: The extracted content in markdown format.
    """
    # Create an instance of WebCrawler
    crawler = WebCrawler()

    # Warm up the crawler (load necessary models)
    crawler.warmup()

    # Run the crawler on the provided URL
    result = crawler.run(url=url)

    # Return the extracted content in markdown format
    return result.markdown


def create_unique_number_from_name(name: str, secret_key: str) -> int:
    """
    Creates a unique number based on the given string (name) and a secret key.
    
    Args:
        name (str): The input string from which the unique number will be generated.
        secret_key (str): The secret key used in the HMAC algorithm.
    
    Returns:
        int: A unique 10-digit number derived from the input string.
    """
    # Ensure the name is a string
    if not isinstance(name, str):
        raise ValueError("The name must be a string.")

    # Convert the name to bytes
    name_bytes = name.encode('utf-8')

    # Create an HMAC object using SHA-256 hash function and the secret key
    hmac_obj = hmac.new(secret_key.encode('utf-8'), name_bytes, hashlib.sha256)

    # Get the HMAC digest in hexadecimal format
    hex_digest = hmac_obj.hexdigest()

    # Convert the hex digest to an integer (base 16)
    unique_number = int(hex_digest, 16)

    # Reduce the size of the number to fit within 10 digits using modulo
    unique_number = unique_number % (10 ** 10)

    return unique_number


# Example usage
def generate_number_from_input(name: str) -> int:
    """
    Wrapper function to generate a unique number using a predefined secret key.
    
    Args:
        name (str): The input string (e.g., a URL).
    
    Returns:
        int: The unique 10-digit number for the input string.
    """
    secret_key = "9vTL8BbSTyGsYXeR3kZPjA=="  # Securely stored secret key
    return create_unique_number_from_name(name, secret_key)


def convert_to_langchain_document(content: str, url: str, category: str, unique_number: int) -> Document:
    """
    Converts the extracted content into a LangChain Document with metadata.
    
    Args:
        content (str): The extracted content in markdown format.
        url (str): The source URL of the content.
        category (str): The category of the content.
        unique_number (int): A unique identifier for the document.
    
    Returns:
        Document: A LangChain Document with the provided content and metadata.
    """
    # Create a LangChain Document with content and metadata
    document = Document(
        page_content=content,  # The extracted content
        metadata={
            "source": url,  # Store the URL as metadata
            "category": category,  # Store the category
            "chat_num": unique_number  # Store the unique number
        }
    )

    return [document]


def split_documents_into_chunks(documents: List[Document], chunk_size: int = 2000, chunk_overlap: int = 1000) -> List[
    Document]:
    """
    Splits a list of documents into smaller chunks using RecursiveCharacterTextSplitter.
    
    Args:
        documents (List[Document]): The list of LangChain documents to be split.
        chunk_size (int, optional): The maximum size of each chunk. Defaults to 2000 characters.
        chunk_overlap (int, optional): The overlap between consecutive chunks. Defaults to 1000 characters.
    
    Returns:
        List[Document]: A list of split document chunks.
    """
    # Initialize the text splitter with the specified chunk size and overlap
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # Split the documents into chunks
    split_docs = text_splitter.split_documents(documents)

    return split_docs


def map_chat_num_to_uuids(docs: List[Document]) -> Dict[int, List[str]]:
    """
    Maps each `chat_num` in the document metadata to a list of unique UUIDs.
    
    Args:
        docs (List[Document]): A list of LangChain documents.
    
    Returns:
        Dict[int, List[str]]: A dictionary mapping `chat_num` to a list of generated UUIDs.
    """
    # Generate unique UUIDs for each document
    ids = [str(uuid.uuid4()) for _ in docs]

    # Initialize a dictionary to map chat_num to UUIDs
    chat_num_to_uuid = {}

    # Map each chat_num to its corresponding list of UUIDs
    for doc, id in zip(docs, ids):
        chat_num = doc.metadata['chat_num']
        if chat_num not in chat_num_to_uuid:
            chat_num_to_uuid[chat_num] = []
        chat_num_to_uuid[chat_num].append(id)

    return ids, chat_num_to_uuid


load_dotenv()


def manage_faiss_index(user_id: str, docs: List[Document], ids: List[str]) -> FAISS:
    """
    Manages FAISS index for a given user. If an index for the user_id already exists, it loads the index and adds documents.
    Otherwise, it creates a new index from the provided documents and saves it.

    Args:
        user_id (str): The user ID (used to name the FAISS index file).
        docs (List[Document]): The list of LangChain documents to add to the FAISS index.
        ids (List[str]): The unique IDs corresponding to each document.

    Returns:
        FAISS: The FAISS vector store.
    """
    # Load the API key from the environment variables
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("Google API key is not set. Please check your .env file.")

    # Initialize the embeddings model
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",  # Replace with the actual model name
        api_key=api_key
    )

    # Define the path where the FAISS index is saved (based on user_id)
    index_path = f"faiss_index_{user_id}"

    # Check if the FAISS index folder for the user_id exists
    if os.path.exists(index_path):
        # If the index already exists, load the FAISS index
        print(f"FAISS index for user {user_id} exists. Loading index...")
        vector_db = FAISS.load_local(
            index_path,
            embeddings=embeddings_model,
            allow_dangerous_deserialization=True  # Enable deserialization
        )

        # Add new documents to the existing FAISS index
        vector_db.add_documents(documents=docs, ids=ids)
        vector_db.save_local(index_path)
        print(f"Documents added to existing FAISS index for user {user_id}.")


    else:
        # If the index doesn't exist, create a new FAISS index from documents
        print(f"FAISS index for user {user_id} does not exist. Creating new index...")
        vector_db = FAISS.from_documents(documents=docs, embedding=embeddings_model, ids=ids)

        # Save the newly created FAISS index locally
        vector_db.save_local(index_path)
        print(f"FAISS index for user {user_id} created and saved.")

    return vector_db


def get_youtube_video_details(url):
    # Create a YouTube object
    yt = YouTube(url)

    # Access available captions
    subtitles = yt.captions

    # Check for 'en-IN' or 'e.in' captions
    if 'en-IN' in subtitles or 'e.in' in subtitles:
        # Fetch captions based on available language code
        if 'en-IN' in subtitles:
            caption = subtitles['en-IN']  # Access directly as a dictionary
        else:
            caption = subtitles['e.in']  # Access directly as a dictionary

        # Generate the subtitle content
        document_content = caption.generate_srt_captions()
        title = yt.title  # Get video title
        return document_content
    else:
        return None, "Please provide a YouTube video that has English auto-generated subtitles."


def parse_pdf(pdf_path):
    # Get API key from .env file
    nest_asyncio.apply()

    # Load API key from .env file
    load_dotenv()
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")

    # Set the environment variable for the API key
    os.environ["LLAMA_CLOUD_API_KEY"] = api_key

    # Extract the PDF file name
    pdf_name = Path(pdf_path).name

    # Parse the document using LlamaParse
    document = LlamaParse(result_type="markdown").load_data(pdf_path)

    # Return the parsed document and file name
    return pdf_name, document


def concatenate_document_text(document):
    """
    Concatenates the text from each item in the document list into a single string.
    
    :param document: List of document objects, each containing a `text` attribute.
    :return: A string with all the text concatenated together.
    """
    document_content = ""

    for doc in document:
        document_content += doc.text

    return document_content


def load_faiss_vector_db(user_id: int) -> FAISS:
    """
    Function to load a FAISS vector database for a given user_id.
    
    Parameters:
    user_id (str): The user ID for which to load the FAISS index.
    
    Returns:
    FAISS: The loaded FAISS vector store.
    """

    # Get the API key from environment variables
    api_key = os.getenv("GOOGLE_API_KEY")

    if api_key is None:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    # Initialize the embeddings model
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",  # Replace with the actual model name
        api_key=api_key  # Pass the API key dynamically
    )
    user_id = str(user_id)
    # Load the vector database from local storage using user_id
    vector_db = FAISS.load_local(
        f"faiss_index_{user_id}",  # Use the user_id to specify the index path
        embeddings=embeddings_model,
        allow_dangerous_deserialization=True  # Enable deserialization
    )

    return vector_db


def query_retrieval_qa(query: str, category: str = None, vector_db=None):
    """
    Function to run a query through the RetrievalQA chain. 
    If a category is provided, it applies a filter based on the category.
    
    Parameters:
    query (str): The question to be answered.
    category (str, optional): The category to filter the FAISS search. Defaults to None.
    vector_db: The FAISS vector store that acts as the retriever.

    Returns:
    dict: The result of the query processing.
    """

    # Ensure the GROQ API key is in the environment
    api_key = os.getenv("GROQ_API_KEY")

    if api_key is None:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    # Initialize the ChatGroq model
    llm = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=0.6,
        max_retries=2,
        api_key=api_key
    )

    # Set up the retriever from the vector DB
    retriever = vector_db.as_retriever(
        search_kwargs={
            "filter": {"category": category},  # Filter to only include documents with category "asw"
            "k": 10,  # Number of top documents to retrieve
            "similarity": "cosine"  # Specify the similarity measure (e.g., "cosine", "euclidean")
        }
    )
    # Define the custom prompt template
    prompt_template = PromptTemplate(
        template="""Use the following documents to answer the question: , if there are no documents below use your own knowledge , you should reply like 
    "there is no relevant documents saved in memory ,based on my knowledge" and your answer
        
        {context}
        
        Question: {question}
        
        Answer:""",
        input_variables=["context", "question"]
    )

    # Create the RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # Use "stuff", "map_reduce", etc.
        retriever=retriever,
        return_source_documents=True,
        verbose=False,
        chain_type_kwargs={"prompt": prompt_template}
    )

    # Enable debugging 
    # langchain.debug = True
    result = qa_chain.invoke({"query": query})
    return result["result"]
