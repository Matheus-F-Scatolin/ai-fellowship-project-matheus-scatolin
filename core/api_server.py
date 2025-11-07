from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import tempfile
import os
import json
import time
import uvicorn
from typing import Dict, Any, List
from core.store.caching import CacheManager
from core.store.key_gen import CacheKeyBuilder
from core.connectors.llm_connector import LLMConnector
from core.learning.template_orchestrator import TemplateOrchestrator
import pymupdf

# Constantes de fallback de página
PAGE_WIDTH_FALLBACK = 612
PAGE_HEIGHT_FALLBACK = 792


# Pydantic Models
class ExtractionResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str


# Pipeline Completa (Singleton)
class ExtractionPipeline:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 1. Inicializar todos os componentes
        self.cache = CacheManager()
        self.llm = LLMConnector()
        self.template = TemplateOrchestrator()
        
        self.stats = {
            "total_requests": 0,
            "cache_hits_l1_l2": 0,
            "cache_hits_l3": 0,
            "template_hits": 0,
            "llm_calls_full": 0,
            "llm_calls_fallback": 0,
            "start_time": time.time()
        }
        self._initialized = True


    def _get_rich_elements(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai elementos com texto, coordenadas (x,y = canto superior-esquerdo do bbox)
        e dimensões da página usando PyMuPDF.
        """
        rich_elements: List[Dict[str, Any]] = []
        doc = pymupdf.open(pdf_path)

        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_rect = page.rect
                page_w = page_rect.width if page_rect.width else PAGE_WIDTH_FALLBACK
                page_h = page_rect.height if page_rect.height else PAGE_HEIGHT_FALLBACK

                # Usamos a saída "dict" para obter spans (texto com bbox preciso)
                page_dict = page.get_text("dict")
                for block in page_dict.get("blocks", []):
                    # block["type"] == 0 -> texto; outros tipos são imagens/linhas
                    if block.get("type", 1) != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            # bbox = [x0, y0, x1, y1]
                            bbox = span.get("bbox")
                            if bbox and len(bbox) >= 4:
                                x0, y0, x1, y1 = bbox
                                x, y = float(x0), float(y0)  # canto superior-esquerdo
                            else:
                                x, y = 0.0, 0.0

                            rich_elements.append({
                                "text": text,
                                "x": x,
                                "y": y,
                                "page_width": float(page_w),
                                "page_height": float(page_h),
                                "page_index": page_index  # 0-based; remova se não quiser
                            })
        finally:
            doc.close()
        return rich_elements

    def extract(
        self,
        pdf_bytes: bytes,
        label: str,
        schema: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Executa a pipeline de extração completa:
        L1/L2 -> L3 -> L4 (Template) -> LLM (Fallback)
        """
        self.stats["total_requests"] += 1
        pipeline_metadata = {"method": "unknown", "steps": []}
        
        # --- Etapa 1: Cache L1/L2 (Hit Completo) e L3 (Parcial) ---
        cached_result = self.cache.get(pdf_bytes, label, schema)
        
        if cached_result:
            cache_info = cached_result.get('_cache_info', {})
            source = cache_info.get('source')
            
            # Hit L1 ou L2 (completo)
            if source in ['L1_MEMORY', 'L2_DISK']:
                self.stats["cache_hits_l1_l2"] += 1
                pipeline_metadata["method"] = "cache-l2"
                cached_result["_pipeline"] = pipeline_metadata
                cached_result["metadata"]["method"] = "cache-l2"
                if "data" in cached_result and isinstance(cached_result["data"], dict):
                    return cached_result["data"]
                return cached_result
            
            # Hit L3 (Parcial)
            if source == 'L3_PARTIAL':
                self.stats["cache_hits_l3"] += 1
                pipeline_metadata["steps"].append("cache-l3")
                # Prepara para o fallback
                final_data = cached_result['data']
                schema_to_extract = {
                    k: v for k, v in schema.items() 
                    if final_data.get(k) is None
                }
            else:
                # Cache miss
                final_data = {}
                schema_to_extract = schema.copy()
        else:
            final_data = {}
            schema_to_extract = schema.copy()

        # --- Salva PDF em arquivo temporário para análise ---
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            # Carrega elementos apenas uma vez
            rich_elements = self._get_rich_elements(tmp_path)
            
            # --- Etapa 2: Template (L4) ---
            if schema_to_extract: # Só roda se algo estiver faltando
                template_result = self.template.check_and_use_template(label, rich_elements)
                
                if template_result:
                    pipeline_metadata["steps"].append("template")
                    self.stats["template_hits"] += 1
                    
                    # Processa o resultado do template
                    temp_schema_to_extract = {}
                    for field_name, value in schema_to_extract.items():
                        template_value = template_result.get(field_name)
                        if template_value is not None:
                            final_data[field_name] = template_value
                        else:
                            # Campo falhou no template, precisa de LLM
                            temp_schema_to_extract[field_name] = value
                    schema_to_extract = temp_schema_to_extract
                
            # --- Etapa 3: LLM (Fallback ou Completo) ---
            if schema_to_extract:
                if not pipeline_metadata["steps"]:
                    # LLM foi o primeiro método
                    pipeline_metadata["steps"].append("llm-full")
                    self.stats["llm_calls_full"] += 1
                else:
                    # LLM foi usado como fallback
                    pipeline_metadata["steps"].append("llm-fallback")
                    self.stats["llm_calls_fallback"] += 1
                    
                llm_result_json = self.llm.run_extraction(tmp_path, label, schema_to_extract)
                try:
                    llm_data = json.loads(llm_result_json)
                except json.JSONDecodeError:
                    llm_data = {}
                
                # Atualiza o resultado final
                final_data.update(llm_data)
                
                # Aprende com o resultado do LLM (apenas os campos que o LLM extraiu)
                self.template.learn_from_llm_result(
                    label, schema_to_extract, llm_data, rich_elements
                )
            
            # --- Finalização ---
            pipeline_metadata["method"] = "->".join(pipeline_metadata["steps"])
            
            # Salva o resultado *completo* no cache
            self.cache.set(pdf_bytes, label, schema, final_data, pipeline_metadata)
            
            final_data["_pipeline"] = pipeline_metadata
            return final_data

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


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
    status = "healthy"
    try:
        # Tenta acessar componentes
        _ = pipeline.cache.l2_disk_cache.stats()
        _ = pipeline.template.db._get_connection()
        _ = pipeline.llm.client
    except Exception:
        status = "degraded"
    
    return HealthResponse(status=status, version="1.0-custom")


@app.get("/stats")
async def get_stats():
    """Endpoint de estatísticas"""
    try:
        pipeline_stats = pipeline.stats
        cache_stats = pipeline.cache.get_stats()
        template_stats = pipeline.template.get_template_stats()
        
        combined_stats = {
            "pipeline": pipeline_stats,
            "cache": cache_stats,
            "templates": template_stats
        }
        return JSONResponse(content=combined_stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


# Runner
if __name__ == "__main__":
    uvicorn.run(
        "core.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )