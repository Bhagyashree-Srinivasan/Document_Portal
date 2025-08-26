from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional, List
import os
from pathlib import Path

from src.DocIngestion.data_ingestion import (
    DocHandler,
    DocumentComparator,
    ChatIngestor, 
    FaissManager
)
from src.DocAnalyzer.data_analysis import DocumentAnalyzer
from src.DocComparison.document_comparer import DocumentComparer
from src.DocChat.retrieval import ConversationRAG
from utils.file_io import save_uploaded_files

UPLOAD_BASE = os.getenv("UPLOAD_BASE", "data")
FAISS_BASE = os.getenv("FAISS_BASE", "faiss_index")

app = FastAPI(title="Document Portal API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory = Path(__file__).parent.parent / "static"), name="static")
templates = Jinja2Templates(directory= Path(__file__).parent.parent / "templates")

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    #will render templates/index.html
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/health")
def health() -> Dict[str, str]:
    """
    Health check endpoint
    """
    return {"status": "ok", "service": "Document Portal"}

class FastAPIFileAdapter:
    """
    Adapter to convert FastAPI UploadFile to a standard file-like object.
    """
    def __init__(self, upload_file: UploadFile):
        self._upload_file = upload_file
        self.name = upload_file.filename

    def getbuffer(self) -> bytes:
        self._upload_file.file.seek(0)
        return self._upload_file.file.read()
    
def _read_pdf_via_handler(handler: DocHandler, path: str) -> str:
    """
    Helper function to read PDF content via DocHandler.
    """
    if hasattr(handler, "read_pdf"):
        return handler.read_pdf(path)
    if hasattr(handler, "read_"):
        return handler.read_(path)
    raise RuntimeError("DocHandler has neither read_pdf nor read_ method.")

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)) -> Any:
    try:
        dh = DocHandler()
        saved_path = dh.save_pdf(FastAPIFileAdapter(file))
        text = _read_pdf_via_handler(dh, saved_path)

        analyzer = DocumentAnalyzer()
        result = analyzer.analyze_metadata(text)
        return JSONResponse(content=result)
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Failed: {e}")
                        
@app.post("/compare")
async def compare_documents(reference: UploadFile = File(...), 
                            actual: UploadFile = File(...)) -> Any:
    try:
        dc = DocumentComparator()
        ref_path, act_path = dc.save_uploaded_files(FastAPIFileAdapter(reference), FastAPIFileAdapter(actual))
        _ = ref_path, act_path
        combined_text = dc.combine_documents()
        comp = DocumentComparer()
        df = comp.compare_documents(combined_text)
        return {"rows": df.to_dict(orient="records"), "session_id": dc.session_id}
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison Failed: {e}")
    
@app.post("/chat/index")
async def chat_build_index(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    use_session_dirs: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    k: int = Form(5),
) -> Any:
    try:
        wrapped = [FastAPIFileAdapter(file) for file in files]
        ci = ChatIngestor(
            temp_base = UPLOAD_BASE,
            faiss_base = FAISS_BASE,
            use_session_dirs = use_session_dirs,
            session_id = session_id or None,
        )
        ci.build_retriever(wrapped, chunk_size=chunk_size, chunk_overlap=chunk_overlap, k=k)
        return {"session_id": ci.session_id, "k": k, "use_session_dirs": use_session_dirs}
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing Failed: {e}")
    
@app.post("/chat/query")
async def chat_query(
    question: str = Form(...),
    session_id: Optional[str] = Form(None),
    use_session_dirs: bool = Form(True),
    k: int = Form(5),
) -> Any:
    try:
        if use_session_dirs and not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required when using session directories.")
        
        #Prepare FAISS index path
        index_dir = os.path.join(FAISS_BASE, session_id) if use_session_dirs else FAISS_BASE
        if not os.path.isdir(index_dir):
            raise HTTPException(status_code=404, detail=f"Index path {index_dir} does not exist.")
        
        #Initialize LCEL-style RAG pipeline
        rag = ConversationRAG(
            session_id = session_id
        )
        rag.load_retriever_from_faiss(index_dir)

        #Optional: for now we pass empty chat history
        response = rag.invoke(
            user_input=question,
            chat_history=[]
        )
        return {
            "answer": response,
            "session_id": rag.session_id,
            "k": k,
            "engine": "LCEL-RAG"
        }
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query Failed: {e}")
    
#uvicorn main:app --reload (from within api)