from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.rag.vector_store import VectorStoreManager
from backend.services.gemini_service import GeminiService
from backend.database.mongodb import Database

class RAGService:
    def __init__(self):
        self.vector_store_manager = VectorStoreManager()
        self.gemini = GeminiService()

    def process_and_index_pdf(self, file_path: str, filename: str) -> int:
        """Loads a PDF, splits it into chunks, saves them to the FAISS vector store, and updates MongoDB metadata."""
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(docs)
        chunk_count = len(chunks)

        if chunks:
            self.vector_store_manager.create_or_add_vectorstore(chunks)

        # Save/Update metadata in MongoDB so the UI displays the correct count
        metadata_coll = Database.get_collection("pdf_metadata")
        metadata_coll.update_one(
            {"filename": filename},
            {
                "$set": {
                    "filename": filename,
                    "chunks_count": chunk_count,  # Matched with frontend expectation
                    "file_path": file_path
                }
            },
            upsert=True
        )

        return chunk_count

    def query(self, question: str) -> dict:
        vectorstore = self.vector_store_manager.get_vectorstore()
        if not vectorstore:
            return {
                "found": False,
                "answer": "1. No documents found.\n2. Vector store is empty.\n3. Please upload documents.\n4. Check sidebar.\n5. Source: None",
                "sources": []
            }

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        relevant_docs = retriever.invoke(question)

        if not relevant_docs:
            return {
                "found": False,
                "answer": "1. Answer not found in docs.\n2. Try a different query.\n3. Check database records.\n4. Verify indexed files.\n5. Source: None",
                "sources": []
            }

        # Fetch MongoDB metadata for chunks and collection details
        db = Database.connect()
        metadata_coll = db["pdf_metadata"]
        
        context_parts = []
        sources = []
        
        for doc in relevant_docs:
            source_name = doc.metadata.get("source", doc.metadata.get("filename", "Unknown PDF"))
            sources.append(source_name)
            
            # Query MongoDB for specific document chunk count and record ID
            db_record = metadata_coll.find_one({"filename": source_name})
            record_info = ""
            if db_record:
                record_id = str(db_record.get("_id", ""))
                chunks_count = db_record.get("chunks_count", db_record.get("chunks", 0))
                record_info = f" [DB ID: {record_id}, Chunks: {chunks_count}, Collection: pdf_metadata]"
            
            context_parts.append(f"Content: {doc.page_content}\nSource File: {source_name}{record_info}")

        context = "\n\n".join(context_parts)
        unique_sources = list(set(sources))

        answer = self.gemini.generate_rag_response(context, question)

        return {
            "found": True,
            "answer": answer,
            "sources": unique_sources
        }