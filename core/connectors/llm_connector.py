# LLM Connector - Interface para integração com modelos de linguagem
import os
import re
from typing import Dict, Any, List
import openai
from dotenv import load_dotenv
from types import SimpleNamespace
import pymupdf


class LLMConnector:
    """Conector para interface com a API da OpenAI e processamento de PDFs usando unstructured."""
    
    def __init__(self):
        """Inicializa o conector LLM carregando as configurações e cliente OpenAI."""
        load_dotenv()
        self.model_name = "gpt-5-mini"
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def run_extraction(self, pdf_path: str, label: str, schema: Dict[str, str]) -> str:
        """
        Executa a extração de dados do PDF usando o LLM.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            label: Rótulo/nome do documento para contexto
            schema: Dicionário com campos e suas descrições
            
        Returns:
            String JSON com os dados extraídos
        """
        # 1. Obter elementos do PDF
        elements = self._parse_pdf_elements(pdf_path)
        
        # 2. Construir texto estruturado (ordenado)
        structured_text = self._build_structured_text(elements)
        
        # 3. Gerar o prompt
        prompt = self._generate_extraction_prompt(label, schema)
        
        # 4. Combinar prompt e texto
        full_prompt = f"{prompt}\n\nDOCUMENT_TEXT:\n{structured_text}"
        
        # 5. Fazer chamada à API
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": full_prompt}],
            response_format={"type": "json_object"},
            store=False,
            reasoning_effort="minimal"
        )
        
        # 6. Retornar conteúdo da resposta
        result = response.choices[0].message.content

        result_json_str = str(result[result.index('{'):result.rindex('}')+1])

        return result_json_str

    def _parse_pdf_elements(self, pdf_path: str) -> List[Any]:
        """
        Faz o parsing dos elementos do PDF usando PyMuPDF.
        Retorna lista de objetos compatíveis (cada item tem .text, .x, .y).
        x,y correspondem ao canto superior-esquerdo do bbox (PyMuPDF: x0,y0).
        """
        elements: List[Any] = []
        doc = pymupdf.open(pdf_path)
        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_h = float(page.rect.height)
                page_dict = page.get_text("dict")
                for block in page_dict.get("blocks", []):
                    if block.get("type", 1) != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            if not text or not text.strip():
                                continue
                            bbox = span.get("bbox", None)  # [x0, y0, x1, y1], y0 = topo
                            if bbox and len(bbox) >= 4:
                                x0, y0, x1, y1 = bbox
                                x = float(x0)
                                y = float(y0)  # canto superior-esquerdo (origem no topo)
                            else:
                                x = 0.0
                                y = 0.0
                            elements.append(SimpleNamespace(text=text.strip(), x=x, y=y, page_index=page_index))
        finally:
            doc.close()
        return elements


    def _build_structured_text(self, elements: List[Any]) -> str:
        """
        Constrói texto estruturado a partir dos elementos (saída de _parse_pdf_elements),
        ordenando por posição e agrupando por linhas.
        Espera x,y sendo canto superior-esquerdo (y aumenta para baixo).
        """
        elements_data = []

        for elem in elements:
            # extrair texto
            text = None
            x = None
            y = None

            if isinstance(elem, dict):
                text = elem.get("text", None)
                x = elem.get("x", None)
                y = elem.get("y", None)
            else:
                text = getattr(elem, "text", None)
                if hasattr(elem, "x") and hasattr(elem, "y"):
                    x = float(getattr(elem, "x", 0.0))
                    y = float(getattr(elem, "y", 0.0))
                else:
                    metadata = getattr(elem, "metadata", None)
                    if metadata:
                        coordinates = getattr(metadata, "coordinates", None)
                        if coordinates and hasattr(coordinates, "points"):
                            pts = coordinates.points
                            if pts:
                                point = pts[0]
                                if isinstance(point, (tuple, list)) and len(point) >= 2:
                                    # Compatibilidade: se ainda vier bottom-left, tentamos detectar
                                    # Assume formato (x, y)
                                    x, y = float(point[0]), float(point[1])
                                else:
                                    x = float(getattr(point, "x", 0.0) or 0.0)
                                    y = float(getattr(point, "y", 0.0) or 0.0)

            if not text or not str(text).strip():
                continue
            if x is None:
                x = 0.0
            if y is None:
                y = 0.0

            elements_data.append({
                "text": str(text).strip(),
                "x": float(x),
                "y": float(y)
            })

        # ordenar por y (topo -> baixo) depois x (esquerda -> direita)
        elements_data.sort(key=lambda e: (e["y"], e["x"]))

        # agrupar em linhas — tolerância em y (em unidades de coordenada)
        final_lines = []
        current_line = []
        line_ref_y = None
        y_tolerance = 5  # ajuste se necessário

        for elem in elements_data:
            if not all(k in elem for k in ("text", "x", "y")):
                raise ValueError("Elemento inválido: faltando 'text', 'x' ou 'y' chave.")
            if line_ref_y is None:
                current_line.append(elem)
                line_ref_y = elem["y"]
            else:
                if abs(elem["y"] - line_ref_y) <= y_tolerance:
                    current_line.append(elem)
                else:
                    current_line_sorted = sorted(current_line, key=lambda e: e["x"])
                    line_text = " ".join([e["text"] for e in current_line_sorted])
                    final_lines.append(line_text)
                    current_line = [elem]
                    line_ref_y = elem["y"]

        if current_line:
            current_line_sorted = sorted(current_line, key=lambda e: e["x"])
            line_text = " ".join([e["text"] for e in current_line_sorted])
            final_lines.append(line_text)

        return "\n".join(final_lines)
    
    def _generate_extraction_prompt(self, label: str, schema: Dict[str, str]) -> str:
        """
        Gera o prompt para extração de dados.
        
        Args:
            label: Rótulo do documento
            schema: Schema com campos e descrições
            
        Returns:
            Prompt formatado para o LLM
        """
        # Criar lista de campos com descrições
        fields_list = "\n".join([f'"{k}": "{v}"' for k, v in schema.items()])
        
        # Criar template JSON
        json_template = self._create_json_template(schema)
        
        return f"""Extraia os seguintes dados do documento "{label}". O texto está ordenado de cima para baixo, esquerda para direita.

SCHEMA DE EXTRAÇÃO:
{fields_list}

Responda APENAS com um objeto JSON válido, seguindo este formato.
Se alguns dos campos não estiverem presentes no documento, retorne null para eles.

FORMATO JSON:
{json_template}
"""
    
    def _create_json_template(self, schema: Dict[str, str]) -> str:
        """
        Cria template JSON baseado no schema.
        
        Args:
            schema: Dicionário com campos do schema
            
        Returns:
            Template JSON formatado
        """
        fields = ", ".join([f'"{k}": "..."' for k in schema.keys()])
        return f"{{{fields}}}"