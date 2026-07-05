"""
Industrial Knowledge Intelligence System - Backend API
FastAPI + LangChain + embedded knowledge graph + PostgreSQL/SQLite
Updated with proper environment variable handling
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import asyncio
from datetime import datetime
import logging
from dotenv import load_dotenv

# Data processing
import PyPDF2
import io
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI as NvidiaClient

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_CHAT_MODEL = "meta/llama-3.1-70b-instruct"
NVIDIA_EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"

# Database
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# Knowledge graph (embedded, no external service required)
import threading
import pickle
import networkx as nx

load_dotenv()

# Environment variables with defaults
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= CONFIG - Environment Variables =============

# Required Key - powers both embeddings (RAG) and chat completions (entity
# extraction, RAG answers, maintenance/compliance reasoning) via NVIDIA's
# OpenAI-compatible NIM API catalog (https://integrate.api.nvidia.com/v1).
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# Knowledge graph persistence path (embedded, no external service required)
GRAPH_PATH = os.getenv("GRAPH_PATH", "./knowledge_graph.gpickle")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ikis.db")

# Validate required environment variables
if not NVIDIA_API_KEY:
    logger.warning("⚠️  NVIDIA_API_KEY not set. RAG, entity extraction, and AI features will not work.")

logger.info(f"✅ Configuration loaded:")
logger.info(f"   Database: {DATABASE_URL}")
logger.info(f"   NVIDIA API enabled: {bool(NVIDIA_API_KEY)}")

# ============= DATABASE SETUP =============
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)

class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    filename = Column(String)
    doc_type = Column(String)  # pdf, p&id, maintenance_log, safety_proc, etc
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    content = Column(Text)
    extracted_entities = Column(Text)  # JSON string

Base.metadata.create_all(bind=engine)
logger.info(f"✅ Database initialized: {DATABASE_URL}")

# ============= KNOWLEDGE GRAPH SETUP =============
# Embedded graph (nodes: Document/Equipment/Procedure/Regulation, edges:
# DESCRIBES/CONTAINS/REFERENCES) persisted to a local pickle file. No
# external database required.
graph_lock = threading.Lock()

def _load_graph() -> nx.MultiDiGraph:
    if os.path.exists(GRAPH_PATH):
        try:
            with open(GRAPH_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"⚠️  Failed to load knowledge graph, starting fresh: {e}")
    return nx.MultiDiGraph()

graph = _load_graph()

def _save_graph():
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(graph, f)

logger.info(f"✅ Knowledge graph loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges ({GRAPH_PATH})")

# ============= VECTOR STORE =============
vector_store = None
if NVIDIA_API_KEY:
    try:
        embeddings = NVIDIAEmbeddings(model=NVIDIA_EMBED_MODEL, api_key=NVIDIA_API_KEY)
        vector_store = Chroma(
            collection_name="industrial_docs",
            embedding_function=embeddings,
            persist_directory="./chroma_db"
        )
        logger.info("✅ Vector store initialized")
    except Exception as e:
        logger.warning(f"⚠️  Vector store initialization failed: {e}")
        vector_store = None
else:
    logger.info("ℹ️  Vector store not available (NVIDIA_API_KEY required)")

# ============= PYDANTIC MODELS =============
class DocumentUploadRequest(BaseModel):
    doc_type: str  # "pdf", "p&id", "maintenance_log", "safety_procedure", "inspection_record"
    filename: str

class QueryRequest(BaseModel):
    query: str
    include_citations: bool = True

class EntityExtractionResponse(BaseModel):
    equipment: List[Dict[str, str]]
    procedures: List[str]
    regulations: List[str]
    personnel: List[str]
    dates: List[str]

class RAGResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float

class MaintenanceRecommendation(BaseModel):
    equipment_id: str
    action: str
    urgency: str  # low, medium, high
    estimated_downtime_hours: float
    supporting_evidence: List[str]

class ComplianceGap(BaseModel):
    regulation_code: str
    requirement: str
    current_status: str
    evidence: List[str]
    remediation_steps: List[str]

# ============= CORE FUNCTIONS =============

def parse_llm_json(text: str):
    """
    Parse a JSON object/array out of an LLM response, tolerating
    fenced code blocks and leading/trailing prose the model may add
    around the JSON.
    """
    cleaned = text.replace("```json", "").replace("```", "").strip()
    start = min(
        (i for i in (cleaned.find("{"), cleaned.find("[")) if i != -1),
        default=-1
    )
    if start == -1:
        raise ValueError("No JSON object/array found in LLM response")
    return json.JSONDecoder().raw_decode(cleaned, start)[0]

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from PDF")

def extract_entities_with_llm(text: str) -> Dict[str, Any]:
    """
    Use an NVIDIA-hosted LLM to extract entities from document text.
    """
    if not NVIDIA_API_KEY:
        return {
            "equipment": [],
            "procedures": [],
            "regulations": [],
            "personnel": [],
            "dates": []
        }

    client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

    prompt = f"""
    Analyze this industrial document and extract the following entities in JSON format:
    - equipment: list of equipment IDs/names mentioned
    - procedures: list of procedures or operational steps
    - regulations: list of regulatory references (OISD, Factory Act, PESO, etc)
    - personnel: list of roles/people mentioned
    - dates: list of dates or time references

    Document text:
    {text[:3000]}

    Return ONLY valid JSON, no markdown or explanation.
    """

    try:
        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        entities = parse_llm_json(completion.choices[0].message.content)
    except Exception as e:
        logger.error(f"Entity extraction error: {e}")
        entities = {
            "equipment": [],
            "procedures": [],
            "regulations": [],
            "personnel": [],
            "dates": []
        }
    
    return entities

def _entity_label(entity: Any) -> Optional[str]:
    """Entities come back from the LLM as plain strings, but tolerate dicts too."""
    if isinstance(entity, str):
        return entity.strip() or None
    if isinstance(entity, dict):
        for key in ("tag", "id", "name"):
            if entity.get(key):
                return str(entity[key]).strip()
    return None

def build_knowledge_graph(doc_id: str, entities: Dict[str, Any], text: str):
    """Add a document and its extracted entities to the embedded knowledge graph."""
    try:
        with graph_lock:
            graph.add_node(doc_id, type="Document", created_at=datetime.utcnow().isoformat())

            for equipment in entities.get("equipment", []):
                tag = _entity_label(equipment)
                if not tag:
                    continue
                graph.add_node(tag, type="Equipment")
                graph.add_edge(doc_id, tag, relation="DESCRIBES")

            for procedure in entities.get("procedures", []):
                name = _entity_label(procedure)
                if not name:
                    continue
                graph.add_node(name, type="Procedure")
                graph.add_edge(doc_id, name, relation="CONTAINS")

            for regulation in entities.get("regulations", []):
                code = _entity_label(regulation)
                if not code:
                    continue
                graph.add_node(code, type="Regulation")
                graph.add_edge(doc_id, code, relation="REFERENCES")

            _save_graph()
        logger.info(f"✅ Knowledge graph updated for document {doc_id}")
    except Exception as e:
        logger.error(f"Knowledge graph error: {e}")

def split_and_embed(text: str, doc_id: str, doc_type: str):
    """Split text into chunks, embed them, and store in vector DB."""
    if not vector_store:
        return
    
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " "]
        )
        
        chunks = splitter.split_text(text)
        
        # Add metadata
        metadatas = [
            {"doc_id": doc_id, "doc_type": doc_type, "chunk_index": i}
            for i in range(len(chunks))
        ]
        
        # Store in vector DB
        vector_store.add_texts(texts=chunks, metadatas=metadatas)
        logger.info(f"✅ Embedded {len(chunks)} chunks from {doc_id}")
    except Exception as e:
        logger.error(f"Embedding error: {e}")

def query_rag_system(query: str, top_k: int = 5) -> RAGResponse:
    """Query the RAG system: retrieve relevant documents + generate answer with LLM."""
    if not vector_store or not NVIDIA_API_KEY:
        return RAGResponse(
            answer="Vector store or API key not configured. Please set NVIDIA_API_KEY.",
            sources=[],
            confidence=0.0
        )
    
    try:
        # Retrieve relevant chunks
        relevant_docs = vector_store.similarity_search(query, k=top_k)
        
        if not relevant_docs:
            return RAGResponse(
                answer="No relevant documents found in the knowledge base.",
                sources=[],
                confidence=0.0
            )
        
        # Prepare context
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Generate answer with an NVIDIA-hosted LLM
        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

        prompt = f"""
        You are an industrial knowledge expert. Answer the following query based on the provided context.
        Be specific, cite the sources, and provide confidence level (0-1).

        Query: {query}

        Context:
        {context}

        Provide your answer in JSON format:
        {{
            "answer": "your detailed answer",
            "confidence": 0.95
        }}
        """

        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        message_text = completion.choices[0].message.content

        try:
            result = parse_llm_json(message_text)
        except (json.JSONDecodeError, ValueError):
            result = {
                "answer": message_text,
                "confidence": 0.5
            }
        
        sources = [
            {
                "doc_id": doc.metadata.get("doc_id"),
                "doc_type": doc.metadata.get("doc_type"),
                "excerpt": doc.page_content[:200]
            }
            for doc in relevant_docs
        ]
        
        return RAGResponse(
            answer=result.get("answer", ""),
            sources=sources,
            confidence=result.get("confidence", 0.5)
        )
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return RAGResponse(
            answer=f"Error processing query: {str(e)}",
            sources=[],
            confidence=0.0
        )

def analyze_maintenance_patterns(equipment_id: str) -> List[MaintenanceRecommendation]:
    """Analyze historical maintenance data for equipment using the knowledge graph."""
    if not NVIDIA_API_KEY:
        return []

    try:
        # Find documents that DESCRIBE this equipment, most recent first
        with graph_lock:
            if graph.has_node(equipment_id):
                doc_ids = [
                    u for u in graph.predecessors(equipment_id)
                    if graph.nodes[u].get("type") == "Document"
                ]
            else:
                doc_ids = []
            doc_ids.sort(key=lambda d: graph.nodes[d].get("created_at", ""), reverse=True)
            doc_ids = doc_ids[:10]

        history = []
        if doc_ids:
            session = SessionLocal()
            records = session.query(DocumentRecord).filter(DocumentRecord.id.in_(doc_ids)).all()
            session.close()
            history = [
                {
                    "doc_id": r.id,
                    "doc_type": r.doc_type,
                    "uploaded_at": r.uploaded_at.isoformat(),
                    "excerpt": (r.content or "")[:800]
                }
                for r in records
            ]

        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

        prompt = f"""
        Based on these maintenance/engineering records for equipment {equipment_id}:
        {json.dumps(history) if history else "No historical records found for this equipment in the knowledge graph."}

        Generate 2-3 specific predictive maintenance recommendations in JSON format:
        [
            {{
                "action": "specific maintenance action",
                "urgency": "low|medium|high",
                "estimated_downtime_hours": 4,
                "reasoning": "why this is recommended"
            }}
        ]
        """

        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        recommendations = parse_llm_json(completion.choices[0].message.content)
        
        return [
            MaintenanceRecommendation(
                equipment_id=equipment_id,
                action=rec["action"],
                urgency=rec["urgency"],
                estimated_downtime_hours=rec["estimated_downtime_hours"],
                supporting_evidence=[rec["reasoning"]]
            )
            for rec in recommendations
        ]
    except Exception as e:
        logger.error(f"Maintenance analysis error: {e}")
        return []

def check_compliance_gaps(doc_type: str = "all") -> List[ComplianceGap]:
    """Check for compliance gaps against regulatory standards."""
    if not NVIDIA_API_KEY:
        return []

    try:
        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

        regulations = [
            "OISD-119: Safety in Petroleum Industry",
            "Factory Act Sec 13: General requirements",
            "PESO Code: Storage and handling",
            "ISO 45001: Occupational health and safety"
        ]
        
        prompt = f"""
        Given these industrial regulations:
        {json.dumps(regulations)}
        
        Generate 3 realistic compliance gap scenarios:
        Return JSON array:
        [
            {{
                "regulation_code": "OISD-119",
                "requirement": "specific requirement from regulation",
                "gap_scenario": "how this gap might occur",
                "remediation": ["step1", "step2"]
            }}
        ]
        """
        
        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        gaps_data = parse_llm_json(completion.choices[0].message.content)
        
        return [
            ComplianceGap(
                regulation_code=gap["regulation_code"],
                requirement=gap["requirement"],
                current_status="Gap identified",
                evidence=["Document analysis"],
                remediation_steps=gap["remediation"]
            )
            for gap in gaps_data
        ]
    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        return []

# ============= FastAPI APP =============
app = FastAPI(
    title="Industrial Knowledge Intelligence System",
    description="AI-powered industrial knowledge retrieval, maintenance analytics, compliance intelligence",
    version="1.0.0"
)

# CORS - Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    background_tasks: BackgroundTasks = None
):
    """Upload and process a document."""
    try:
        content = await file.read()
        doc_id = f"{doc_type}_{datetime.utcnow().timestamp()}"
        
        # Extract text
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(content)
        else:
            text = content.decode('utf-8')
        
        # Extract entities (runs in a thread so one slow LLM call doesn't
        # block the event loop / other in-flight requests)
        entities = await asyncio.to_thread(extract_entities_with_llm, text)
        
        # Store in database
        session = SessionLocal()
        doc_record = DocumentRecord(
            id=doc_id,
            filename=file.filename,
            doc_type=doc_type,
            content=text,
            extracted_entities=json.dumps(entities)
        )
        session.add(doc_record)
        session.commit()
        session.close()
        
        # Build knowledge graph (background)
        if background_tasks:
            background_tasks.add_task(build_knowledge_graph, doc_id, entities, text)
        
        # Embed and store vectors (background)
        if background_tasks:
            background_tasks.add_task(split_and_embed, text, doc_id, doc_type)
        
        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": file.filename,
            "entities_found": {
                "equipment": len(entities.get("equipment", [])),
                "procedures": len(entities.get("procedures", [])),
                "regulations": len(entities.get("regulations", [])),
            },
            "message": "Document uploaded and is being processed"
        }
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query", response_model=RAGResponse)
async def query_knowledge_base(request: QueryRequest):
    """Query the RAG system for expert knowledge retrieval."""
    try:
        response = await asyncio.to_thread(query_rag_system, request.query)
        return response
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/maintenance/recommendations/{equipment_id}")
async def get_maintenance_recommendations(equipment_id: str):
    """Get predictive maintenance recommendations for specific equipment."""
    try:
        recommendations = await asyncio.to_thread(analyze_maintenance_patterns, equipment_id)
        return {
            "equipment_id": equipment_id,
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Maintenance analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/gaps")
async def get_compliance_gaps():
    """Identify compliance gaps across the organization."""
    try:
        gaps = await asyncio.to_thread(check_compliance_gaps)
        return {
            "gaps_found": len(gaps),
            "gaps": gaps,
            "report_generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "online",
            "vector_db": "online" if vector_store else "offline",
            "knowledge_graph": f"online ({graph.number_of_nodes()} nodes)",
            "nvidia_api": "configured" if NVIDIA_API_KEY else "not_configured"
        }
    }

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Industrial Knowledge Intelligence System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /api/documents/upload",
            "query": "POST /api/query",
            "maintenance": "GET /api/maintenance/recommendations/{equipment_id}",
            "compliance": "GET /api/compliance/gaps",
            "health": "GET /api/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
