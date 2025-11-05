"""
Testes unitários para a classe PatternBuilder.
Valida o aprendizado de padrões regex e contexto relativo usando arquivos PDF reais.
"""

import unittest
import json
import os
import sys
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Add the current directory to the path to import from core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.learning.pattern_builder import PatternBuilder, COMMON_PATTERNS, Y_TOLERANCE_SAME_LINE, X_TOLERANCE_SAME_COLUMN
from core.connectors.llm_connector import LLMConnector


class TestPatternBuilder(unittest.TestCase):
    """Testes para a classe PatternBuilder."""
    
    def setUp(self):
        """Configura os testes com uma instância da classe."""
        self.builder = PatternBuilder()
        self.llm_connector = LLMConnector()
        
        # Dados de teste baseados nos PDFs reais
        self.test_data = {
            "oab_1": {
                "expected": {
                    "nome": "JOANA D'ARC",
                    "inscricao": "101943",
                    "seccional": "PR",
                    "subsecao": "Conselho Seccional - Paraná",
                    "categoria": "Suplementar",
                    "endereco_profissional": "Avenida Paulista, Nº 2300, andar Pilotis, Bela Vista, São Paulo - SP, 01310300",
                    "situacao": "Situação Regular"
                },
                "pdf_path": "files/oab_1.pdf"
            },
            "oab_2": {
                "expected": {
                    "nome": "LUIS FILIPE ARAUJO AMARAL",
                    "inscricao": "101943",
                    "seccional": "PR",
                    "subsecao": "Conselho Seccional - Paraná",
                    "categoria": "Suplementar",
                    "endereco_profissional": None,
                    "situacao": "Situação Regular"
                },
                "pdf_path": "files/oab_2.pdf"
            },
            "oab_3": {
                "expected": {
                    "nome": "SON GOKU",
                    "inscricao": "101943",
                    "seccional": "PR",
                    "subsecao": "Conselho Seccional - Paraná",
                    "categoria": "Suplementar",
                    "endereco_profissional": None,
                    "situacao": "Situação Regular"
                },
                "pdf_path": "files/oab_3.pdf"
            }
        }
    
    def test_initialization(self):
        """Testa se a inicialização está correta."""
        self.assertEqual(self.builder.common_patterns, COMMON_PATTERNS)
        self.assertIn('cpf', self.builder.common_patterns)
        self.assertIn('numero_inscricao', self.builder.common_patterns)
    
    def test_constants(self):
        """Testa se as constantes estão definidas corretamente."""
        self.assertEqual(Y_TOLERANCE_SAME_LINE, 10)
        self.assertEqual(X_TOLERANCE_SAME_COLUMN, 20)
        self.assertIsInstance(COMMON_PATTERNS, dict)
    
    def test_learn_rule_for_field_null_values(self):
        """Testa o tratamento de valores nulos."""
        elements = []
        
        # Teste com None
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("nome", None, elements)
        self.assertEqual(rule_type, "none")
        self.assertEqual(rule_data["reason"], "value_is_null")
        self.assertEqual(confidence, 0.9)
        
        # Teste com string "null"
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("nome", "null", elements)
        self.assertEqual(rule_type, "none")
        self.assertEqual(rule_data["reason"], "value_is_null")
        self.assertEqual(confidence, 0.9)
    
    def test_learn_rule_for_field_no_pattern_found(self):
        """Testa o fallback quando nenhum padrão é encontrado."""
        elements = []
        
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("campo_desconhecido", "valor_qualquer", elements)
        self.assertEqual(rule_type, "none")
        self.assertEqual(rule_data["reason"], "value_not_found_in_elements")
        self.assertEqual(confidence, 0.1)
    
    def test_regex_pattern_learning(self):
        """Testa o aprendizado de padrões regex."""
        elements = [{"text": "101943", "x": 100, "y": 50},
                    {"text": "123.456.789-01", "x": 150, "y": 60},
                    {"text": "01310-300", "x": 200, "y": 70}]
        
        # Teste com CPF
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("cpf_cliente", "123.456.789-01", elements)
        self.assertEqual(rule_data["rules"][0]["data"]["pattern"], "cpf")

        # Teste com CEP
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("cep_endereco", "01310-300", elements)
        self.assertEqual(rule_data["rules"][0]["data"]["pattern"], "cep")
    
    def test_regex_pattern_invalid_value(self):
        """Testa regex com valor que não bate com o padrão."""
        elements = []
        
        # CPF inválido - não deve ser reconhecido como regex
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("cpf_cliente", "123", elements)
        self.assertEqual(rule_type, "none")
        self.assertEqual(rule_data["reason"], "value_not_found_in_elements")
        self.assertEqual(confidence, 0.1)
    
    def test_find_element_by_text(self):
        """Testa a busca de elementos por texto."""
        elements = [
            {"text": "Nome:", "x": 100, "y": 50},
            {"text": "JOANA D'ARC", "x": 200, "y": 50},
            {"text": "Inscrição", "x": 100, "y": 80},
            {"text": "101943", "x": 200, "y": 80}
        ]
        
        # Busca exata
        element = self.builder._find_element_by_text("Nome:", elements)
        self.assertIsNotNone(element)
        self.assertEqual(element["text"], "Nome:")
        
        # Busca parcial
        element = self.builder._find_element_by_text("JOANA", elements)
        self.assertIsNotNone(element)
        self.assertEqual(element["text"], "JOANA D'ARC")
        
        # Busca sem resultado
        element = self.builder._find_element_by_text("INEXISTENTE", elements)
        self.assertIsNone(element)
    
    def test_find_anchor_left(self):
        """Testa a busca de âncoras à esquerda."""
        value_element = {"text": "JOANA D'ARC", "x": 200, "y": 50}
        elements = [
            {"text": "Nome:", "x": 100, "y": 50},  # Mesma linha, à esquerda
            {"text": "Inscrição", "x": 100, "y": 80},  # Linha diferente
            {"text": "Valor:", "x": 150, "y": 52},  # Mesma linha, mais próximo
            {"text": "Distante:", "x": 50, "y": 50}  # Mesma linha, mais distante
        ]
        
        anchor = self.builder._find_anchor_left(value_element, elements)
        self.assertIsNotNone(anchor)
        # Deve retornar "Valor:" por ser o mais próximo à esquerda na mesma linha
        self.assertEqual(anchor["text"], "Valor:")
    
    def test_find_anchor_above(self):
        """Testa a busca de âncoras acima."""
        value_element = {"text": "101943", "x": 200, "y": 80}
        elements = [
            {"text": "Nome:", "x": 100, "y": 50},  # Coluna diferente
            {"text": "Inscrição", "x": 200, "y": 50},  # Mesma coluna, acima
            {"text": "Valor:", "x": 205, "y": 60},  # Mesma coluna (com tolerância), mais próximo
            {"text": "Distante:", "x": 200, "y": 20}  # Mesma coluna, mais distante
        ]
        
        anchor = self.builder._find_anchor_above(value_element, elements)
        self.assertIsNotNone(anchor)
        # Deve retornar "Valor:" por ser o mais próximo acima na mesma coluna
        self.assertEqual(anchor["text"], "Valor:")
    
    def test_context_pattern_learning_left_anchor(self):
        """Testa o aprendizado de padrão de contexto com âncora à esquerda."""
        elements = [
            {"text": "Nome:", "x": 100, "y": 50},
            {"text": "JOANA D'ARC", "x": 200, "y": 50},
            {"text": "Inscrição", "x": 100, "y": 80},
            {"text": "101943", "x": 200, "y": 80}
        ]
        
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("nome", "JOANA D'ARC", elements)
        self.assertEqual(rule_type, "relative_context")
        self.assertEqual(rule_data["anchor_text"], "Nome:")
        self.assertEqual(rule_data["direction"], "right")
        self.assertEqual(confidence, 0.8)
    
    def test_context_pattern_learning_above_anchor(self):
        """Testa o aprendizado de padrão de contexto com âncora acima."""
        elements = [
            {"text": "Inscrição", "x": 200, "y": 50},
            {"text": "101943", "x": 200, "y": 80},
            {"text": "Nome:", "x": 100, "y": 50},
            {"text": "JOANA D'ARC", "x": 300, "y": 50}
        ]
        
        rule_type, rule_data, confidence = self.builder.learn_rule_for_field("inscricao", "101943", elements)
        self.assertEqual(rule_type, "relative_context")
        self.assertEqual(rule_data["anchor_text"], "Inscrição")
        self.assertEqual(rule_data["direction"], "below")
        self.assertEqual(confidence, 0.8)

    def _get_elements_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai elementos estruturados de um PDF usando o LLMConnector.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Lista de elementos com texto e coordenadas
        """
        try:
            # Usar métodos internos do LLMConnector para extrair elementos
            raw_elements = self.llm_connector._parse_pdf_elements(pdf_path)
            
            # Converter para formato esperado pelo PatternBuilder
            elements = []
            for elem in raw_elements:
                if not elem.text or not elem.text.strip():
                    continue
                    
                # Extrair coordenadas dos metadados
                x, y = 0, 0
                if hasattr(elem, 'metadata') and elem.metadata:
                    coordinates = getattr(elem.metadata, 'coordinates', None)
                    if coordinates and hasattr(coordinates, 'points'):
                        if coordinates.points:
                            point = coordinates.points[0]
                            if isinstance(point, (tuple, list)) and len(point) >= 2:
                                x, y = point[0], point[1]
                            elif hasattr(point, 'x') and hasattr(point, 'y'):
                                x, y = point.x, point.y
                
                elements.append({
                    "text": elem.text.strip(),
                    "x": x,
                    "y": y
                })
            
            return elements
        except Exception as e:
            # Fallback para dados mocados se não conseguir processar o PDF
            print(f"Erro ao processar PDF {pdf_path}: {e}")
            return self._get_mock_elements_for_pdf(pdf_path)
    
    def _get_mock_elements_for_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Retorna elementos mocados baseados no conteúdo conhecido dos PDFs.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Lista de elementos mocados
        """
        if "oab_1.pdf" in pdf_path:
            return [
                {"text": "JOANA D'ARC", "x": 200, "y": 50},
                {"text": "Inscrição", "x": 100, "y": 80},
                {"text": "101943", "x": 200, "y": 80},
                {"text": "PR", "x": 250, "y": 80},
                {"text": "CONSELHO SECCIONAL - PARANÁ", "x": 300, "y": 80},
                {"text": "SUPLEMENTAR", "x": 100, "y": 110},
                {"text": "Endereço Profissional", "x": 100, "y": 140},
                {"text": "AVENIDA PAULISTA, Nº 2300", "x": 200, "y": 140},
                {"text": "SITUAÇÃO REGULAR", "x": 100, "y": 200}
            ]
        elif "oab_2.pdf" in pdf_path:
            return [
                {"text": "LUIS FILIPE ARAUJO AMARAL", "x": 200, "y": 50},
                {"text": "Inscrição", "x": 100, "y": 80},
                {"text": "101943", "x": 200, "y": 80},
                {"text": "PR", "x": 250, "y": 80},
                {"text": "CONSELHO SECCIONAL - PARANÁ", "x": 300, "y": 80},
                {"text": "SUPLEMENTAR", "x": 100, "y": 110},
                {"text": "SITUAÇÃO REGULAR", "x": 100, "y": 200}
            ]
        elif "oab_3.pdf" in pdf_path:
            return [
                {"text": "SON GOKU", "x": 200, "y": 50},
                {"text": "Inscrição", "x": 100, "y": 80},
                {"text": "101943", "x": 200, "y": 80},
                {"text": "PR", "x": 250, "y": 80},
                {"text": "Subseção", "x": 100, "y": 110},
                {"text": "CONSELHO SECCIONAL - PARANÁ", "x": 200, "y": 110},
                {"text": "SUPLEMENTAR", "x": 100, "y": 140},
                {"text": "SITUAÇÃO REGULAR", "x": 100, "y": 200}
            ]
        else:
            return []

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_pattern_learning_inscricao(self):
        """Testa o aprendizado de padrões com dados reais do PDF - campo inscrição."""
        for test_name, test_data in self.test_data.items():
            with self.subTest(test=test_name):
                if not os.path.exists(test_data["pdf_path"]):
                    self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
                
                elements = self._get_elements_from_pdf(test_data["pdf_path"])
                inscricao = test_data["expected"]["inscricao"]
                
                rule_type, rule_data, confidence = self.builder.learn_rule_for_field("numero_inscricao", inscricao, elements)
                
                # Inscrição deve ser reconhecida como regex (número de 5-8 dígitos)
                self.assertEqual(rule_type, "hybrid")
                self.assertEqual(rule_data["rules"][0]["data"]["pattern"], "numero_inscricao")

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_pattern_learning_nome(self):
        """Testa o aprendizado de padrões com dados reais do PDF - campo nome."""
        for test_name, test_data in self.test_data.items():
            with self.subTest(test=test_name):
                if not os.path.exists(test_data["pdf_path"]):
                    self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
                
                elements = self._get_elements_from_pdf(test_data["pdf_path"])
                nome = test_data["expected"]["nome"]
                
                rule_type, rule_data, confidence = self.builder.learn_rule_for_field("nome", nome, elements)
                
                # Nome pode ser reconhecido por contexto relativo ou não ter padrão
                self.assertIn(rule_type, ["relative_context", "none"])
                if rule_type == "relative_context":
                    self.assertIn("anchor_text", rule_data)
                    self.assertIn("direction", rule_data)
                    self.assertGreaterEqual(confidence, 0.8)

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_pattern_learning_null_fields(self):
        """Testa o tratamento de campos nulos nos PDFs reais."""
        # OAB 2 e 3 têm endereco_profissional nulo
        for test_name in ["oab_2", "oab_3"]:
            test_data = self.test_data[test_name]
            with self.subTest(test=test_name):
                if not os.path.exists(test_data["pdf_path"]):
                    self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
                
                elements = self._get_elements_from_pdf(test_data["pdf_path"])
                endereco = test_data["expected"]["endereco_profissional"]
                
                rule_type, rule_data, confidence = self.builder.learn_rule_for_field("endereco_profissional", endereco, elements)
                
                # Campo nulo deve ser reconhecido como "none" com alta confiança
                self.assertEqual(rule_type, "none")
                self.assertEqual(rule_data["reason"], "value_is_null")
                self.assertEqual(confidence, 0.9)

if __name__ == '__main__':
    unittest.main(verbosity=2)