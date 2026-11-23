import os
from flask import Blueprint, request, jsonify
from bson import ObjectId
from backend.config import Config
from backend.database.mongodb import Database
from backend.graph.workflow import WorkflowManager
from backend.rag.rag_service import RAGService

chat_bp = Blueprint("chat_bp", __name__)
workflow_manager = WorkflowManager()
rag_service = RAGService()

@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        response = workflow_manager.run(question)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        os.makedirs(Config.DOCUMENTS_DIR, exist_ok=True)
        file_path = os.path.join(Config.DOCUMENTS_DIR, file.filename)
        file.save(file_path)

        # Index the PDF using RAG service
        rag_service.process_and_index_pdf(file_path, file.filename)
        return jsonify({"message": f"Successfully uploaded and indexed {file.filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to view uploaded documents from "pdf_metadata" collection
@chat_bp.route("/documents", methods=["GET"])
def get_documents():
    try:
        db = Database.connect()
        metadata_coll = db["pdf_metadata"]  # Fixed to match RAGService collection name
        docs = list(metadata_coll.find({}))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return jsonify({"documents": docs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to delete a specific document by ID from "pdf_metadata" collection
@chat_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    try:
        db = Database.connect()
        metadata_coll = db["pdf_metadata"]  # Fixed to match RAGService collection name
        
        # Remove the local file if it exists
        doc = metadata_coll.find_one({"_id": ObjectId(doc_id)})
        if doc and "filename" in doc:
            file_path = os.path.join(Config.DOCUMENTS_DIR, doc["filename"])
            if os.path.exists(file_path):
                os.remove(file_path)

        result = metadata_coll.delete_one({"_id": ObjectId(doc_id)})
        if result.deleted_count > 0:
            return jsonify({"message": "Document deleted successfully"})
        return jsonify({"error": "Document not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to view MongoDB database summary and records
@chat_bp.route("/database", methods=["GET"])
def get_database_records():
    try:
        db = Database.connect()
        db_summary = {}
        for coll_name in db.list_collection_names():
            if coll_name == "pdf_metadata":
                continue
            count = db[coll_name].count_documents({})
            samples = list(db[coll_name].find({}, {"_id": 0}).limit(10))
            db_summary[coll_name] = {
                "count": count,
                "records": samples
            }
        return jsonify({"database": db_summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500