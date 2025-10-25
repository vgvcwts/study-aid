import os
import uuid
import chromadb
from pathlib import Path
import litellm
import json
from datetime import datetime
import config as cfg

#all langchain imports
from langchain_community.document_loaders import JSONLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter

from chromadb.utils import embedding_functions

#helper functions for RAG application
#0. Initilialize chroma client and embedding function
#1. load the documents
#2. split the documents into chunks
#3. create a vector store from the chunks
#4. query the vector store to get context for a prompt
#5. maintain chat history

def load_docs(folder, docsToAdd):
    docs = []
    loadedDocs = []
    for d in docsToAdd:
        path = d
        print(".....Loading doc: {}".format(path))
        suffix = Path(path).suffix.lower()
        if suffix == ".pdf":
            pdfLoader = PyPDFLoader(path)
            thisDoc = pdfLoader.load()
            loadedDocs.extend(thisDoc)
            docs.extend([d])
            continue
        elif suffix == ".json":
            jsonLoader = JSONLoader(path)
            thisDoc = jsonLoader.load()
            loadedDocs.extend(thisDoc)
            docs.extend([d])
            continue
        elif suffix == ".txt" or suffix == ".rtf":
            txtLoader = TextLoader(path)
            thisDoc = txtLoader.load()
            loadedDocs.extend(thisDoc)
            docs.extend([d])
        elif suffix == ".xlsx" or suffix == ".xls":
            excelLoader = UnstructuredExcelLoader(path, mode="elements")
            thisDoc = excelLoader.load()
            loadedDocs.extend(thisDoc)
            docs.extend([d])
            continue
        elif suffix == ".pptx" or suffix == ".ppt":
            #need to test if it can handle speaker notes
            pptLoader = UnstructuredPowerPointLoader(path, mode="elements")
            thisDoc = pptLoader.load()
            loadedDocs.extend(thisDoc)
            docs.extend([d])
            continue
        elif suffix == ".docx" or suffix == ".doc":
            docxLoader = UnstructuredWordDocumentLoader(path, mode="elements")
            thisDoc = docxLoader.load()
            loadedDocs.extend(thisDoc)
            docs.extend([d])            
        else:
            print(".....Unsupported file type: {}".format(suffix))
            continue

    return docs, loadedDocs

def process_docs(docs):
    #chunk/split
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    return splits

def remove_docs(docStemsToRemove):
    removeCount = 0
    collection = get_vectorstore()
    #remove doc stems from vector store if source name matches doc stem
    for docStem in docStemsToRemove:
        print(".....Removing doc: {}".format(docStem))
        collection.delete(where={"source": docStem})
        #do NOT need to call persist in newer version of chromadb
        removeCount += 1
    return removeCount        

def collection_exists(name):
    collections = cfg.chromaClient.list_collections()
    for collection in collections:
        if collection.name == name:
            return True
    return False

def create_or_update_vectorstore(splits):
    collection = cfg.chromaClient.get_or_create_collection(name=cfg.collectionName, embedding_function=cfg.embedder)

    #create a unique doc_id for each split based on source name concatenated with split number
    #will avoid duplicates on re-entry, as long as source name and number of splits remain the same
    doc_ids = [doc.metadata.get("source", str(uuid.uuid4())) + f"-{i}" for i, doc in enumerate(splits)]
    print("doc_ids: {}".format(doc_ids)) if cfg.debugLevel > 1 else None

    documents = [d.page_content for d in splits]

    #use the directory hierarchy to create categories
    metadatas = []
    for i, doc in enumerate(splits):
        fullPath = doc.metadata.get("source", "")
        pathBelowRagSource = fullPath.replace(cfg.ragSource + "/", "")
        sourceNoExt = Path(pathBelowRagSource).stem
        ext = Path(pathBelowRagSource).suffix.lower()
        categories = pathBelowRagSource.split(os.sep)
        if len(categories) == 1:
            main_category = ""
            sub_category = ""
        elif len(categories) == 2:
            main_category = categories[0]
            sub_category = ""
        elif len(categories) > 2:
            main_category = categories[0]
            sub_category = categories[1]
        tags = {
            "source": sourceNoExt,
            "extension": ext,
            "main_category": main_category,
            "sub_category": sub_category,
        }
        #print("tags:{}".format(tags)) if cfg.debugLevel > 0 else None
        metadatas.append(tags)

    #metadatas=[{"source": Path(doc.metadata.get("source", "").replace(cfg.ragSource + "/", "")).stem} for i, doc in enumerate(splits)]

    collection.add(documents=documents, ids=doc_ids, metadatas=metadatas)
    return collection

def get_vectorstore():
    collection = cfg.chromaClient.get_or_create_collection(name=cfg.collectionName, embedding_function=cfg.embedder)
    return collection

def query_vectorstore(q, source=None, mainCategory = None, subCategory = None, numResults=10):
    kwargs = {
        "query_texts" : [q], 
        "n_results" : numResults
    }
    if source is not None:
        if mainCategory is not None and subCategory is not None:
            kwargs["where"] = {
                "$and": [
                    {"source": source},
                    {"main_category": mainCategory},
                    {"sub_category": subCategory}
                ]
            }
        elif mainCategory is not None and subCategory is None:
            kwargs["where"] = {
                "$and": [
                    {"source": source},
                    {"main_category": mainCategory}
                ]
            }
        else:
            kwargs["where"] = {
                "source": source
            }
    else:
        if mainCategory is not None and subCategory is not None:
            kwargs["where"] = {
                "$and": [
                    {"main_category": mainCategory},
                    {"sub_category": subCategory}
                ]
            }
        elif mainCategory is not None and subCategory is None:
            kwargs["where"] = {
                "main_category": mainCategory
            }
        else:
            pass


    print("Querying vector store with args: {}".format(kwargs)) if cfg.debugLevel > 1 else None

    results = cfg.vectorStore.query(
        **kwargs
    )

    return results

#As new ones come in the old ones must go
def add_to_history(item):
    cfg.history.append(item)
    if len(cfg.history) > cfg.maxHistory:
        cfg.history.pop(0)
    if cfg.debugLevel > 1:
        for item in cfg.history:
            print("History item: {}".format(item))

def clear_history():
    cfg.history = []
    #print("History cleared!")

def cleanup(collectionName):
    cfg.chromaClient.delete_collection(name=collectionName)

def cleanup_all():
    collections = cfg.chromaClient.list_collections()
    for collection in collections:
        print("Deleting collection: {}".format(collection.name))
        cfg.chromaClient.delete_collection(name=collection.name)

def remove_chroma_data_folder():
    import shutil
    if os.path.exists(cfg.chromaPath):
        shutil.rmtree(cfg.chromaPath)
        print("Removed chroma data folder: {}".format(cfg.chromaPath))
    else:
        print("Chroma data folder does not exist: {}".format(cfg.chromaPath))

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
        print("Knowledge base is not initialized")
        return []
    
    docStems=[]
    results = cfg.vectorStore.get()
    print("Retrieved {} documents from vector store".format(len(results["metadatas"]))) if cfg.debugLevel > 0 else None
    for elem in results["metadatas"]:
        if elem["source"] not in docStems:
            docStems.append(elem["source"])
    return docStems

def needs_update():
    #check if the vector store needs to be updated
    docPathsToAdd = []

    #existing docs do not have file extensions
    docStemsInDb = get_documents_in_store()
    print("Existing docs in store: {}".format(docStemsInDb)) if cfg.debugLevel > 0 else None
    
    docPathsInFolder = traverse_recursively(cfg.ragSource)
    print("All docs in source folder: {}".format(docPathsInFolder)) if cfg.debugLevel > 0 else None
    for docPath in docPathsInFolder:
        #strip the prefix and the extension from the path, leaving just the file name without extension
        stem = Path(docPath).stem
        if stem not in docStemsInDb:
            docPathsToAdd.append(docPath)

    print("Docs to add: {}".format(docPathsToAdd)) if cfg.debugLevel > 0 else None

    #create a docsToRemove list that removes docs from chromadb if not in source folder
    docStemsToRemove = []
    for docStem in docStemsInDb:
        #go through allDocs to see if the prefix in existingDocs matches the one in allDocs
        found = False
        for docPath in docPathsInFolder:
            stem = Path(docPath).stem
            if stem == docStem:
                found = True
                break
        if not found:
            docStemsToRemove.append(docStem)
    
    print("Doc stems to remove: {}".format(docStemsToRemove)) if cfg.debugLevel > 0 else None

    return docPathsToAdd, docStemsToRemove

def traverse_recursively(root_dir):
    """
    Recursively traverses a directory, processes each file,
    and extracts path prefixes for each level.
    """
    docs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            docs.append(os.path.join(dirpath, f))
    
    return docs

def get_response(prompt, jsonOutput=False, schema=None):
    userMessage = {'role':'user', 'content': f"{prompt}"}
    add_to_history(userMessage)

    #join the user and assistant messages from history to create the prompt. This is done to preserve context
    modPrompt = "\n".join([h["content"] for h in cfg.history if h["role"] == "user" or h["role"] == "assistant"])
    print("modPrompt: {}".format(modPrompt)) if cfg.debugLevel > 1 else None

    ragData = query_vectorstore(modPrompt, cfg.documentSource)
    print("ragData: {}\nLength of RAG list: {}".format(ragData, len(ragData))) if cfg.debugLevel > 1 else None
    
    response = get_litellm_generator_response(ragData, jsonOutput=jsonOutput, schema=schema)
    print("Full response: {}".format(response)) if cfg.debugLevel > 1 else None

    assistantMessage = {'role':'assistant', 'content': response.choices[0].message.content}
    print("Assistant Message: {}".format(assistantMessage)) if cfg.debugLevel > 1 else None

    add_to_history(assistantMessage)
    text = assistantMessage['content']

    return text

def evaluate_response(generatorResponse, ragData):
    verdict = False
    print("Evaluating response...")
    response2 = get_litellm_evaluator_response(generatorResponse, ragData, jsonOutput=True, schema=cfg.judgeSchema)
    verdictStr = response2.choices[0].message.content
    print("Verdict str: {}".format(verdictStr))
    #strip the json from the response by locating the position of { and }
    start = verdictStr.find("{")
    end = verdictStr.rfind("}")
    if start != -1 and end != -1:
        verdictStr = verdictStr[start:end+1]
    try:
        verdictJson = json.loads(verdictStr, strict=True)
        print("Verdict: {}".format(verdictJson))
        verdict = (verdictJson["correct"] == True)
    except Exception as e:
        print("Error parsing verdict JSON: {}".format(e))
        verdict = False

    return verdict

def get_litellm_generator_response(ragData, jsonOutput=False, schema=None):
    context = [d for d in ragData['documents']]
    print("Number of context documents: {}".format(len(context))) if cfg.debugLevel > 1 else None

    systemPrompt = cfg.sysPrompt + f"""
<context>
    {context}
</context>
"""

    print("System Prompt: {}".format(systemPrompt)) if cfg.debugLevel > 1 else None

    messages = [
        {"role": "system", "content": systemPrompt}
    ]

    messages.extend(cfg.history)
    print("Number of messages: {}, context length: {}".format(len(messages), len(json.dumps(context)))) if cfg.debugLevel > 1 else None

    args = {
        "model" : cfg.generatorModelId,
        "messages" : messages,
        "temperature" : cfg.temperature
    }

    if jsonOutput:
        args["format"] = "json"
        args["response_format"] = {
            "type": "json_schema",
            "json_schema": {"schema": schema, "name": "schema", "strict": True},
        }

    response = litellm.completion(
        **args
    )

    return response

def get_litellm_evaluator_response(generatorResponse, ragData, jsonOutput=True, schema=cfg.judgeSchema):
    context = [d for d in ragData['documents']]
    print("Number of context documents: {}".format(len(context))) if cfg.debugLevel > 1 else None

    systemPrompt = cfg.judgeModePrompt + f"""
<context>
    {context}
</context>
"""

    print("System Prompt: {}".format(systemPrompt)) if cfg.debugLevel > 1 else None

    messages = [
        {"role": "system", "content": systemPrompt}
    ]

    #messages.extend(cfg.history)
    messages.append({'role':'user', 'content': f"""
Evaluate the passage presented below between <passage></passage> for accuracy
<passage>
{generatorResponse}
</passage>"""})
    print("Number of messages: {}, context length: {}".format(len(messages), len(json.dumps(context)))) if cfg.debugLevel > 1 else None

    args = {
        "model" : cfg.judgeModelId,
        "messages" : messages,
        "temperature" : 0
    }

    if jsonOutput:
        args["format"] = "json"
        args["response_format"] = {
            "type": "json_schema",
            "json_schema": {"schema": schema, "name": "schema", "strict": True},
        }

    response = litellm.completion(
        **args
    )

    return response

def select_document(msg):
    tries = 0
    while True and tries < 4:
        tries += 1
        if tries >= 4:
            print("Sorry, I'm unable to help you.  Please try later!")
            status = "exit"
            break

        print(msg)
        for i,d in enumerate(cfg.documents):
            print("{}. {}".format(i+1,d))

        numDocuments = len(cfg.documents)
        num = input("Select (1-{}): ".format(numDocuments))
        if num.strip().lower() in ["exit", "bye", "quit", "end"]:
            status = "exit"
            break
        elif not num.isdigit() or int(num) < 1 or int(num) > numDocuments:
            print("Invalid number.")
            continue
        else:
            status="ok"
            break

    print("-"*40)
    if status == "exit":
        print("Goodbye!")
        exit(0)
    elif status == "ok":
        return cfg.documents[int(num)-1]

def write_log(f, msg):
    current_datetime = datetime.now()

    with open(f, "a") as fd:
        fd.write(str(current_datetime) + ":" + msg + "\n")

def initialize():
    print("Initializing...")
    absPath = os.path.abspath(cfg.chromaPath)
    print("Chroma abs path: {}".format(absPath)) if cfg.debugLevel > 0 else None

    cfg.chromaClient = chromadb.PersistentClient(
        path=absPath
    )

    cfg.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=cfg.embedderModelId
    )

    if collection_exists(cfg.collectionName):
        print("Collection {} already exists".format(cfg.collectionName))
        cfg.vectorStore = get_vectorstore()
        docsToAdd, docStemsToRemove = needs_update()
    else:
        print("Collection {} does not exist. Creating...".format(cfg.collectionName))
        docsToAdd = traverse_recursively(cfg.ragSource)

    if len(docsToAdd) > 0:
        print("Knowledge base needs to be updated with {} documents".format(len(docsToAdd)))
        docs, loadedDocs = load_docs(cfg.ragSource, docsToAdd)
        if len(docs) > 0:
            print("Loaded {} documents".format(len(docs)))
            splits = process_docs(loadedDocs)
            print("Processed into {} splits".format(len(splits)))
            cfg.vectorStore = create_or_update_vectorstore(splits)
            print("Knowledge base created with {} splits".format(cfg.vectorStore.count()))

    if len(docStemsToRemove) > 0:
        remove_docs(docStemsToRemove)

    print("Knowledge base is up to date!")

    cfg.documents = get_documents_in_store()
    print("="*80)
    print("Welcome to the StudyAId!")
    print("Number of documents in the library: {}".format(len(cfg.documents)))
    print("If you would like to exit at any time, type 'bye' or 'quit'")
    print("="*80)
