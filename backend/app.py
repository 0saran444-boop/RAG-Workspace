import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template
from flask_cors import CORS
from backend.config import Config
from backend.database.mongodb import Database
from backend.rag.rag_service import RAGService
from backend.routes.chat_routes import chat_bp

# Explicitly set paths relative to backend directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

app.register_blueprint(chat_bp, url_prefix="/api")

@app.route("/", methods=["GET"])
def serve_frontend():
    return render_template("index.html")

def populate_existing_documents():
    docs_dir = Config.DOCUMENTS_DIR
    if os.path.exists(docs_dir):
        metadata_coll = Database.get_collection("pdf_metadata")
        rag_service = None
        for filename in os.listdir(docs_dir):
            if filename.endswith(".pdf"):
                # Only process if not already indexed in MongoDB
                if not metadata_coll.find_one({"filename": filename}):
                    if rag_service is None:
                        rag_service = RAGService()
                    file_path = os.path.join(docs_dir, filename)
                    print(f"Ensuring metadata for: {filename}")
                    rag_service.process_and_index_pdf(file_path, filename)

if __name__ == "__main__":
    # Populate existing files into MongoDB on startup
    populate_existing_documents()
    
    # Start the Flask app server
    app.run(host="0.0.0.0", port=5000, debug=True)