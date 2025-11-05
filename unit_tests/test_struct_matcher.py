"""
Testes unitários para a classe StructuralMatcher.
Valida a normalização de texto, similaridade Jaccard e verificação de matches.
"""

import unittest
from typing import Dict, Any, List, Set
from core.learning.struct_matcher import StructuralMatcher, JACCARD_MATCH_THRESHOLD, KNOWN_LABELS


class TestStructuralMatcher(unittest.TestCase):
    """Testes para a classe StructuralMatcher."""
    
    def setUp(self):
        """Configura os testes com uma instância da classe."""
        self.matcher = StructuralMatcher()
    
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
    
    def test_check_similarity_high_match(self):
        """Testa verificação de similaridade com match alto."""
        new_signature = {"nome", "endereco", "telefone", "cpf"}
        template_signature_list = ["nome", "endereco", "telefone", "cnpj"]
        
        # Jaccard = 3/5 = 0.6 (menor que threshold de 0.8)
        is_match, score = self.matcher.check_similarity(new_signature, template_signature_list)
        self.assertFalse(is_match)
        self.assertAlmostEqual(score, 0.6, places=2)
    
    def test_check_similarity_exact_match(self):
        """Testa verificação de similaridade com match exato."""
        new_signature = {"nome", "endereco", "telefone"}
        template_signature_list = ["nome", "endereco", "telefone"]
        
        is_match, score = self.matcher.check_similarity(new_signature, template_signature_list)
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)
    
    def test_check_similarity_above_threshold(self):
        """Testa verificação de similaridade acima do threshold."""
        new_signature = {"nome", "endereco", "telefone", "cpf", "situacao"}
        template_signature_list = ["nome", "endereco", "telefone", "cpf"]
        
        # Jaccard = 4/5 = 0.8 (igual ao threshold)
        is_match, score = self.matcher.check_similarity(new_signature, template_signature_list)
        self.assertTrue(is_match)
        self.assertAlmostEqual(score, 0.8, places=2)


if __name__ == '__main__':
    unittest.main()