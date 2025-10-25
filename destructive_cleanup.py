import os
import chromadb
from chromadb.utils import embedding_functions

import raghelper as rag
import config as cfg

if __name__ == "__main__":
    absPath = os.path.abspath(cfg.chromaPath)
    print("Chroma abs path: {}".format(absPath)) if cfg.debugLevel > 0 else None

    cfg.chromaClient = chromadb.PersistentClient(
        path=absPath
    )

    cfg.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=cfg.embedderModelId
    )

    allowed_options = []
    print("1. Remove chroma data folder")
    allowed_options.append("1")
    if rag.collection_exists(cfg.collectionName):
        print("2. Remove current collection: {}".format(cfg.collectionName))
        print("3. Remove all collections")
        allowed_options.extend(["2", "3"])
    response = input("Select an option:")
    if response == "1" and "1" in allowed_options:
        rag.remove_chroma_data_folder()
        print("Removed chroma data folder.")
    elif response == "2" and "2" in allowed_options:
        rag.cleanup(cfg.collectionName)
        print("Removed collection: {}".format(cfg.collectionName))
    elif response == "3" and "3" in allowed_options:
        rag.cleanup_all()
        print("Removed all collections.")
    else:
        print("Invalid option.")
        exit(0)
