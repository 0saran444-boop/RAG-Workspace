import json
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from backend.services.gemini_service import GeminiService
from backend.database.mongodb import Database
from backend.rag.rag_service import RAGService
from bson import ObjectId

class GraphState(TypedDict):
    question: str
    route: str
    result: str
    sources: list

class WorkflowManager:
    def __init__(self):
        self.gemini = GeminiService()
        self.rag_service = RAGService()
        self.workflow = self._build_graph()

    def router_node(self, state: GraphState):
        question = state["question"]
        prompt = f"""Classify the user's question into one of these three categories:
        1. "chat" - General conversational questions, greetings, or general knowledge not needing external data.
        2. "database" - Questions querying database records (like counts, students, courses, employees, products, ObjectIds, or student IDs).
        3. "documentation" - Questions asking about policies, handbooks, guidelines, manga, or any information inside uploaded documents (even single keywords if they relate to uploaded topics like Naruto or notes).

        Return ONLY a valid JSON object with keys "route" (values: "chat", "database", "documentation").

        Question: {question}
        JSON Output:"""
        
        response_text = self.gemini.generate_chat_response(prompt)
        try:
            cleaned = response_text.strip().replace("```json", "").replace("```", "")
            data = json.loads(cleaned)
            route = data.get("route", "chat")
        except Exception:
            route = "chat"

        return {"route": route}

    def chat_node(self, state: GraphState):
        answer = self.gemini.generate_chat_response(state["question"])
        return {"result": answer, "sources": []}

    def database_node(self, state: GraphState):
        question = state["question"].strip()
        db = Database.connect()
        
        found_record = None
        target_collection = ""
        
        # Search collections for specific student IDs or ObjectIds
        try:
            for coll_name in db.list_collection_names():
                if coll_name == "pdf_metadata":
                    continue
                coll = db[coll_name]
                
                # Check for ObjectId match
                if "ObjectId" in question or len(question.strip('"\'')) == 24:
                    try:
                        id_str = question.split("'")[1] if "'" in question else question.strip('"\'')
                        found_record = coll.find_one({"_id": ObjectId(id_str)})
                        if found_record:
                            target_collection = coll_name
                            break
                    except Exception:
                        pass
                
                # Check for numeric student_id match
                digits = ''.join([c for c in question if c.isdigit()])
                if digits:
                    found_record = coll.find_one({"student_id": int(digits)})
                    if found_record:
                        target_collection = coll_name
                        break
        except Exception:
            pass

        if found_record:
            found_record["_id"] = str(found_record["_id"])
            context = f"Found record in collection '{target_collection}': {found_record}"
            source_label = f"Database: student_db, Collection: {target_collection}"
        else:
            summary = {}
            for coll_name in db.list_collection_names():
                if coll_name == "pdf_metadata":
                    continue
                count = db[coll_name].count_documents({})
                sample = list(db[coll_name].find({}, {"_id": 1}).limit(3))
                for s in sample:
                    s["_id"] = str(s["_id"])
                summary[coll_name] = {"count": count, "samples": sample}
            context = f"Database collections summary: {summary}"
            source_label = "Database: student_db"

        prompt = f"""You are a precise database assistant. Use the provided database context to answer the user's question.
You MUST format your response in EXACTLY 5 lines:
- Lines 1 to 4: Concise factual points answering the question (including record details, ID, and collection/column names).
- Line 5: State the source database, collection, and record info.
If the answer cannot be found, output 5 lines stating that it is not found, with Line 5 as "Source: None".

Context:
{context}

Question: {question}

Answer (strictly 5 lines):"""

        answer = self.gemini.generate_chat_response(prompt)
        return {"result": answer, "sources": [source_label]}

    def documentation_node(self, state: GraphState):
        res = self.rag_service.query(state["question"])
        
        if not res.get("found", True):
            fallback_answer = self.gemini.generate_chat_response(state["question"])
            return {
                "result": fallback_answer,
                "sources": [],
                "route": "chat (fallback)"
            }

        return {
            "result": res["answer"],
            "sources": res["sources"]
        }

    def decide_route(self, state: GraphState):
        return state["route"]

    def _build_graph(self):
        builder = StateGraph(GraphState)

        builder.add_node("router", self.router_node)
        builder.add_node("chat", self.chat_node)
        builder.add_node("database", self.database_node)
        builder.add_node("documentation", self.documentation_node)

        builder.add_edge(START, "router")
        builder.add_conditional_edges(
            "router",
            self.decide_route,
            {
                "chat": "chat",
                "database": "database",
                "documentation": "documentation"
            }
        )
        builder.add_edge("chat", END)
        builder.add_edge("database", END)
        builder.add_edge("documentation", END)

        return builder.compile()

    def run(self, question: str):
        initial_state = {"question": question, "route": "", "result": "", "sources": []}
        final_state = self.workflow.invoke(initial_state)
        return {
            "route": final_state["route"],
            "answer": final_state["result"],
            "sources": final_state.get("sources", [])
        }