from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any

app = FastAPI(title="Document Portal API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")

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

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)) -> Any:
    try:
        pass
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Failed: {e}")
                        
@app.post("/compare")
async def compare_documents(reference: UploadFile = File(...), 
                            actual: UploadFile = File(...)) -> Any:
    try:
        pass
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison Failed: {e}")
    
@app.post("/chat/index")
async def chat_build_index() -> Any:
    try:
        pass
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing Failed: {e}")
    
@app.post("/chat/query")
async def chat_query() -> Any:
    try:
        pass
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query Failed: {e}")
    
#uvicorn main:app --reload (from within api)