# Struct Matcher - Correspondência de estruturas em documentos
import re
from typing import Dict, Any, List, Set, Tuple
import unicodedata

# Threshold de similaridade para considerar um match
JACCARD_MATCH_THRESHOLD = 0.8

# Conjunto de rótulos/palavras-chave conhecidos para ajudar na identificação
KNOWN_LABELS = {
    'nome', 'inscricao', 'seccional', 'subsecao', 'categoria', 
    'endereço', 'telefone', 'situacao', 'data', 'sistema', 'produto',
    'valor', 'quantidade', 'tipo', 'cidade', 'referencia', 'cpf',
    'cnpj', 'cep', 'email', 'hora', 'total','sobrenome', 'logradouro',
    'complemento', 'bairro', 'estado', 'pais', 'cidade', 'uf',
    'subtotal', 'descontos', 'emissao', 'vencimento', 'pagamento',
    'banco', 'agencia', 'conta', 'favorecido', 'documento',
    'numero do documento', 'endereco de entrega', 'forma de pagamento',
    'data de nascimento', 'estado civil', 'nacionalidade',
    'profissao', 'rg', 'orgao emissor', 'uf', 'titulo de eleitor',
    'zona', 'secao', 'carteira de trabalho', 'serie', 'pis', 'pasep',
    'salario', 'cargo', 'admissao', 'demissao', 'motivo da demissao',
    'ctps', 'ctps serie', 'ctps uf', 'ctps data de emissao'
}

class StructuralMatcher:
    """
    Classe responsável por extrair assinaturas estruturais de documentos
    e comparar similaridade usando o índice Jaccard.
    """
    
    def __init__(self):
        """Inicializa o matcher com configurações padrão."""
        self.known_labels = KNOWN_LABELS
        self.match_threshold = JACCARD_MATCH_THRESHOLD
    
    def check_similarity(self, new_pdf_elements, template_signature_list: List[str]) -> Tuple[bool, float]:
        """
        Compara duas assinaturas usando similaridade Jaccard.
        
        Args:
            new_pdf_elements: Conjunto de elentos extraídos do novo documento
            template_signature_list: Lista de rótulos do template salvo no banco
            
        Returns:
            Tupla com (is_match, similarity_score)
        """
        # Converte a assinatura do banco (lista) em conjunto
        template_signature_set = set(template_signature_list)

        new_signature = self.extract_signature(new_pdf_elements)
        
        # Calcula a similaridade Jaccard
        similarity_score = self._calculate_jaccard_similarity(new_signature, template_signature_set)
        
        # Verifica se é um match baseado no threshold
        is_match = similarity_score >= self.match_threshold
        
        return (is_match, similarity_score)
    
    def extract_signature(self, elements: List[Dict[str, Any]]) -> Set[str]:
        """
        Extrai a assinatura estrutural de uma lista de elementos do unstructured.
        Itera sobre os KNOWN_LABELS e testa se eles aparecem nos textos dos elementos.
        
        Args:
            elements: Lista de elementos extraídos pelo unstructured
            
        Returns:
            Conjunto de rótulos que compõem a assinatura estrutural
        """
        pdf_text = self._build_structured_text(elements)
        pdf_normalized_text = self._normalize_text(pdf_text)
        signature = set()
        for label in self.known_labels:
            if label in pdf_normalized_text:
                signature.add(label)

        return signature

    
    def _calculate_jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        Calcula a similaridade Jaccard entre dois conjuntos.
        
        Args:
            set1: Primeiro conjunto
            set2: Segundo conjunto
            
        Returns:
            Índice Jaccard (0.0 a 1.0)
        """
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto para comparação.
        
        Args:
            text: Texto a ser normalizado
            
        Returns:
            Texto normalizado
        """
        # Converte para minúsculas
        text = text.lower()

        # Remove acentuação, çedilhas e outros diacríticos

        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Remove pontuação comum de rótulos (como dois-pontos no final)
        text = re.sub(r'[:]$', '', text).strip()
        
        return text
    
    def _build_structured_text(self, elements: List[Dict[str, Any]]) -> str:
        """
        Constrói um texto estruturado a partir dos elementos do unstructured.
        
        Args:
            elements: Lista de elementos extraídos pelo unstructured
            
        Returns:
            Texto estruturado
        """
        # Ordenar elementos por posição (y primeiro, depois x)
        elements.sort(key=lambda e: (e['y'], e['x']))
        
        # Agrupar em linhas com tolerância para pequenas diferenças em y
        final_lines = []
        current_line = []
        line_ref_y = None
        y_tolerance = 5  # Tolerância em unidades de coordenada
        
        for elem in elements:
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
