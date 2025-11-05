# Struct Matcher - Correspondência de estruturas em documentos
import re
from typing import Dict, Any, List, Set, Tuple
import unicodedata

# Threshold de similaridade para considerar um match
JACCARD_MATCH_THRESHOLD = 0.80

# Conjunto de rótulos/palavras-chave conhecidos para ajudar na identificação
KNOWN_LABELS = {
    'nome', 'inscricao', 'seccional', 'subsecao', 'categoria', 
    'endereço', 'telefone', 'situacao', 'data', 'sistema', 'produto',
    'valor', 'quantidade', 'tipo', 'cidade', 'referencia', 'cpf',
    'cnpj', 'cep', 'email', 'data', 'hora', 'valor', 'total',
    'subtotal', 'descontos', 'emissao', 'vencimento', 'pagamento',
    'banco', 'agencia', 'conta', 'favorecido', 'documento',
    'numero do documento', 'endereco de entrega', 'forma de pagamento'
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
    
    def check_similarity(self, new_signature: Set[str], template_signature_list: List[str]) -> Tuple[bool, float]:
        """
        Compara duas assinaturas usando similaridade Jaccard.
        
        Args:
            new_signature: Conjunto de rótulos extraídos do novo documento
            template_signature_list: Lista de rótulos do template salvo no banco
            
        Returns:
            Tupla com (is_match, similarity_score)
        """
        # Converte a assinatura do banco (lista) em conjunto
        template_signature_set = set(template_signature_list)
        
        # Calcula a similaridade Jaccard
        similarity_score = self._calculate_jaccard_similarity(new_signature, template_signature_set)
        
        # Verifica se é um match baseado no threshold
        is_match = similarity_score >= self.match_threshold
        
        return (is_match, similarity_score)
    
    def extract_signature(self, elements: List[Dict[str, Any]]) -> Set[str]:
        """
        Extrai a assinatura estrutural de uma lista de elementos do unstructured.
        
        Esta versão é mais criteriosa e só adiciona no máximo UMA nova assinatura
        que não esteja em self.known_labels. A estratégia é:
        - Manter adição imediata de rótulos conhecidos e títulos.
        - Coletar candidatos que passem heurísticas estritas.
        - Atribuir uma pontuação a cada candidato com base em sinais fortes de rótulo
          (dois-pontos, presença de palavras-chaves, curta extensão, ausência de
          números, categoria etc.).
        - Selecionar o melhor candidato (se atingir threshold) e adicioná-lo — no
          máximo um novo rótulo.
        
        Args:
            elements: Lista de elementos extraídos pelo unstructured
            
        Returns:
            Conjunto de rótulos que compõem a assinatura estrutural
        """
        signature: Set[str] = set()
        candidates: List[Tuple[str, float]] = []  # (label, score)
        def token_similarity(a: str, b: str) -> float:
            ta = set(a.split())
            tb = set(b.split())
            if not ta and not tb:
                return 0.0
            inter = ta.intersection(tb)
            uni = ta.union(tb)
            return len(inter) / len(uni)

        for elem in elements:
            text = elem.get('text', '').strip()
            if not text:
                continue

            normalized_text = self._normalize_text(text)

            # Regra 1: Rótulo conhecido -> adiciona sem contagem ao limite de 1 novo rótulo
            if normalized_text in self.known_labels:
                signature.add(normalized_text)
                continue

            # Evitar valores puramente numéricos ou monetários
            if re.fullmatch(r'[\d\.,\-\/R\$ %]+', text):
                continue

            # Evitar sentenças longas (rótulos são geralmente curtos)
            if len(normalized_text.split()) > 4:
                continue
    
            # Heurísticas adicionais para filtrar ruído
            if not (2 <= len(normalized_text) <= 50):
                continue

            # Evitar textos que contenham muitas cifras/ dígitos
            if sum(c.isdigit() for c in normalized_text) / max(1, len(normalized_text)) > 0.2:
                continue

            # Evitar se muito semelhante a um rótulo já presente
            too_similar = False
            for s in signature:
                if token_similarity(normalized_text, s) > 0.75:
                    too_similar = True
                    break
            if too_similar:
                continue

            # Se possui ":", adiciona sem contagem ao limite de 1 novo rótulo
            if re.search(r':\s*$', text):
                signature.add(normalized_text)
                continue

            # Score heurístico para priorizar o melhor candidato
            category = elem.get('category', '')
            score = 0.0

            # Palavra-chave do domínio (aumenta confiança)
            domain_keywords = ['nome', 'endereco', 'telefone', 'cpf', 'cnpj', 'email', 'valor', 'data', 'vencimento', 'total', 'subtotal']
            for kw in domain_keywords:
                if kw in normalized_text:
                    score += 2.0

            # Preferir textos curtos (1-3 tokens)
            tokens = normalized_text.split()
            if len(tokens) == 1:
                score += 1.2
            elif len(tokens) <= 3:
                score += 0.8

            # Penalizar presença de dígitos (provável valor)
            if re.search(r'\d', normalized_text):
                score -= 2.0

            # Penalizar se contém palavras muito comuns sem sentido (stopwords simples)
            stopwords = {'de', 'do', 'da', 'dos', 'das', 'e', 'ou', 'para', 'com', 'em', 'por'}
            stopword_ratio = sum(1 for t in tokens if t in stopwords) / max(1, len(tokens))
            if stopword_ratio > 0.5:
                score -= 1.0

            # Leve bônus se categoria sinalizou algo mas não foi Title
            if category:
                score += 0.3

            # Só considerar candidatos com score razoável
            if score > 0.0:
                candidates.append((normalized_text, score))

        # Seleciona o melhor candidato (máximo 1 novo rótulo)
        if candidates:
            # Ordena por score desc e por comprimento asc para desempate
            candidates.sort(key=lambda x: (-x[1], len(x[0])))
            best_label, best_score = candidates[0]

            # Threshold conservador para aceitar um novo rótulo
            if best_score >= 1.5:
                # Evitar duplicatas contra known_labels (por segurança)
                if best_label not in self.known_labels and best_label not in signature:
                    signature.add(best_label)
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