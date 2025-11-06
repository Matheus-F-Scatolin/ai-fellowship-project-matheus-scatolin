# Pattern Builder - Construção de padrões de extração
import re
from typing import Dict, Any, List, Optional, Tuple

# Padrões regex comuns para diferentes tipos de campos com pontuações de confiança
COMMON_PATTERNS = {
    'cpf': {'pattern': r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', 'confidence': 1.0},
    'cnpj': {'pattern': r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}', 'confidence': 1.0},
    'email': {'pattern': r'[\w\.-]+@[\w\.-]+\.\w+', 'confidence': 1.0},
    'telefone': {'pattern': r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}', 'confidence': 1.0},
    'cep': {'pattern': r'\d{5}-?\d{3}', 'confidence': 1.0},
    'valor_monetario': {'pattern': r'R\$\s?\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})', 'confidence': 1.0},
    'data': {'pattern': r'\d{2}/\d{2}/\d{4}', 'confidence': 1.0},
    'numero_inscricao': {'pattern': r'\d{5,8}', 'confidence': 1.0},
    'numero': {'pattern': r'\d+', 'confidence': 0.7},
    'texto': {'pattern': r'^[^\d]+$', 'confidence': 0.7},
    'outros': {'pattern': r'.+', 'confidence': 0.7},
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
        Agora suporta regras híbridas combinando regex, contexto e posição.
        
        Args:
            field_name: Nome do campo (ex: 'cpf_cliente', 'numero_inscricao')
            field_value: Valor extraído do campo
            elements: Lista de elementos estruturados do documento
            
        Returns:
            Tupla contendo (rule_type, rule_data, confidence)
        """
        # Verificar se o valor é nulo
        if field_value is None or field_value == "null":
            return ("none", {"reason": "value_is_null"}, 0.9)
        
        # Converter valor para string
        value_str = str(field_value).strip()
        
        # Encontrar o elemento que contém o valor
        value_element = self._find_element_by_text(value_str, elements)
        if not value_element:
            return ("none", {"reason": "value_not_found_in_elements"}, 0.1)
        
        # Coletar todas as regras possíveis
        found_rules = []
        
        regex_rule = self._learn_regex_pattern(field_name, value_str)
        if regex_rule:
            found_rules.append(regex_rule)
            
        context_rule = self._learn_context_pattern(value_str, elements)
        if context_rule:
            found_rules.append(context_rule)
        
        position_rule = self._learn_position_pattern(value_element)
        if position_rule:
            found_rules.append(position_rule)
        
        # Decidir a Regra Final
        # Caso 1: Híbrido (Melhor Caso)
        if len(found_rules) > 1:
            hybrid_confidence = sum(r['confidence'] for r in found_rules) / len(found_rules) + 0.2
            hybrid_confidence = min(hybrid_confidence, 0.99)
            return ("hybrid", {"rules": found_rules}, hybrid_confidence)
        
        # Caso 2: Regra Única
        if len(found_rules) == 1:
            rule = found_rules[0]
            return (rule['type'], rule['data'], rule['confidence'])
        
        # Caso 3: Sem Regras
        return ("none", {"reason": "no_pattern_found"}, 0.1)
    
    def _learn_regex_pattern(self, field_name: str, field_value: str) -> Optional[Dict[str, Any]]:
        """
        Tenta identificar um padrão regex para o campo baseado no nome e valor.
        
        Args:
            field_name: Nome do campo
            field_value: Valor do campo
            
        Returns:
            Dicionário com regra regex ou None se não encontrar
        """
        field_name_lower = field_name.lower()
        
        for pattern_type, data in self.common_patterns.items():
            regex = data['pattern']
            confidence = data['confidence']
            
            # Verificar se o tipo de padrão está no nome do campo OU valor bate com o regex
            if pattern_type in field_name_lower or re.search(regex, field_value):
                rule_data = {"pattern": pattern_type, "regex": regex}
                return {"type": "regex", "data": rule_data, "confidence": confidence}
        
        return None
    
    def _learn_context_pattern(self, field_value: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Tenta identificar um padrão de contexto relativo para o campo.
        
        Args:
            field_value: Valor do campo
            elements: Lista de elementos estruturados
            
        Returns:
            Dicionário com regra de contexto ou None se não encontrar
        """
        # Encontrar o elemento que contém o valor
        value_element = self._find_element_by_text(field_value, elements)
        if not value_element:
            return None
        
        # Tentar encontrar âncora à esquerda (ex: "Nome: SON GOKU")
        anchor_left = self._find_anchor_left(value_element, elements)
        if anchor_left:
            rule_data = {"anchor_text": anchor_left['text'], "direction": "right"}
            return {"type": "relative_context", "data": rule_data, "confidence": 0.8}
        
        # Tentar encontrar âncora acima (ex: "Inscrição\n101943")
        anchor_above = self._find_anchor_above(value_element, elements)
        if anchor_above:
            rule_data = {"anchor_text": anchor_above['text'], "direction": "below"}
            return {"type": "relative_context", "data": rule_data, "confidence": 0.8}
        
        return None
    
    def _learn_position_pattern(self, value_element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Aprende padrão baseado na posição relativa do elemento na página.
        
        Args:
            value_element: Elemento que contém o valor
            
        Returns:
            Dicionário com regra de posição ou None se não conseguir calcular
        """
        x = value_element.get('x')
        y = value_element.get('y')
        # Dimensões padrão da página: 612, 792
        w = value_element.get('page_width', 612)
        h = value_element.get('page_height', 792)
        
        # Verificar se temos todas as informações necessárias
        if any(val is None for val in [x, y, w, h]) or w == 0 or h == 0:
            return None
        
        # Calcular posição relativa
        rel_x = x / w
        rel_y = y / h
        
        rule_data = {"rel_x": rel_x, "rel_y": rel_y, "tolerance": 0.05}
        return {"type": "position", "data": rule_data, "confidence": 0.6}
    
    def _find_element_by_text(self, text: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra um elemento pela correspondência de texto.
        Agora retorna o dicionário do elemento inteiro.
        
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
        A âncora não pode ser um número.
        
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
            # verificar se o texto da âncora não é numérico
            if re.fullmatch(r'\d+', elem['text'].strip()):
                continue
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
        A âncora não pode ser um número.
        
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
            # verificar se o texto da âncora não é numérico
            if re.fullmatch(r'\d+', elem['text'].strip()):
                continue
            # Verificar se está acima (Y menor) e na mesma coluna (tolerância X)
            if (elem['y'] < value_y and 
                abs(elem['x'] - value_x) <= X_TOLERANCE_SAME_COLUMN):
                
                distance = value_y - elem['y']
                if distance < min_distance:
                    min_distance = distance
                    closest_anchor = elem
        
        return closest_anchor