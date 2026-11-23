import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from backend.config import Config

class VectorStoreManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.index_path = Config.VECTORSTORE_DIR
        os.makedirs(self.index_path, exist_ok=True)

    def create_or_add_vectorstore(self, chunks):
        if os.path.exists(os.path.join(self.index_path, "index.faiss")):
            vectorstore = FAISS.load_local(
                self.index_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            vectorstore.add_documents(chunks)
        else:
            vectorstore = FAISS.from_documents(chunks, self.embeddings)
        
        vectorstore.save_local(self.index_path)
        return vectorstore

    def get_vectorstore(self):
        if os.path.exists(os.path.join(self.index_path, "index.faiss")):
            return FAISS.load_local(
                self.index_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        return None