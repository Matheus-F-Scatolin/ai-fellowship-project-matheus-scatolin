"""
Testes unitários para a classe StructuralMatcher.
Valida a normalização de texto, similaridade Jaccard, verificação de matches e extração de assinaturas.
"""

import unittest
from typing import Dict, Any, List, Set
from unittest.mock import Mock, patch
from core.learning.struct_matcher import StructuralMatcher, JACCARD_MATCH_THRESHOLD, KNOWN_LABELS


class TestStructuralMatcher(unittest.TestCase):
    """Testes para a classe StructuralMatcher."""
    
    def setUp(self):
        """Configura os testes com uma instância da classe."""
        self.matcher = StructuralMatcher()
        
        # Elementos de teste simulando estrutura de documentos
        self.sample_elements = [
            {'text': 'Nome:', 'x': 100, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'JOANA SILVA', 'x': 200, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'Inscrição:', 'x': 100, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': '123456', 'x': 200, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': 'Telefone:', 'x': 100, 'y': 300, 'page_width': 612, 'page_height': 792},
            {'text': '(11) 9999-9999', 'x': 200, 'y': 300, 'page_width': 612, 'page_height': 792}
        ]
        
        self.sample_elements_different = [
            {'text': 'Produto:', 'x': 100, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'Notebook Dell', 'x': 200, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'Valor:', 'x': 100, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': 'R$ 2.500,00', 'x': 200, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': 'Quantidade:', 'x': 100, 'y': 300, 'page_width': 612, 'page_height': 792},
            {'text': '2', 'x': 200, 'y': 300, 'page_width': 612, 'page_height': 792}
        ]
    
    def test_initialization(self):
        """Testa se a inicialização está correta."""
        self.assertEqual(self.matcher.known_labels, KNOWN_LABELS)
        self.assertEqual(self.matcher.match_threshold, JACCARD_MATCH_THRESHOLD)
        self.assertEqual(self.matcher.match_threshold, 0.80)
    
    def test_normalize_text_basic(self):
        """Testa a normalização básica de texto."""
        # Teste básico de minúsculas
        result = self.matcher._normalize_text("NOME")
        self.assertEqual(result, "nome")
        
        # Teste de remoção de dois-pontos
        result = self.matcher._normalize_text("Endereço:")
        self.assertEqual(result, "endereco")
        
        # Teste de remoção de acentos
        result = self.matcher._normalize_text("Situação")
        self.assertEqual(result, "situacao")
        
        # Teste combinado
        result = self.matcher._normalize_text("INSCRIÇÃO:")
        self.assertEqual(result, "inscricao")
    
    def test_normalize_text_special_characters(self):
        """Testa normalização com caracteres especiais."""
        # Teste com ç
        result = self.matcher._normalize_text("Seção:")
        self.assertEqual(result, "secao")
        
        # Teste com múltiplos acentos
        result = self.matcher._normalize_text("Informações Adicionais")
        self.assertEqual(result, "informacoes adicionais")
        
        # Teste com dois pontos no meio não são removidos
        result = self.matcher._normalize_text("  Telefone:  ")
        self.assertEqual(result, "telefone:")
        
        # Teste com dois pontos no final que devem ser removidos
        result = self.matcher._normalize_text("Telefone:")
        self.assertEqual(result, "telefone")
    
    def test_calculate_jaccard_similarity_identical_sets(self):
        """Testa similaridade Jaccard com conjuntos idênticos."""
        set1 = {"nome", "endereco", "telefone"}
        set2 = {"nome", "endereco", "telefone"}
        
        similarity = self.matcher._calculate_jaccard_similarity(set1, set2)
        self.assertEqual(similarity, 1.0)
    
    def test_calculate_jaccard_similarity_disjoint_sets(self):
        """Testa similaridade Jaccard com conjuntos disjuntos."""
        set1 = {"nome", "endereco", "telefone"}
        set2 = {"produto", "valor", "quantidade"}
        
        similarity = self.matcher._calculate_jaccard_similarity(set1, set2)
        self.assertEqual(similarity, 0.0)
    
    def test_calculate_jaccard_similarity_partial_overlap(self):
        """Testa similaridade Jaccard com sobreposição parcial."""
        set1 = {"nome", "endereco", "telefone"}
        set2 = {"nome", "telefone", "cpf", "cnpj"}
        
        # Interseção: {nome, telefone} = 2 elementos
        # União: {nome, endereco, telefone, cpf, cnpj} = 5 elementos
        # Jaccard = 2/5 = 0.4
        similarity = self.matcher._calculate_jaccard_similarity(set1, set2)
        self.assertAlmostEqual(similarity, 0.4, places=2)
    
    def test_calculate_jaccard_similarity_empty_sets(self):
        """Testa similaridade Jaccard com conjuntos vazios."""
        set1 = set()
        set2 = set()
        
        similarity = self.matcher._calculate_jaccard_similarity(set1, set2)
        self.assertEqual(similarity, 0.0)
        
        # Um conjunto vazio, outro não
        set1 = {"nome"}
        set2 = set()
        
        similarity = self.matcher._calculate_jaccard_similarity(set1, set2)
        self.assertEqual(similarity, 0.0)
    
    @patch.object(StructuralMatcher, '_normalize_text')
    def test_extract_signature_basic(self, mock_normalize):
        """Testa extração básica de assinatura."""
        # Mock da normalização para simplificar o teste
        mock_normalize.return_value = "nome: joana silva inscricao: 123456 telefone: (11) 9999-9999"
        
 
        signature = self.matcher.extract_signature(self.sample_elements)
        
        # Verifica se encontrou os labels conhecidos
        expected_labels = {'nome', 'inscricao', 'telefone'}
        self.assertEqual(signature, expected_labels)
    
    @patch.object(StructuralMatcher, '_normalize_text')
    def test_extract_signature_different_document(self, mock_normalize):
        """Testa extração de assinatura com documento diferente."""
        # Mock da normalização para documento de produto
        mock_normalize.return_value = "produto: notebook dell valor: r$ 2.500,00 quantidade: 2"
        
        signature = self.matcher.extract_signature(self.sample_elements_different)
        
        # Verifica se encontrou os labels conhecidos
        expected_labels = {'produto', 'valor', 'quantidade'}
        self.assertEqual(signature, expected_labels)
    
    @patch.object(StructuralMatcher, '_normalize_text')
    def test_extract_signature_empty_elements(self, mock_normalize):
        """Testa extração de assinatura com elementos vazios."""
        mock_normalize.return_value = ""
        signature = self.matcher.extract_signature([])
        # Deve retornar conjunto vazio
        self.assertEqual(signature, set())
    
    @patch.object(StructuralMatcher, '_normalize_text')
    def test_extract_signature_no_known_labels(self, mock_normalize):
        """Testa extração de assinatura sem labels conhecidos."""
        mock_normalize.return_value = "campo desconhecido: val campo estranho: outro val"
        
        signature = self.matcher.extract_signature(self.sample_elements)
        
        # Deve retornar conjunto vazio pois não há labels conhecidos
        self.assertEqual(signature, set())
    
    def test_check_similarity_high_match(self):
        """Testa verificação de similaridade com match alto."""
        # Mock do extract_signature para retornar assinatura específica
        with patch.object(self.matcher, 'extract_signature', return_value={'nome', 'endereco', 'telefone', 'cpf'}):
            template_signature_list = ["nome", "endereco", "telefone", "cnpj"]
            
            # Jaccard = 3/5 = 0.6 (menor que threshold de 0.8)
            is_match, score = self.matcher.check_similarity(self.sample_elements, template_signature_list)
            self.assertFalse(is_match)
            self.assertAlmostEqual(score, 0.6, places=2)
    
    def test_check_similarity_exact_match(self):
        """Testa verificação de similaridade com match exato."""
        # Mock do extract_signature para retornar assinatura idêntica
        with patch.object(self.matcher, 'extract_signature', return_value={'nome', 'endereco', 'telefone'}):
            template_signature_list = ["nome", "endereco", "telefone"]
            
            is_match, score = self.matcher.check_similarity(self.sample_elements, template_signature_list)
            self.assertTrue(is_match)
            self.assertEqual(score, 1.0)
    
    def test_check_similarity_above_threshold(self):
        """Testa verificação de similaridade acima do threshold."""
        # Mock do extract_signature para retornar assinatura com 80% de similaridade
        with patch.object(self.matcher, 'extract_signature', return_value={'nome', 'endereco', 'telefone', 'cpf', 'situacao'}):
            template_signature_list = ["nome", "endereco", "telefone", "cpf"]
            
            # Jaccard = 4/5 = 0.8 (igual ao threshold)
            is_match, score = self.matcher.check_similarity(self.sample_elements, template_signature_list)
            self.assertTrue(is_match)
            self.assertAlmostEqual(score, 0.8, places=2)
    
    def test_check_similarity_below_threshold(self):
        """Testa verificação de similaridade abaixo do threshold."""
        # Mock do extract_signature para retornar assinatura com baixa similaridade
        with patch.object(self.matcher, 'extract_signature', return_value={'produto', 'valor', 'quantidade'}):
            template_signature_list = ["nome", "endereco", "telefone", "cpf"]
            
            # Jaccard = 0/7 = 0.0 (muito abaixo do threshold)
            is_match, score = self.matcher.check_similarity(self.sample_elements, template_signature_list)
            self.assertFalse(is_match)
            self.assertEqual(score, 0.0)
    
    def test_check_similarity_empty_signature(self):
        """Testa verificação de similaridade com assinatura vazia."""
        # Mock do extract_signature para retornar conjunto vazio
        with patch.object(self.matcher, 'extract_signature', return_value=set()):
            template_signature_list = ["nome", "endereco", "telefone"]
            
            is_match, score = self.matcher.check_similarity(self.sample_elements, template_signature_list)
            self.assertFalse(is_match)
            self.assertEqual(score, 0.0)
    
    def test_check_similarity_empty_template(self):
        """Testa verificação de similaridade com template vazio."""
        # Mock do extract_signature para retornar assinatura normal
        with patch.object(self.matcher, 'extract_signature', return_value={'nome', 'telefone'}):
            template_signature_list = []
            
            is_match, score = self.matcher.check_similarity(self.sample_elements, template_signature_list)
            self.assertFalse(is_match)
            self.assertEqual(score, 0.0)


if __name__ == '__main__':
    unittest.main()