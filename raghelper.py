import os
import uuid
import chromadb
from pathlib import Path
import config as cfg

#all langchain imports
from langchain_community.document_loaders import JSONLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter

from chromadb.utils import embedding_functions

#helper functions for RAG application
#1. load the product catalog
#2. split the product catalog into chunks
#3. create a vector store from the chunks
#4. query the vector store to get context for a prompt
#5. initialize the vector store and the LLM
#6. maintain chat history

#create an array that holds max_history items. As new ones come in the old ones must go
def add_to_history(item):
    cfg.history.append(item)
    if len(cfg.history) > cfg.maxHistory:
        cfg.history.pop(0)
    #for item in cfg.history:
    #    print("History item: {}".format(item))

def load_docs(folder, docsToAdd):
    # # Load the contents of the product catalog
    # docs = []

    # #loop through all the files in the directory
    # for d in os.listdir(folder):
    #     path = os.path.join(folder, d)
    #     print(".....Loading doc: {}".format(path))
    #     txtLoader = TextLoader(path)
    #     thisDoc = txtLoader.load()
    #     docs.extend(thisDoc)

    loadedDocs = []
    processedDocs = []
    for d in docsToAdd:
        path = os.path.join(folder, d)
        print(".....Loading doc: {}".format(path))
        suffix = Path(path).suffix.lower()
        if suffix == ".pdf":
            pdfLoader = PyPDFLoader(path)
            thisDoc = pdfLoader.load()
            processedDocs.extend(thisDoc)
            loadedDocs.extend([d])
            continue
        elif suffix == ".json":
            jsonLoader = JSONLoader(path)
            thisDoc = jsonLoader.load()
            processedDocs.extend(thisDoc)
            loadedDocs.extend([d])
            continue
        elif suffix == ".txt" or suffix == ".rtf":
            txtLoader = TextLoader(path)
            thisDoc = txtLoader.load()
            processedDocs.extend(thisDoc)
            loadedDocs.extend([d])
        else:
            print(".....Unsupported file type: {}".format(suffix))
            continue

    return loadedDocs, processedDocs

def process_docs(docs):
    #chunk/split
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    return splits

def collection_exists(name):
    collections = cfg.chromaClient.list_collections()
    for collection in collections:
        if collection.name == name:
            return True
    return False

def create_vectorstore(splits):
    collection = cfg.chromaClient.get_or_create_collection(name=cfg.collectionName, embedding_function=cfg.embedder)

    #create a unique doc_id for each split based on source name concatenated with split number
    #will avoid duplicates on re-entry, as long as source name and number of splits remain the same
    doc_ids = [doc.metadata.get("source", str(uuid.uuid4())) + f"-{i}" for i, doc in enumerate(splits)]
    #print("doc_ids: {}".format(doc_ids))

    documents = [d.page_content for d in splits]
    metadatas=[{"source": Path(doc.metadata.get("source", "").replace(cfg.ragSource + "/", "")).stem} for i, doc in enumerate(splits)]
    collection.add(documents=documents, ids=doc_ids, metadatas=metadatas)
    return collection

def get_vectorstore():
    collection = cfg.chromaClient.get_or_create_collection(name=cfg.collectionName, embedding_function=cfg.embedder)
    return collection

def query_vectorstore(q, numResults=5):
    results = cfg.vectorStore.query(query_texts=[q], n_results=numResults)

    #print("Query: {}\n\n, Results: {}\n\n".format(q, results))
    return results

def clear_history():
    cfg.history = []
    #print("History cleared!")

def cleanup():
    cfg.chromaClient.delete_collection(name=cfg.collectionName)
    cfg.vectorStore = None

def print_context(response):
    #use this to understand the context (documents retrieved from vector store for a query)
    print("Context:")
    for document in response["context"]:
        print(document)

def list_collections():
    collections = cfg.chromaClient.list_collections()
    for collection in collections:
        print("Collection: {}".format(collection.name))
        count = collection.count()
        print("   Number of documents: {}".format(count))

def get_documents_in_store():
    #list all documents in the collection
    if cfg.vectorStore is None:
        print("Vector store is not initialized")
        return []
    
    docs=[]
    results = cfg.vectorStore.get()
    for elem in results["metadatas"]:
        if elem["source"] not in docs:
            docs.append(elem["source"])
    return docs

def needs_update():
    #check if the vector store needs to be updated
    #for example, if the source documents have changed
    #find time stamp of the vector store
    #if the source documents are newer than the vector store, add to the list of docs
    docsToAdd = []

    vector_store_time = 0
    vector_store_folder = cfg.chromaPath
    f = "chroma.sqlite3"
    path = os.path.join(vector_store_folder, f)
    if os.path.isfile(path):
        vector_store_time = os.path.getmtime(path)
    print("Vector store time: {}".format(vector_store_time))

    source_folder = cfg.ragSource
    #go through all files in the source folder and get the latest time stamp
    latest_time = 0
    for f in os.listdir(source_folder):
        path = os.path.join(source_folder, f)
        if os.path.isfile(path):
            print("Source file: {}".format(path))
            file_time = os.path.getmtime(path)
            print("   File time: {}".format(file_time))
            if file_time > latest_time:
                latest_time = file_time
            if file_time > vector_store_time:
                docsToAdd.append(f)
                print("   File {} is newer than vector store".format(f))
    source_time = latest_time

    #print("Source time: {}, Vector store time: {}".format(source_time, vector_store_time))
    return (source_time > vector_store_time), docsToAdd

def initialize():
    print("Initializing...")
    absPath = os.path.abspath(cfg.chromaPath)
    #print("Chroma abs path: {}".format(absPath))

    cfg.chromaClient = chromadb.PersistentClient(
        path=absPath
    )

    cfg.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    if collection_exists(cfg.collectionName):
        #print("Collection {} already exists".format(cfg.collectionName))
        cfg.vectorStore = get_vectorstore()
    else:
        print("Collection {} does not exist. Creating...".format(cfg.collectionName))
        loadedDocs, processedDocs = load_docs(cfg.ragSource, os.listdir(cfg.ragSource))
        #print("Docs:{}".format(loadedDocs))
        print("Loaded {} documents".format(len(loadedDocs)))
        splits = process_docs(processedDocs)
        print("Processed into {} splits".format(len(splits)))
        cfg.vectorStore = create_vectorstore(splits)
        print("Vector store created with {} splits".format(cfg.vectorStore.count()))

    #count = cfg.vectorStore.count()
    #print("Number of splits in vector store: {}".format(count))

    cfg.documents = get_documents_in_store()
    print("Welcome to the StudyAId!")
    print("Number of documents in the library: {}".format(len(cfg.documents)))
    print("If you would like to exit at any time, type 'exit', 'bye', 'quit', or 'end'")
    print("="*40)

    # needsUpdate, docsToAdd = needs_update()
    # if needsUpdate:
    #     print("Vector store needs to be updated")
    #     docs = load_docs(cfg.ragSource, docsToAdd)
    #     print("Loaded {} documents".format(len(docs)))
    #     splits = process_docs(docs)
    #     print("Processed into {} splits".format(len(splits)))
    #     cfg.vectorStore = create_vectorstore(splits)
    #     print("Vector store updated with {} documents".format(cfg.vectorStore.count()))
    # else:
    #     print("Vector store does not need to be updated")
