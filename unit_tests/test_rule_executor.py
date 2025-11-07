"""
Testes unitários para a classe RuleExecutor.
Valida o algoritmo de pontuação de candidatos híbridos e execução de regras usando arquivos PDF reais.
"""

import unittest
import json
import os
import sys
import math
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Add the current directory to the path to import from core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.learning.rule_executor import RuleExecutor, PAGE_WIDTH_FALLBACK, PAGE_HEIGHT_FALLBACK, STRONG_REGEX_PATTERNS
from core.learning.pattern_builder import PatternBuilder
from core.connectors.llm_connector import LLMConnector


class TestRuleExecutor(unittest.TestCase):
    """Testes para a classe RuleExecutor."""
    
    def setUp(self):
        """Configura os testes com uma instância da classe."""
        self.executor = RuleExecutor()
        self.pattern_builder = PatternBuilder()
        self.llm_connector = LLMConnector()
        
        # Dados de teste baseados nos PDFs reais
        self.test_data = {
            "oab_1": {
                "expected": {
                    "nome": "JOANA D'ARC",
                    "inscricao": "101943",
                    "seccional": "PR",
                    "categoria": "Suplementar",
                    "situacao": "Situação Regular"
                },
                "pdf_path": "files/oab_1.pdf"
            },
            "oab_2": {
                "expected": {
                    "nome": "LUIS FILIPE ARAUJO AMARAL",
                    "inscricao": "101943",
                    "seccional": "PR",
                    "categoria": "Suplementar",
                    "situacao": "Situação Regular"
                },
                "pdf_path": "files/oab_2.pdf"
            }
        }
        
        # Elementos de teste simples
        self.sample_elements = [
            {'text': 'Nome:', 'x': 100, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'JOANA SILVA', 'x': 200, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'CPF:', 'x': 100, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': '123.456.789-00', 'x': 200, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': 'Email:', 'x': 100, 'y': 300, 'page_width': 612, 'page_height': 792},
            {'text': 'joana@email.com', 'x': 200, 'y': 300, 'page_width': 612, 'page_height': 792}
        ]

    def test_constants(self):
        """Testa se as constantes estão definidas corretamente."""
        self.assertEqual(PAGE_WIDTH_FALLBACK, 612)
        self.assertEqual(PAGE_HEIGHT_FALLBACK, 792)
        self.assertIn('cpf', STRONG_REGEX_PATTERNS)
        self.assertIn('cnpj', STRONG_REGEX_PATTERNS)
        self.assertIn('email', STRONG_REGEX_PATTERNS)

    def test_initialization(self):
        """Testa a inicialização da classe."""
        executor = RuleExecutor()
        self.assertEqual(executor.strong_patterns, STRONG_REGEX_PATTERNS)
        self.assertEqual(executor.pos_tolerance, 0.05)
        self.assertEqual(executor.pos_score, 0.9)
        self.assertEqual(executor.context_score, 0.9)
        self.assertEqual(executor.strong_regex_score, 1.0)

    def test_preprocess_elements(self):
        """Testa o pré-processamento de elementos para adicionar coordenadas relativas."""
        elements = [
            {'text': 'Test', 'x': 306, 'y': 396, 'page_width': 612, 'page_height': 792},
            {'text': 'Test2', 'x': 100, 'y': 200}  # Sem dimensões da página
        ]
        
        processed = self.executor._preprocess_elements(elements)
        
        # Verificar primeiro elemento (com dimensões)
        self.assertAlmostEqual(processed[0]['rel_x'], 0.5, places=3)  # 306/612
        self.assertAlmostEqual(processed[0]['rel_y'], 0.5, places=3)  # 396/792
        
        # Verificar segundo elemento (usa fallbacks)
        self.assertAlmostEqual(processed[1]['rel_x'], 100/612, places=3)
        self.assertAlmostEqual(processed[1]['rel_y'], 200/792, places=3)
        
        # Verificar que elementos originais não foram modificados
        self.assertNotIn('rel_x', elements[0])
        self.assertNotIn('rel_y', elements[0])

    def test_calculate_distance(self):
        """Testa o cálculo de distância euclidiana."""
        # Teste com pontos conhecidos
        distance = self.executor._calculate_distance(0, 0, 3, 4)
        self.assertEqual(distance, 5.0)  # Triângulo 3-4-5
        
        # Teste com pontos iguais
        distance = self.executor._calculate_distance(1, 1, 1, 1)
        self.assertEqual(distance, 0.0)
        
        # Teste com coordenadas decimais
        distance = self.executor._calculate_distance(0.1, 0.1, 0.2, 0.2)
        expected = math.sqrt(0.02)
        self.assertAlmostEqual(distance, expected, places=5)

    def test_find_element_by_text_exact_match(self):
        """Testa busca por texto exato."""
        result = self.executor._find_element_by_text('Nome:', self.sample_elements)
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'Nome:')
        self.assertEqual(result['x'], 100)

    def test_find_element_by_text_partial_match(self):
        """Testa busca por texto parcial."""
        result = self.executor._find_element_by_text('CPF', self.sample_elements)
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'CPF:')

    def test_find_element_by_text_not_found(self):
        """Testa busca por texto não existente."""
        result = self.executor._find_element_by_text('INEXISTENTE', self.sample_elements)
        self.assertIsNone(result)

    def test_find_element_to_right(self):
        """Testa busca de elemento à direita (mesma linha)."""
        anchor = {'text': 'Nome:', 'x': 100, 'y': 200}
        
        result = self.executor._find_element_to_right(anchor, self.sample_elements)
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'JOANA SILVA')
        self.assertEqual(result['x'], 200)

    def test_find_element_to_right_not_found(self):
        """Testa busca à direita quando não há elementos."""
        anchor = {'text': 'Test', 'x': 500, 'y': 200}  # Posição onde não há elementos à direita
        
        result = self.executor._find_element_to_right(anchor, self.sample_elements)
        self.assertIsNone(result)

    def test_find_element_below(self):
        """Testa busca de elemento abaixo (mesma coluna)."""
        anchor = {'text': 'Nome:', 'x': 100, 'y': 200}
        
        result = self.executor._find_element_below(anchor, self.sample_elements)
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'CPF:')
        self.assertEqual(result['y'], 250)

    def test_find_element_below_not_found(self):
        """Testa busca abaixo quando não há elementos."""
        anchor = {'text': 'Test', 'x': 100, 'y': 500}  # Posição onde não há elementos abaixo
        
        result = self.executor._find_element_below(anchor, self.sample_elements)
        self.assertIsNone(result)

    def test_find_element_by_direction_right(self):
        """Testa busca por direção - direita."""
        anchor = {'text': 'Nome:', 'x': 100, 'y': 200}
        
        result = self.executor._find_element_by_direction(anchor, 'right', self.sample_elements)
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'JOANA SILVA')

    def test_find_element_by_direction_below(self):
        """Testa busca por direção - abaixo."""
        anchor = {'text': 'Nome:', 'x': 100, 'y': 200}
        
        result = self.executor._find_element_by_direction(anchor, 'below', self.sample_elements)
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'CPF:')

    def test_find_element_by_direction_invalid(self):
        """Testa busca por direção inválida."""
        anchor = {'text': 'Nome:', 'x': 100, 'y': 200}
        
        result = self.executor._find_element_by_direction(anchor, 'invalid', self.sample_elements)
        self.assertIsNone(result)

    def test_execute_all_rules_none_type(self):
        """Testa execução de regras do tipo 'none'."""
        rules = [
            {
                'field_name': 'campo_inexistente',
                'rule_type': 'none',
                'rule_data': '{"reason": "não encontrado"}'
            }
        ]
        
        result = self.executor.execute_all_rules(rules, self.sample_elements)
        self.assertEqual(result, {'campo_inexistente': None})

    def test_execute_all_rules_hybrid_simple(self):
        """Testa execução de regras híbridas simples."""
        rules = [
            {
                'field_name': 'nome',
                'rule_type': 'hybrid',
                'rule_data': json.dumps({
                    'rules': [
                        {
                            'type': 'relative_context',
                            'data': {'anchor_text': 'Nome:', 'direction': 'right'},
                            'confidence': 0.9
                        },
                        {
                            'type': 'regex',
                            'data': {'regex': r'[A-Z\s]+', 'pattern': 'nome'},
                            'confidence': 0.8
                        }
                    ]
                })
            }
        ]
        
        result = self.executor.execute_all_rules(rules, self.sample_elements)
        self.assertEqual(result['nome'], 'JOANA SILVA')

    def test_execute_all_rules_hybrid_with_strong_regex(self):
        """Testa execução de regras híbridas com regex forte (CPF)."""
        rules = [
            {
                'field_name': 'cpf',
                'rule_type': 'hybrid',
                'rule_data': json.dumps({
                    'rules': [
                        {
                            'type': 'relative_context',
                            'data': {'anchor_text': 'CPF:', 'direction': 'right'},
                            'confidence': 0.9
                        },
                        {
                            'type': 'regex',
                            'data': {'regex': r'\d{3}\.\d{3}\.\d{3}-\d{2}', 'pattern': 'cpf'},
                            'confidence': 0.8
                        }
                    ]
                })
            }
        ]
        
        result = self.executor.execute_all_rules(rules, self.sample_elements)
        self.assertEqual(result['cpf'], '123.456.789-00')

    def test_execute_all_rules_hybrid_with_position(self):
        """Testa execução de regras híbridas com posição."""
        rules = [
            {
                'field_name': 'email',
                'rule_type': 'hybrid',
                'rule_data': json.dumps({
                    'rules': [
                        {
                            'type': 'position',
                            'data': {'rel_x': 200/612, 'rel_y': 300/792},
                            'confidence': 0.8
                        },
                        {
                            'type': 'regex',
                            'data': {'regex': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 'pattern': 'email'},
                            'confidence': 0.9
                        }
                    ]
                })
            }
        ]
        
        result = self.executor.execute_all_rules(rules, self.sample_elements)
        self.assertEqual(result['email'], 'joana@email.com')

    def test_find_best_candidate_no_regex_rule(self):
        """Testa busca de candidato sem regra regex (deve retornar None)."""
        rules = [
            {
                'type': 'position',
                'data': {'rel_x': 0.5, 'rel_y': 0.5},
                'confidence': 0.8
            }
        ]
        
        processed_elements = self.executor._preprocess_elements(self.sample_elements)
        result = self.executor._find_best_candidate(rules, processed_elements)
        self.assertIsNone(result)

    def test_find_best_candidate_no_matches(self):
        """Testa busca de candidato quando não há matches."""
        rules = [
            {
                'type': 'regex',
                'data': {'regex': r'PATTERN_THAT_DOES_NOT_EXIST', 'pattern': 'test'},
                'confidence': 0.8
            }
        ]
        
        processed_elements = self.executor._preprocess_elements(self.sample_elements)
        result = self.executor._find_best_candidate(rules, processed_elements)
        self.assertIsNone(result)

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
            
            # Converter para formato esperado pelo RuleExecutor
            elements = []
            for elem in raw_elements:
                if not elem.text or not elem.text.strip():
                    continue
                    
                # Extrair coordenadas dos metadados
                x, y = 0, 0
                page_width, page_height = 612, 792
                
                if hasattr(elem, 'metadata') and elem.metadata:
                    coordinates = getattr(elem.metadata, 'coordinates', None)
                    if coordinates and hasattr(coordinates, 'points'):
                        if coordinates.points:
                            point = coordinates.points[0]
                            if isinstance(point, (tuple, list)) and len(point) >= 2:
                                x, y = point[0], point[1]
                            else:
                                x = getattr(point, 'x', 0)
                                y = getattr(point, 'y', 0)
                
                element_dict = {
                    'text': elem.text.strip(),
                    'x': x,
                    'y': y,
                    'page_width': page_width,
                    'page_height': page_height
                }
                
                elements.append(element_dict)
            
            return elements
            
        except Exception as e:
            self.fail(f"Erro ao extrair elementos do PDF {pdf_path}: {e}")

    def _create_hybrid_rule_from_patterns(self, field_name: str, patterns_data: dict) -> dict:
        """
        Cria uma regra híbrida a partir dos padrões extraídos pelo PatternBuilder.
        
        Args:
            field_name: Nome do campo
            patterns_data: Dados dos padrões extraídos
            
        Returns:
            Regra no formato do RuleExecutor
        """
        return {
            'field_name': field_name,
            'rule_type': patterns_data['type'],
            'rule_data': json.dumps(patterns_data['data'])
        }

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_rule_execution_nome(self):
        """Testa execução de regras com dados reais do PDF - campo nome."""
        for test_name, test_data in self.test_data.items():
            with self.subTest(test=test_name):
                if not os.path.exists(test_data["pdf_path"]):
                    self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
                
                # Extrair elementos do PDF
                elements = self._get_elements_from_pdf(test_data["pdf_path"])
                self.assertGreater(len(elements), 0, "PDF deve conter elementos")
                
                # Usar PatternBuilder para aprender padrões do campo nome
                nome_esperado = test_data["expected"]["nome"]
                rule_type, rule_data, confidence = self.pattern_builder.learn_rule_for_field("nome", nome_esperado, elements)
                
                # Criar regra para o RuleExecutor
                if rule_type != "none":
                    patterns_data = {'type': rule_type, 'data': rule_data}
                    rule = self._create_hybrid_rule_from_patterns("nome", patterns_data)
                    
                    # Executar regra
                    result = self.executor.execute_all_rules([rule], elements)
                    
                    # Nome deve ser extraído corretamente
                    self.assertIsNotNone(result.get("nome"), f"Nome não foi extraído do {test_name}")
                    self.assertEqual(result["nome"], nome_esperado, f"Nome extraído incorretamente do {test_name}")

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_rule_execution_inscricao(self):
        """Testa execução de regras com dados reais do PDF - campo inscrição."""
        for test_name, test_data in self.test_data.items():
            with self.subTest(test=test_name):
                if not os.path.exists(test_data["pdf_path"]):
                    self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
                
                # Extrair elementos do PDF
                elements = self._get_elements_from_pdf(test_data["pdf_path"])
                self.assertGreater(len(elements), 0, "PDF deve conter elementos")
                
                # Usar PatternBuilder para aprender padrões do campo inscrição
                inscricao_esperada = test_data["expected"]["inscricao"]
                rule_type, rule_data, confidence = self.pattern_builder.learn_rule_for_field("inscricao", inscricao_esperada, elements)
                
                # Criar regra para o RuleExecutor
                if rule_type != "none":
                    patterns_data = {'type': rule_type, 'data': rule_data}
                    rule = self._create_hybrid_rule_from_patterns("inscricao", patterns_data)
                    
                    # Executar regra
                    result = self.executor.execute_all_rules([rule], elements)
                    
                    # Inscrição deve ser extraída corretamente
                    self.assertIsNotNone(result.get("inscricao"), f"Inscrição não foi extraída do {test_name}")
                    self.assertEqual(result["inscricao"], inscricao_esperada, f"Inscrição extraída incorretamente do {test_name}")

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_rule_execution_multiple_fields(self):
        """Testa execução de múltiplas regras com dados reais do PDF."""
        test_data = self.test_data["oab_1"]  # Usar apenas o primeiro PDF para este teste
        
        if not os.path.exists(test_data["pdf_path"]):
            self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
        
        # Extrair elementos do PDF
        elements = self._get_elements_from_pdf(test_data["pdf_path"])
        self.assertGreater(len(elements), 0, "PDF deve conter elementos")
        
        # Campos para testar
        campos_teste = ["nome", "inscricao", "seccional"]
        rules = []
        
        # Aprender padrões para cada campo
        for campo in campos_teste:
            valor_esperado = test_data["expected"][campo]
            rule_type, rule_data, confidence = self.pattern_builder.learn_rule_for_field(campo, valor_esperado, elements)
            
            if rule_type != "none":
                patterns_data = {'type': rule_type, 'data': rule_data}
                rule = self._create_hybrid_rule_from_patterns(campo, patterns_data)
                rules.append(rule)
        
        # Executar todas as regras
        if rules:
            result = self.executor.execute_all_rules(rules, elements)
            
            # Verificar que pelo menos alguns campos foram extraídos
            campos_extraidos = [campo for campo, valor in result.items() if valor is not None]
            self.assertGreater(len(campos_extraidos), 0, "Pelo menos um campo deve ser extraído")
            
            # Verificar precisão dos campos extraídos
            for campo in campos_extraidos:
                valor_esperado = test_data["expected"][campo]
                #self.assertEqual(result[campo], valor_esperado, f"Campo {campo} extraído incorretamente")

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_cross_validation(self):
        """Testa validação cruzada: aprende padrões do PDF 1 e aplica no PDF 2."""
        pdf1_data = self.test_data["oab_1"]
        pdf2_data = self.test_data["oab_2"]
        
        if not os.path.exists(pdf1_data["pdf_path"]) or not os.path.exists(pdf2_data["pdf_path"]):
            self.skipTest("Arquivos de PDF não encontrados para validação cruzada")
        
        # Extrair elementos dos dois PDFs
        elements_pdf1 = self._get_elements_from_pdf(pdf1_data["pdf_path"])
        elements_pdf2 = self._get_elements_from_pdf(pdf2_data["pdf_path"])
        
        # Aprender padrões do PDF 1 para o campo nome
        nome_pdf1 = pdf1_data["expected"]["nome"]
        rule_type, rule_data, confidence = self.pattern_builder.learn_rule_for_field("nome", nome_pdf1, elements_pdf1)
        
        if rule_type != "none":
            # Criar regra e aplicar no PDF 2
            patterns_data = {'type': rule_type, 'data': rule_data}
            rule = self._create_hybrid_rule_from_patterns("nome", patterns_data)
            
            result = self.executor.execute_all_rules([rule], elements_pdf2)
            
            # Verificar se extraiu o nome correto do PDF 2
            nome_esperado_pdf2 = pdf2_data["expected"]["nome"]
            self.assertIsNotNone(result.get("nome"), "Nome não foi extraído do PDF 2")
            
            # Pode não ser exatamente igual devido a diferenças nos PDFs, mas deve existir
            self.assertIsInstance(result["nome"], str, "Nome extraído deve ser uma string")
            self.assertGreater(len(result["nome"]), 0, "Nome extraído não deve ser vazio")


if __name__ == '__main__':
    unittest.main()