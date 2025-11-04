from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import time
import uvicorn
from typing import Dict, Any


# Pydantic Models
class ExtractionResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str


# Mock Pipeline (Singleton)
class ExtractionPipeline:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExtractionPipeline, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.stats = {"start_time": time.time()}
            self.initialized = True
    
    def extract(self, pdf_bytes: bytes, label: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """Mock extraction method - retorna dados simulados"""
        return {
            "field_1": "mock_data_1",
            "field_2": 123,
            "_pipeline": {
                "method": "mock",
                "time": 0.01
            }
        }


# Global pipeline instance
pipeline = ExtractionPipeline()


# Lifespan event handler (nova abordagem do FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("--- API Iniciada (Versão Customizada) ---")
    yield
    # Shutdown
    print("--- API Encerrada ---")


# FastAPI App Instance
app = FastAPI(
    title="PDF Data Extraction API",
    description="API para extração de dados de PDFs com aprendizado de template e cache.",
    version="1.0-custom",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints
@app.get("/")
async def root():
    """Root endpoint com informações da API"""
    return {
        "name": "PDF Data Extraction API",
        "version": "1.0-custom",
        "description": "API para extração de dados de PDFs com aprendizado de template e cache.",
        "docs": "/docs",
        "status": "running"
    }


@app.post("/extract", response_model=ExtractionResponse)
async def run_extraction(
    file: UploadFile = File(...),
    label: str = Form(...),
    extraction_schema: str = Form(...)
):
    """Endpoint principal para extração de dados de PDFs"""
    start_time = time.time()
    
    try:
        # Ler bytes do PDF
        pdf_bytes = await file.read()
        
        # Validar schema JSON
        try:
            schema_dict = json.loads(extraction_schema)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="extraction_schema deve ser um JSON válido"
            )
        
        # Chamar pipeline
        result = pipeline.extract(pdf_bytes, label, schema_dict)
        
        # Separar dados do metadata
        data = {k: v for k, v in result.items() if not k.startswith('_')}
        pipeline_metadata = {k: v for k, v in result.items() if k.startswith('_')}
        
        # Construir metadata final
        total_time = time.time() - start_time
        metadata = {
            "request_time": total_time,
            "file_name": file.filename,
            "file_size": len(pdf_bytes),
            "label": label,
            "schema_fields": list(schema_dict.keys()),
            **pipeline_metadata
        }
        
        return ExtractionResponse(
            success=True,
            data=data,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno na extração: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0-custom"
    )


@app.get("/stats")
async def get_stats():
    """Endpoint de estatísticas (não implementado ainda)"""
    return {"message": "stats_not_implemented_yet"}


# Runner
if __name__ == "__main__":
    uvicorn.run(
        "core.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )