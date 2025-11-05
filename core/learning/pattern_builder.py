# Pattern Builder - Construção de padrões de extração
import re
from typing import Dict, Any, List, Optional, Tuple

# Padrões regex comuns para diferentes tipos de campos
COMMON_PATTERNS = {
    'cpf': r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}',
    'cnpj': r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}',
    'telefone': r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}',
    'cep': r'\d{5}-?\d{3}',
    'email': r'[\w\.-]+@[\w\.-]+\.\w+',
    'data': r'\d{1,2}/\d{1,2}/\d{4}',
    'hora': r'\d{1,2}:\d{2}',
    'valor_monetario': r'R\$\s?\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})',
    'numero_inscricao': r'\d{5,8}',
    'numero': r'\d+',
}

# Tolerâncias para encontrar âncoras de contexto
Y_TOLERANCE_SAME_LINE = 10
X_TOLERANCE_SAME_COLUMN = 20


class PatternBuilder:
    """
    Classe responsável por aprender padrões de extração a partir de exemplos de sucesso.
    Suporta dois tipos de padrões:
    1. Regex - para campos com formatos específicos (CPF, CNPJ, etc.)
    2. Contexto Relativo - para campos que dependem de âncoras posicionais
    """
    
    def __init__(self):
        """Inicializa o construtor de padrões."""
        self.common_patterns = COMMON_PATTERNS
    
    def learn_rule_for_field(self, field_name: str, field_value: Any, elements: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], float]:
        """
        Método principal para aprender uma regra de extração para um campo específico.
        
        Args:
            field_name: Nome do campo (ex: 'cpf_cliente', 'numero_inscricao')
            field_value: Valor extraído do campo
            elements: Lista de elementos estruturados do documento
            
        Returns:
            Tupla contendo (rule_type, rule_data, confidence)
        """
        # Verificar se o valor é nulo
        if field_value is None or str(field_value).strip().lower() == "null":
            return ("none", {"reason": "value_is_null"}, 0.9)
        
        # Converter valor para string
        value_str = str(field_value).strip()
        
        # Tentar padrão regex (prioridade alta)
        regex_data = self._learn_regex_pattern(field_name, value_str)
        if regex_data:
            return ("regex", regex_data, 0.95)
        
        # Tentar padrão de contexto relativo (prioridade média)
        context_data = self._learn_context_pattern(value_str, elements)
        if context_data:
            return ("relative_context", context_data, 0.85)
        
        # Fallback - nenhum padrão encontrado
        return ("none", {"reason": "no_pattern_found"}, 0.1)
    
    def _learn_regex_pattern(self, field_name: str, field_value: str) -> Optional[Dict[str, Any]]:
        """
        Tenta identificar um padrão regex para o campo baseado no nome e valor.
        
        Args:
            field_name: Nome do campo
            field_value: Valor do campo
            
        Returns:
            Dicionário com padrão regex ou None se não encontrar
        """
        field_name_lower = field_name.lower()
        
        for pattern_type, regex in self.common_patterns.items():
            # Verificar se o tipo de padrão está no nome do campo
            if pattern_type in field_name_lower:
                # Validar se o valor de fato bate com o regex
                if re.search(regex, field_value):
                    return {
                        "pattern": regex,
                        "type": pattern_type
                    }
        
        return None
    
    def _learn_context_pattern(self, field_value: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Tenta identificar um padrão de contexto relativo para o campo.
        
        Args:
            field_value: Valor do campo
            elements: Lista de elementos estruturados
            
        Returns:
            Dicionário com dados do contexto ou None se não encontrar
        """
        # Encontrar o elemento que contém o valor
        value_element = self._find_element_by_text(field_value, elements)
        if not value_element:
            return None
        
        # Tentar encontrar âncora à esquerda (ex: "Nome: SON GOKU")
        anchor_left = self._find_anchor_left(value_element, elements)
        if anchor_left:
            return {
                "anchor_text": anchor_left['text'],
                "direction": "right"
            }
        
        # Tentar encontrar âncora acima (ex: "Inscrição\n101943")
        anchor_above = self._find_anchor_above(value_element, elements)
        if anchor_above:
            return {
                "anchor_text": anchor_above['text'],
                "direction": "below"
            }
        
        return None
    
    def _find_element_by_text(self, text: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra um elemento pela correspondência de texto.
        
        Args:
            text: Texto a procurar
            elements: Lista de elementos
            
        Returns:
            Elemento encontrado ou None
        """
        # Preferência para correspondência exata
        for elem in elements:
            if elem.get('text') == text:
                return elem
        
        # Fallback para correspondência parcial
        for elem in elements:
            if text in elem.get('text', ''):
                return elem
        
        return None
    
    def _find_anchor_left(self, value_element: Dict[str, Any], elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra uma âncora à esquerda do elemento de valor (mesma linha).
        
        Args:
            value_element: Elemento que contém o valor
            elements: Lista de todos os elementos
            
        Returns:
            Elemento âncora mais próximo à esquerda ou None
        """
        value_y = value_element['y']
        value_x = value_element['x']
        
        closest_anchor = None
        min_distance = float('inf')
        
        for elem in elements:
            # Verificar se está na mesma linha (tolerância Y) e à esquerda
            if (abs(elem['y'] - value_y) <= Y_TOLERANCE_SAME_LINE and 
                elem['x'] < value_x):
                
                distance = value_x - elem['x']
                if distance < min_distance:
                    min_distance = distance
                    closest_anchor = elem
        
        return closest_anchor
    
    def _find_anchor_above(self, value_element: Dict[str, Any], elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra uma âncora acima do elemento de valor (mesma coluna).
        
        Args:
            value_element: Elemento que contém o valor
            elements: Lista de todos os elementos
            
        Returns:
            Elemento âncora mais próximo acima ou None
        """
        value_y = value_element['y']
        value_x = value_element['x']
        
        closest_anchor = None
        min_distance = float('inf')
        
        for elem in elements:
            # Verificar se está acima (Y menor) e na mesma coluna (tolerância X)
            if (elem['y'] < value_y and 
                abs(elem['x'] - value_x) <= X_TOLERANCE_SAME_COLUMN):
                
                distance = value_y - elem['y']
                if distance < min_distance:
                    min_distance = distance
                    closest_anchor = elem
        
        return closest_anchor