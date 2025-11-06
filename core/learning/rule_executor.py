# Rule Executor - Execução de regras de extração
# Implementa algoritmo sofisticado de pontuação de candidatos híbridos

import re
import json
import math
from typing import Dict, Any, List, Optional

# Fallbacks para dimensões da página
PAGE_WIDTH_FALLBACK = 612
PAGE_HEIGHT_FALLBACK = 792

# Tipos de padrões regex considerados "fortes" (para a Etapa 3)
STRONG_REGEX_PATTERNS = {'cpf', 'cnpj', 'email', 'telefone', 'cep'}

# Limite de tolerância para a regra de posição
POSITION_TOLERANCE = 0.05

# Pontuação para cada regra bem-sucedida
POSITION_SCORE = 0.9
CONTEXT_SCORE = 0.9
STRONG_REGEX_SCORE = 1.0

# Tolerâncias de busca de contexto (para encontrar âncoras)
Y_TOLERANCE_SAME_LINE = 10
X_TOLERANCE_SAME_COLUMN = 20


class RuleExecutor:
    """
    Executor de regras híbridas com algoritmo de pontuação de candidatos.
    Combina position, relative_context e regex para encontrar o melhor candidato.
    """
    
    def __init__(self):
        """Inicializa o executor com as constantes necessárias."""
        self.strong_patterns = STRONG_REGEX_PATTERNS
        self.pos_tolerance = POSITION_TOLERANCE
        self.pos_score = POSITION_SCORE
        self.context_score = CONTEXT_SCORE
        self.strong_regex_score = STRONG_REGEX_SCORE
        self.y_tolerance = Y_TOLERANCE_SAME_LINE
        self.x_tolerance = X_TOLERANCE_SAME_COLUMN
    
    def execute_all_rules(self, rules: List[Dict[str, Any]], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Método público principal para executar todas as regras.
        
        Args:
            rules: Lista de regras extraídas do banco de dados
            elements: Lista de elementos extraídos do PDF
            
        Returns:
            Dict com os dados extraídos {field_name: value}
        """
        # Pré-processamento dos elementos para adicionar coordenadas relativas
        processed_elements = self._preprocess_elements(elements)
        
        # Inicializar resultado
        extracted_data: Dict[str, Any] = {}
        
        # Processar cada regra
        for rule in rules:
            field_name = rule['field_name']
            rule_type = rule['rule_type']
            rule_data = json.loads(rule['rule_data'])
            
            value: Optional[str] = None
            
            if rule_type == 'hybrid':
                value = self._find_best_candidate(rule_data['rules'], processed_elements)
            elif rule_type == 'none':
                value = None
            
            extracted_data[field_name] = value
        
        return extracted_data
    
    def _find_best_candidate(self, rules: List[Dict[str, Any]], elements: List[Dict[str, Any]]) -> Optional[str]:
        """
        Algoritmo principal de 4 etapas para encontrar o melhor candidato.
        
        Args:
            rules: Lista de sub-regras (position, relative_context, regex)
            elements: Lista de elementos processados do PDF
            
        Returns:
            Texto do melhor candidato ou None se não encontrado
        """
        # Etapa 1: Parse das Regras
        pos_rule = next((r['data'] for r in rules if r['type'] == 'position'), None)
        ctx_rule = next((r['data'] for r in rules if r['type'] == 'relative_context'), None)
        rgx_rule = next((r['data'] for r in rules if r['type'] == 'regex'), None)
        
        if not rgx_rule:  # Regra regex é obrigatória
            return None
        
        # Etapa 2: Inicializar Candidatos
        candidates: Dict[int, Dict[str, Any]] = {}
        for i, elem in enumerate(elements):
            candidates[i] = {
                'element': elem,
                'score': 0.0,
                'distance': float('inf')
            }
        
        # Etapa 3: Pontuar por Posição
        if pos_rule:
            target_x, target_y = pos_rule['rel_x'], pos_rule['rel_y']
            for i, elem in enumerate(elements):
                dist = self._calculate_distance(elem['rel_x'], elem['rel_y'], target_x, target_y)
                candidates[i]['distance'] = dist
                if dist <= self.pos_tolerance:
                    candidates[i]['score'] += self.pos_score
        
        # Etapa 4: Pontuar por Contexto
        if ctx_rule:
            anchor_elem = self._find_element_by_text(ctx_rule['anchor_text'], elements)
            if anchor_elem:
                target_elem = self._find_element_by_direction(anchor_elem, ctx_rule['direction'], elements)
                if target_elem:
                    # Encontrar o índice do target_elem
                    target_idx = None
                    for i, elem in enumerate(elements):
                        if elem is target_elem:
                            target_idx = i
                            break
                    
                    if target_idx is not None:
                        candidates[target_idx]['score'] += self.context_score
        
        # Etapa 5: Pontuar por Regex Forte (Scan)
        if rgx_rule['pattern'] in self.strong_patterns:
            regex = rgx_rule['regex']
            for i, elem in enumerate(elements):
                if re.search(regex, elem['text']):
                    candidates[i]['score'] += self.strong_regex_score
        
        # Etapa 6: Filtrar e Selecionar
        final_regex = rgx_rule['regex']
        filtered_candidates = []
        
        for cand in candidates.values():
            # Filtro Mandatório: regex match E score > 0
            if re.search(final_regex, cand['element']['text']) and cand['score'] > 0:
                filtered_candidates.append(cand)
        
        if not filtered_candidates:
            return None
        
        # Seleção: ordenar por score (desc), depois distância (asc)
        filtered_candidates.sort(key=lambda c: (-c['score'], c['distance']))
        best_candidate = filtered_candidates[0]
        
        return best_candidate['element']['text']
    
    def _preprocess_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pré-processa elementos para adicionar coordenadas relativas.
        
        Args:
            elements: Lista original de elementos
            
        Returns:
            Nova lista com elementos processados incluindo rel_x e rel_y
        """
        processed_elements = []
        
        for elem in elements:
            w = elem.get('page_width', PAGE_WIDTH_FALLBACK)
            h = elem.get('page_height', PAGE_HEIGHT_FALLBACK)
            
            new_elem = elem.copy()
            new_elem['rel_x'] = elem.get('x', 0) / w
            new_elem['rel_y'] = elem.get('y', 0) / h
            
            processed_elements.append(new_elem)
        
        return processed_elements
    
    def _calculate_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calcula distância euclidiana entre dois pontos.
        
        Args:
            x1, y1: Coordenadas do primeiro ponto
            x2, y2: Coordenadas do segundo ponto
            
        Returns:
            Distância euclidiana
        """
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def _find_element_by_text(self, text: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra elemento âncora por texto.
        
        Args:
            text: Texto a ser procurado
            elements: Lista de elementos
            
        Returns:
            Elemento encontrado ou None
        """
        # Busca por texto exato primeiro
        for elem in elements:
            if elem['text'].strip() == text.strip():
                return elem
        
        # Busca por texto parcial se não encontrou exato
        for elem in elements:
            if text.lower().strip() in elem['text'].lower().strip():
                return elem
        
        return None
    
    def _find_element_by_direction(self, anchor_elem: Dict[str, Any], direction: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra elemento em uma direção específica a partir da âncora.
        
        Args:
            anchor_elem: Elemento âncora
            direction: Direção ('right' ou 'below')
            elements: Lista de elementos
            
        Returns:
            Elemento encontrado na direção especificada ou None
        """
        if direction == 'right':
            return self._find_element_to_right(anchor_elem, elements)
        elif direction == 'below':
            return self._find_element_below(anchor_elem, elements)
        
        return None
    
    def _find_element_to_right(self, anchor_elem: Dict[str, Any], elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra elemento à direita da âncora (mesma linha).
        
        Args:
            anchor_elem: Elemento âncora
            elements: Lista de elementos
            
        Returns:
            Elemento à direita ou None
        """
        anchor_x = anchor_elem.get('x', 0)
        anchor_y = anchor_elem.get('y', 0)
        
        candidates = []
        
        for elem in elements:
            elem_x = elem.get('x', 0)
            elem_y = elem.get('y', 0)
            
            # Verifica se está na mesma linha (tolerância Y) e à direita
            if (elem_x > anchor_x and 
                abs(elem_y - anchor_y) <= self.y_tolerance):
                
                distance = elem_x - anchor_x
                candidates.append((elem, distance))
        
        if candidates:
            # Retorna o elemento mais próximo à direita
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
        
        return None
    
    def _find_element_below(self, anchor_elem: Dict[str, Any], elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Encontra elemento abaixo da âncora (mesma coluna).
        
        Args:
            anchor_elem: Elemento âncora
            elements: Lista de elementos
            
        Returns:
            Elemento abaixo ou None
        """
        anchor_x = anchor_elem.get('x', 0)
        anchor_y = anchor_elem.get('y', 0)
        
        candidates = []
        
        for elem in elements:
            elem_x = elem.get('x', 0)
            elem_y = elem.get('y', 0)
            
            # Verifica se está na mesma coluna (tolerância X) e abaixo
            if (elem_y > anchor_y and 
                abs(elem_x - anchor_x) <= self.x_tolerance):
                
                distance = elem_y - anchor_y
                candidates.append((elem, distance))
        
        if candidates:
            # Retorna o elemento mais próximo abaixo
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
        
        return None