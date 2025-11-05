# LLM Connector - Interface para integração com modelos de linguagem
import os
import re
from typing import Dict, Any, List
import openai
from dotenv import load_dotenv
from unstructured.partition.pdf import partition_pdf


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
        return response.choices[0].message.content
    
    def _parse_pdf_elements(self, pdf_path: str) -> List[Any]:
        """
        Faz o parsing dos elementos do PDF usando unstructured.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Lista de elementos extraídos do PDF
        """
        return partition_pdf(
            filename=pdf_path,
            strategy="fast",
            languages=["por"],
            infer_table_structure=True,
            extract_element_metadata=True
        )
    
    def _build_structured_text(self, elements: List[Any]) -> str:
        """
        Constrói texto estruturado a partir dos elementos, ordenando por posição.
        
        Args:
            elements: Lista de elementos extraídos do PDF
            
        Returns:
            Texto estruturado ordenado
        """
        elements_data = []
        
        # Iterar pelos elementos e extrair dados
        for elem in elements:
            # Filtrar elementos sem texto
            if not elem.text or not elem.text.strip():
                continue
                
            # Extrair coordenadas dos metadados
            x, y = 0, 0
            if hasattr(elem, 'metadata') and elem.metadata:
                coordinates = getattr(elem.metadata, 'coordinates', None)
                if coordinates and hasattr(coordinates, 'points'):
                    # Pegar o primeiro ponto como referência
                    if coordinates.points:
                        point = coordinates.points[0]
                        x = getattr(point, 'x', 0)
                        y = getattr(point, 'y', 0)
            
            elements_data.append({
                'text': elem.text.strip(),
                'x': x,
                'y': y
            })
        
        # Ordenar elementos por posição (y primeiro, depois x)
        elements_data.sort(key=lambda e: (e['y'], e['x']))
        
        # Agrupar em linhas com tolerância para pequenas diferenças em y
        final_lines = []
        current_line = []
        line_ref_y = None
        y_tolerance = 5  # Tolerância em unidades de coordenada
        
        for elem in elements_data:
            if not all(k in elem for k in ('text', 'x', 'y')):
                raise ValueError("Elemento inválido: faltando 'text', 'x' ou 'y' chave.")
            if line_ref_y is None:
                # inicia primeira linha
                current_line.append(elem)
                line_ref_y = elem['y']
            else:
                # compara com o y do primeiro elemento da linha atual
                if abs(elem['y'] - line_ref_y) <= y_tolerance:
                    current_line.append(elem)
                else:
                    # Finalizar linha atual e começar nova
                    current_line_sorted = sorted(current_line, key=lambda elem: elem['x'])
                    line_text = " ".join([e['text'] for e in current_line_sorted])
                    final_lines.append(line_text)
                    # Começar nova linha
                    current_line = [elem]
                    line_ref_y = elem['y']

        # Adicionar última linha
        if current_line:
            current_line_sorted = sorted(current_line, key=lambda elem: elem['x'])
            line_text = " ".join([e['text'] for e in current_line_sorted])
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