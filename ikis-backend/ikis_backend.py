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
import mimetypes
from datetime import datetime
import logging
from dotenv import load_dotenv

# Data processing
import PyPDF2
import io
import base64
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI as NvidiaClient

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_CHAT_MODEL = "meta/llama-3.1-70b-instruct"
NVIDIA_EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
NVIDIA_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

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
NVIDIA_API_KEY = (os.getenv("NVIDIA_API_KEY") or "").strip() or None

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

class LessonsPattern(BaseModel):
    pattern: str
    risk_level: str  # low, medium, high
    affected_equipment: List[str]
    supporting_doc_ids: List[str]
    recommended_action: str

class RCAReport(BaseModel):
    equipment_id: str
    immediate_cause: str
    root_cause: str
    contributing_factors: List[str]
    corrective_actions: List[str]
    relevant_procedures: List[str]
    relevant_regulations: List[str]

class QualityDeviation(BaseModel):
    parameter: str
    observed_value: str
    expected_or_baseline: str
    severity: str  # low, medium, high
    evidence_doc_id: str
    recommended_action: str

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

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

def extract_text_from_image(file_content: bytes, mime_type: str = "image/png") -> str:
    """
    OCR / document-intelligence for scanned forms and P&ID drawings via a
    vision-language model (NVIDIA NIM). Reads printed and hand-labeled text,
    tags, and callouts directly from the image — no separate OCR engine
    required. Does not attempt schematic/symbol recognition (line routing,
    instrument bubbles) — text and tag transcription only.
    """
    if not NVIDIA_API_KEY:
        raise HTTPException(status_code=400, detail="NVIDIA_API_KEY not configured; cannot process images")

    b64 = base64.b64encode(file_content).decode()
    client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

    prompt = (
        "This is a scanned industrial document or P&ID-style drawing. Transcribe every piece of "
        "visible text exactly as written: equipment tags, labels, callouts, handwritten notes, "
        "table values, stamps, and signatures. Preserve structure with line breaks. If it's a "
        "diagram, also list the equipment tags and their apparent connections/relationships as "
        "plain text after the transcription, under a 'DIAGRAM RELATIONSHIPS:' heading."
    )

    try:
        completion = client.chat.completions.create(
            model=NVIDIA_VISION_MODEL,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}}
                ]
            }]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Image OCR error: {e}")
        raise HTTPException(status_code=400, detail="Failed to extract text from image")

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
        You are an industrial knowledge expert. Answer the query using ONLY the context below.

        The context was retrieved by vector similarity search, which always returns its closest
        matches even when nothing in the knowledge base is actually relevant to the query. Before
        answering, judge for yourself whether the context genuinely addresses the query.

        - If the query is a greeting, small talk, or unrelated to the context, write one natural,
          conversational sentence explaining that you didn't find anything about that topic in the
          uploaded documents, and set confidence to 0.0. Do not force an industrial answer out of
          unrelated context, and do not just say "not relevant" — respond the way a helpful
          colleague would.
        - Otherwise, answer specifically, cite the sources, and set a genuine confidence level (0-1).

        Query: {query}

        Context:
        {context}

        Respond in JSON format: {{"answer": "...", "confidence": 0.0-1.0}}
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
        
        confidence = result.get("confidence", 0.5)

        # The model judged the retrieved context irrelevant to the query — don't
        # show sources that weren't actually used, that reads as a contradiction.
        sources = []
        if confidence > 0:
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
            confidence=confidence
        )
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return RAGResponse(
            answer=f"Error processing query: {str(e)}",
            sources=[],
            confidence=0.0
        )

def _get_equipment_history(equipment_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Documents describing this equipment, most recent first. Combines two
    retrieval paths: graph traversal (exact-match equipment tag from entity
    extraction) and semantic search (robust to the LLM tagging a document
    under a variant label, e.g. "Unit 2" instead of "COMPRESSOR-02", which
    would otherwise make the graph silently miss a real, relevant document).
    """
    with graph_lock:
        if graph.has_node(equipment_id):
            doc_ids = {
                u for u in graph.predecessors(equipment_id)
                if graph.nodes[u].get("type") == "Document"
            }
        else:
            doc_ids = set()

    if vector_store:
        try:
            semantic_docs = vector_store.similarity_search(equipment_id, k=limit)
            doc_ids.update(d.metadata.get("doc_id") for d in semantic_docs if d.metadata.get("doc_id"))
        except Exception as e:
            logger.warning(f"Equipment history semantic fallback failed: {e}")

    if not doc_ids:
        return []

    session = SessionLocal()
    records = session.query(DocumentRecord).filter(DocumentRecord.id.in_(doc_ids)).all()
    session.close()
    records.sort(key=lambda r: r.uploaded_at, reverse=True)
    return [
        {
            "doc_id": r.id,
            "doc_type": r.doc_type,
            "uploaded_at": r.uploaded_at.isoformat(),
            "excerpt": (r.content or "")[:800]
        }
        for r in records[:limit]
    ]

def analyze_maintenance_patterns(equipment_id: str) -> List[MaintenanceRecommendation]:
    """Analyze historical maintenance data for equipment using the knowledge graph."""
    if not NVIDIA_API_KEY:
        return []

    try:
        history = _get_equipment_history(equipment_id)
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

def perform_rca(equipment_id: str) -> Optional[RCAReport]:
    """
    Multi-step Root Cause Analysis agent — three independent retrieval steps
    feeding one synthesis step, rather than a single flat RAG call:
      1. Graph traversal -> this equipment's document history
      2. Vector search -> safety procedures relevant to this equipment
      3. Vector search -> regulations relevant to this equipment
      4. LLM synthesis -> structured RCA grounded in all three retrievals
    """
    if not NVIDIA_API_KEY:
        return None

    history = _get_equipment_history(equipment_id)
    if not history:
        return None

    procedures_context: List[str] = []
    regulations_context: List[str] = []
    if vector_store:
        try:
            proc_docs = vector_store.similarity_search(f"safety procedure for {equipment_id}", k=3)
            procedures_context = [d.page_content[:500] for d in proc_docs]
        except Exception as e:
            logger.warning(f"RCA procedure retrieval failed: {e}")
        try:
            reg_docs = vector_store.similarity_search(f"regulation requirement for {equipment_id}", k=3)
            regulations_context = [d.page_content[:500] for d in reg_docs]
        except Exception as e:
            logger.warning(f"RCA regulation retrieval failed: {e}")

    history_text = "\n\n".join(f"[{h['doc_id']}] ({h['doc_type']})\n{h['excerpt']}" for h in history)
    procedures_text = "\n\n".join(procedures_context) if procedures_context else "None found."
    regulations_text = "\n\n".join(regulations_context) if regulations_context else "None found."

    prompt = f"""
    You are conducting a Root Cause Analysis for {equipment_id}, drawing on three
    independently retrieved sources.

    EQUIPMENT HISTORY (work orders, inspections, manuals — retrieved via knowledge
    graph traversal):
    {history_text}

    RELATED SAFETY PROCEDURES (retrieved separately via semantic search):
    {procedures_text}

    RELATED REGULATIONS (retrieved separately via semantic search):
    {regulations_text}

    Produce a structured Root Cause Analysis. Distinguish the immediate cause (what
    directly happened) from the root cause (the underlying process or systemic
    reason it happened), list contributing factors, concrete corrective actions,
    and which of the retrieved procedures/regulations above are actually relevant.
    If the history doesn't describe an actual failure, analyze the equipment's
    biggest latent risk instead.

    Return JSON:
    {{
        "immediate_cause": "...",
        "root_cause": "...",
        "contributing_factors": ["...", "..."],
        "corrective_actions": ["...", "..."],
        "relevant_procedures": ["..."],
        "relevant_regulations": ["..."]
    }}
    """

    try:
        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}]
        )
        data = parse_llm_json(completion.choices[0].message.content)
        return RCAReport(
            equipment_id=equipment_id,
            immediate_cause=data.get("immediate_cause", ""),
            root_cause=data.get("root_cause", ""),
            contributing_factors=data.get("contributing_factors", []),
            corrective_actions=data.get("corrective_actions", []),
            relevant_procedures=data.get("relevant_procedures", []),
            relevant_regulations=data.get("relevant_regulations", [])
        )
    except Exception as e:
        logger.error(f"RCA error: {e}")
        return None

def check_compliance_gaps(doc_type: str = "all") -> List[ComplianceGap]:
    """
    Check for compliance gaps. Grounded in real uploaded regulatory documents
    (doc_type='regulatory') cross-referenced against operational documents when
    any have been uploaded; falls back to clearly-labeled representative
    scenarios otherwise.
    """
    if not NVIDIA_API_KEY:
        return []

    try:
        session = SessionLocal()
        reg_records = session.query(DocumentRecord).filter(DocumentRecord.doc_type == "regulatory").all()
        other_records = session.query(DocumentRecord).filter(DocumentRecord.doc_type != "regulatory").limit(10).all()
        session.close()

        grounded = bool(reg_records)

        if grounded:
            regulations_text = "\n\n".join(f"[{r.id}] {(r.content or '')[:1500]}" for r in reg_records)
            operations_text = "\n\n".join(
                f"[{r.id}] ({r.doc_type}) {(r.content or '')[:600]}" for r in other_records
            ) or "No other operational documents uploaded yet."

            prompt = f"""
            You are a compliance auditor. Below are regulatory/procedure documents that have
            actually been uploaded to this system, followed by operational documents (equipment
            manuals, maintenance logs, inspection reports) also uploaded.

            REGULATORY DOCUMENTS:
            {regulations_text}

            OPERATIONAL DOCUMENTS:
            {operations_text}

            Identify specific compliance gaps: places where the operational documents show a
            requirement from the regulatory documents is not being met, or where evidence of
            compliance is missing or incomplete. Ground every gap in the actual text provided
            above — do not invent regulations that were not provided.

            Return a JSON array:
            [
                {{
                    "regulation_code": "short code or name, drawn from the regulatory document",
                    "requirement": "the specific requirement from the uploaded regulatory text",
                    "gap_scenario": "the specific evidence from the operational documents showing the gap",
                    "remediation": ["step1", "step2"]
                }}
            ]
            """
            max_tok = 1200
        else:
            regulations = [
                "OISD-119: Safety in Petroleum Industry",
                "Factory Act Sec 13: General requirements",
                "PESO Code: Storage and handling",
                "ISO 45001: Occupational health and safety"
            ]
            prompt = f"""
            No regulatory documents have been uploaded yet. Generate 3 representative example
            compliance gap scenarios — clearly illustrative, not based on real evidence — for
            these regulations: {json.dumps(regulations)}

            Return a JSON array:
            [
                {{
                    "regulation_code": "OISD-119",
                    "requirement": "specific requirement from regulation",
                    "gap_scenario": "how this gap might occur",
                    "remediation": ["step1", "step2"]
                }}
            ]
            """
            max_tok = 800

        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=max_tok,
            messages=[{"role": "user", "content": prompt}]
        )

        gaps_data = parse_llm_json(completion.choices[0].message.content)

        return [
            ComplianceGap(
                regulation_code=gap["regulation_code"],
                requirement=gap["requirement"],
                current_status="Gap identified" if grounded else "Gap identified (representative scenario — upload regulatory documents to ground this in real evidence)",
                evidence=["Grounded in uploaded regulatory + operational documents"] if grounded else ["Representative scenario — no regulatory documents uploaded yet"],
                remediation_steps=gap["remediation"]
            )
            for gap in gaps_data
        ]
    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        return []

def detect_quality_deviations() -> List[QualityDeviation]:
    """
    Quality deviation flagging: scans uploaded inspection/maintenance/equipment
    documents for measurable parameters (vibration, temperature, pressure,
    clearance, etc.) explicitly reported as deviating from a stated baseline
    or spec, and flags them before they escalate into a compliance gap or
    safety incident. Grounded in the actual uploaded text — will not invent
    numbers that aren't present in the documents.
    """
    if not NVIDIA_API_KEY:
        return []

    try:
        session = SessionLocal()
        records = (
            session.query(DocumentRecord)
            .filter(DocumentRecord.doc_type.in_(["inspection_report", "maintenance_log", "equipment_manual"]))
            .limit(15)
            .all()
        )
        session.close()

        if not records:
            return []

        docs_text = "\n\n".join(f"[{r.id}] ({r.doc_type})\n{(r.content or '')[:1000]}" for r in records)

        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
        prompt = f"""
        You are a quality engineer reviewing inspection and maintenance records below.

        {docs_text}

        Identify specific measurable parameters (vibration, temperature, pressure, clearance,
        lubricant condition, etc.) that are reported as deviating from a stated baseline, spec,
        or normal range. Only report deviations explicitly evidenced in the text above — do not
        invent numbers that aren't present in the documents. If nothing measurable deviates,
        return an empty array.

        Return a JSON array:
        [
            {{
                "parameter": "e.g. Vibration (PUMP-001)",
                "observed_value": "the reported value",
                "expected_or_baseline": "the stated baseline or spec",
                "severity": "low|medium|high",
                "evidence_doc_id": "the [doc_id] this came from",
                "recommended_action": "specific next step"
            }}
        ]
        """
        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}]
        )
        data = parse_llm_json(completion.choices[0].message.content)
        return [
            QualityDeviation(
                parameter=d["parameter"],
                observed_value=d["observed_value"],
                expected_or_baseline=d["expected_or_baseline"],
                severity=d.get("severity", "medium"),
                evidence_doc_id=d.get("evidence_doc_id", ""),
                recommended_action=d["recommended_action"]
            )
            for d in data
        ]
    except Exception as e:
        logger.error(f"Quality deviation detection error: {e}")
        return []

def analyze_lessons_learned() -> List[LessonsPattern]:
    """
    Lessons Learned & Failure Intelligence: analyzes incident/near-miss reports
    across the organization's history to find systemic patterns no single
    document review would surface, and produce proactive warnings.
    """
    if not NVIDIA_API_KEY:
        return []

    try:
        session = SessionLocal()
        records = session.query(DocumentRecord).filter(DocumentRecord.doc_type == "incident_report").all()
        session.close()

        if not records:
            return []

        incidents_text = "\n\n".join(
            f"[{r.id}] uploaded {r.uploaded_at.isoformat()}\n{(r.content or '')[:1200]}"
            for r in records
        )

        client = NvidiaClient(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

        prompt = f"""
        You are a failure-intelligence analyst. Below are incident, near-miss, and audit
        reports uploaded to this system, from potentially different units and dates.

        INCIDENT / NEAR-MISS / AUDIT RECORDS:
        {incidents_text}

        Find systemic patterns that span MULTIPLE documents — the kind of recurring root
        cause or process failure that no single team reviewing one incident in isolation
        would notice, but that becomes obvious when the reports are read together. Do not
        just restate one incident; only report a pattern if at least two documents support it.

        For each pattern, return a proactive warning that could be pushed to operational
        teams before a similar condition recurs.

        Return a JSON array:
        [
            {{
                "pattern": "description of the recurring systemic issue",
                "risk_level": "low|medium|high",
                "affected_equipment": ["EQUIPMENT-ID", "..."],
                "supporting_doc_ids": ["doc_id1", "doc_id2"],
                "recommended_action": "specific proactive action to prevent recurrence"
            }}
        ]
        """

        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )

        patterns_data = parse_llm_json(completion.choices[0].message.content)

        return [
            LessonsPattern(
                pattern=p["pattern"],
                risk_level=p.get("risk_level", "medium"),
                affected_equipment=p.get("affected_equipment", []),
                supporting_doc_ids=p.get("supporting_doc_ids", []),
                recommended_action=p["recommended_action"]
            )
            for p in patterns_data
        ]
    except Exception as e:
        logger.error(f"Lessons learned analysis error: {e}")
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
        filename_lower = file.filename.lower()

        # Extract text
        if filename_lower.endswith('.pdf'):
            text = extract_text_from_pdf(content)
        elif filename_lower.endswith(IMAGE_EXTENSIONS):
            mime_type = mimetypes.guess_type(file.filename)[0] or "image/png"
            # Vision-model OCR call runs in a thread — same non-blocking
            # rationale as the entity-extraction call below.
            text = await asyncio.to_thread(extract_text_from_image, content, mime_type)
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

@app.get("/api/documents")
async def list_documents():
    """List every document actually in the knowledge base right now."""
    session = SessionLocal()
    records = session.query(DocumentRecord).order_by(DocumentRecord.uploaded_at.desc()).all()
    session.close()

    def entity_counts(record):
        try:
            entities = json.loads(record.extracted_entities or "{}")
        except json.JSONDecodeError:
            entities = {}
        return {
            "equipment": len(entities.get("equipment", [])),
            "procedures": len(entities.get("procedures", [])),
            "regulations": len(entities.get("regulations", [])),
        }

    return {
        "documents_found": len(records),
        "documents": [
            {
                "doc_id": r.id,
                "filename": r.filename,
                "doc_type": r.doc_type,
                "uploaded_at": r.uploaded_at.isoformat(),
                "entities_found": entity_counts(r)
            }
            for r in records
        ]
    }

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

@app.get("/api/maintenance/rca/{equipment_id}")
async def get_rca_report(equipment_id: str):
    """Multi-step Root Cause Analysis for specific equipment."""
    try:
        report = await asyncio.to_thread(perform_rca, equipment_id)
        return {
            "equipment_id": equipment_id,
            "report": report,
            "message": None if report else "No document history found for this equipment in the knowledge graph.",
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"RCA endpoint error: {e}")
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

@app.get("/api/quality/deviations")
async def get_quality_deviations():
    """Flag measurable quality deviations from uploaded inspection/maintenance records."""
    try:
        deviations = await asyncio.to_thread(detect_quality_deviations)
        return {
            "deviations_found": len(deviations),
            "deviations": deviations,
            "report_generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Quality deviation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lessons-learned/patterns")
async def get_lessons_learned():
    """Find systemic patterns across incident/near-miss/audit records."""
    try:
        patterns = await asyncio.to_thread(analyze_lessons_learned)
        return {
            "patterns_found": len(patterns),
            "patterns": patterns,
            "report_generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Lessons learned error: {e}")
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
            "rca": "GET /api/maintenance/rca/{equipment_id}",
            "compliance": "GET /api/compliance/gaps",
            "quality_deviations": "GET /api/quality/deviations",
            "lessons_learned": "GET /api/lessons-learned/patterns",
            "health": "GET /api/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
