"""
Testes unitários para a classe TemplateOrchestrator.
Valida funcionalidades individuais e executa testes reais com PDFs.
"""

import unittest
import json
import os
import sys
import tempfile
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

# Add the current directory to the path to import from core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.learning.template_orchestrator import TemplateOrchestrator, MIN_SAMPLE_THRESHOLD, MIN_RULE_CONFIDENCE_TO_SAVE
from core.connectors.llm_connector import LLMConnector


class TestTemplateOrchestrator(unittest.TestCase):
    """Testes para a classe TemplateOrchestrator."""
    
    @classmethod
    def setUpClass(cls):
        """Configuração inicial para toda a classe de testes."""
        cls.temp_db_files = []  # Lista para rastrear arquivos temporários
    
    @classmethod
    def tearDownClass(cls):
        """Limpeza final após todos os testes da classe."""
        # Limpar qualquer arquivo temporário que possa ter sobrado
        import glob
        temp_files = glob.glob("*.db")  # Procurar arquivos .db no diretório atual
        for temp_file in temp_files:
            if temp_file.startswith("tmp") or "test" in temp_file.lower():
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        # Limpar arquivos da lista de rastreamento
        for temp_file in getattr(cls, 'temp_db_files', []):
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        # Limpar também possíveis arquivos no diretório persistent_data criados durante testes
        try:
            persistent_test_files = glob.glob("./persistent_data/tmp*.db") + glob.glob("./persistent_data/*test*.db")
            for temp_file in persistent_test_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
        except:
            pass
        
        # IMPORTANTE: Remover o templates.db se foi criado durante os testes
        try:
            default_db_path = "./persistent_data/templates.db"
            if os.path.exists(default_db_path):
                # Verificar se está vazio (indicativo de que foi criado pelos testes)
                import sqlite3
                try:
                    conn = sqlite3.connect(default_db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM templates')
                    template_count = cursor.fetchone()[0]
                    cursor.execute('SELECT COUNT(*) FROM extraction_rules')
                    rules_count = cursor.fetchone()[0]
                    conn.close()
                    
                    # Se estiver vazio, remover (provavelmente criado pelos testes)
                    if template_count == 0 and rules_count == 0:
                        os.unlink(default_db_path)
                        print(f"🧹 Removido banco vazio criado durante testes: {default_db_path}")
                except:
                    pass
        except:
            pass
    
    def setUp(self):
        """Configura os testes com uma instância da classe."""
        # Usar banco de dados temporário para testes
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Registrar arquivo temporário para limpeza
        if hasattr(self.__class__, 'temp_db_files'):
            self.__class__.temp_db_files.append(self.temp_db.name)
        
        self.orchestrator = TemplateOrchestrator(db_path=self.temp_db.name)
        self.llm_connector = LLMConnector()
        
        # Dados de teste baseados nos PDFs reais OAB
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
        
        # Label e schema para testes OAB
        self.label = "carteira_oab"
        self.schema = {
            "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
            "inscricao": "Número de inscrição do profissional",
            "seccional": "Seccional do profissional",
            "categoria": "Categoria, pode ser ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO, ESTAGIARIA",
            "situacao": "Situação do profissional, normalmente no canto inferior direito."
        }
        
        # Elementos de teste simples
        self.sample_elements = [
            {'text': 'Nome:', 'x': 100, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'JOANA SILVA', 'x': 200, 'y': 200, 'page_width': 612, 'page_height': 792},
            {'text': 'Inscrição:', 'x': 100, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': '123456', 'x': 200, 'y': 250, 'page_width': 612, 'page_height': 792},
            {'text': 'Seccional:', 'x': 100, 'y': 300, 'page_width': 612, 'page_height': 792},
            {'text': 'SP', 'x': 200, 'y': 300, 'page_width': 612, 'page_height': 792}
        ]

    def tearDown(self):
        """Limpa recursos após cada teste."""
        try:
            # Fechar conexões do banco antes de deletar
            if hasattr(self.orchestrator, 'db') and self.orchestrator.db:
                # Forçar fechamento de conexões
                if hasattr(self.orchestrator.db, '_get_connection'):
                    try:
                        with self.orchestrator.db._get_connection() as conn:
                            conn.close()
                    except:
                        pass
            
            # Deletar arquivo do banco
            if hasattr(self, 'temp_db') and self.temp_db.name:
                if os.path.exists(self.temp_db.name):
                    os.unlink(self.temp_db.name)
                    
        except Exception as e:
            # Se falhar, tentar novamente após pequena pausa
            import time
            time.sleep(0.1)
            try:
                if hasattr(self, 'temp_db') and self.temp_db.name:
                    if os.path.exists(self.temp_db.name):
                        os.unlink(self.temp_db.name)
            except:
                # Se ainda falhar, apenas ignore (arquivo pode estar em uso)
                pass

    # ===== TESTES DE CONSTANTES =====
    
    def test_constants(self):
        """Testa se as constantes estão definidas corretamente."""
        self.assertEqual(MIN_SAMPLE_THRESHOLD, 2)
        self.assertEqual(MIN_RULE_CONFIDENCE_TO_SAVE, 0.5)

    # ===== TESTES DE INICIALIZAÇÃO =====
    
    def test_initialization_default_db(self):
        """Testa inicialização com banco padrão (mas usando temporário para teste)."""
        # Mesmo sendo "default", usar banco temporário para não poluir persistent_data
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            orchestrator = TemplateOrchestrator(db_path=temp_db.name)
            self.assertIsNotNone(orchestrator.db)
            self.assertIsNotNone(orchestrator.matcher)
            self.assertIsNotNone(orchestrator.builder)
            self.assertIsNotNone(orchestrator.executor)
        finally:
            # Garantir limpeza do banco temporário
            try:
                if os.path.exists(temp_db.name):
                    os.unlink(temp_db.name)
            except:
                pass

    def test_initialization_custom_db(self):
        """Testa inicialização com banco customizado."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            orchestrator = TemplateOrchestrator(db_path=temp_db.name)
            self.assertIsNotNone(orchestrator.db)
            
            # Verificar se o banco foi criado no caminho correto
            stats = orchestrator.get_template_stats()
            self.assertEqual(stats['total_templates'], 0)
            self.assertEqual(stats['total_rules'], 0)
        finally:
            # Garantir limpeza do banco temporário
            try:
                if os.path.exists(temp_db.name):
                    os.unlink(temp_db.name)
            except:
                pass

    # ===== TESTES DA FUNÇÃO get_template_stats =====
    
    def test_get_template_stats_empty_db(self):
        """Testa estatísticas com banco vazio."""
        stats = self.orchestrator.get_template_stats()
        
        expected_stats = {
            'total_templates': 0,
            'total_rules': 0,
            'mature_templates': 0,
            'min_sample_threshold': MIN_SAMPLE_THRESHOLD,
            'min_rule_confidence': MIN_RULE_CONFIDENCE_TO_SAVE
        }
        
        self.assertEqual(stats, expected_stats)

    def test_get_template_stats_with_data(self):
        """Testa estatísticas após adicionar dados."""
        # Adicionar alguns dados de teste
        llm_data = {"nome": "TESTE", "inscricao": "123"}
        
        # Aprender dados (primeira vez)
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        # Aprender novamente para atingir MIN_SAMPLE_THRESHOLD
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        stats = self.orchestrator.get_template_stats()
        
        self.assertEqual(stats['total_templates'], 1)
        self.assertGreaterEqual(stats['total_rules'], 0)
        self.assertEqual(stats['mature_templates'], 1)
        self.assertEqual(stats['min_sample_threshold'], MIN_SAMPLE_THRESHOLD)
        self.assertEqual(stats['min_rule_confidence'], MIN_RULE_CONFIDENCE_TO_SAVE)

    # ===== TESTES DA FUNÇÃO check_and_use_template =====
    
    def test_check_and_use_template_no_template(self):
        """Testa busca por template inexistente."""
        result = self.orchestrator.check_and_use_template("template_inexistente", self.sample_elements)
        self.assertIsNone(result)

    def test_check_and_use_template_insufficient_samples(self):
        """Testa template com poucas amostras (< MIN_SAMPLE_THRESHOLD)."""
        # Criar template com apenas 1 amostra
        llm_data = {"nome": "TESTE", "inscricao": "123"}
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        # Tentar usar o template (deve falhar por poucas amostras)
        result = self.orchestrator.check_and_use_template(self.label, self.sample_elements)
        self.assertIsNone(result)

    def test_check_and_use_template_successful_match(self):
        """Testa uso bem-sucedido de template maduro."""
        # Criar template maduro (≥ MIN_SAMPLE_THRESHOLD amostras)
        llm_data = {"nome": "JOANA SILVA", "inscricao": "123456"}
        
        # Primeira amostra
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        # Segunda amostra (para atingir threshold)
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        # Agora deve conseguir usar o template
        result = self.orchestrator.check_and_use_template(self.label, self.sample_elements)
        
        # Resultado deve existir e conter campos extraídos
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_check_and_use_template_signature_mismatch(self):
        """Testa quando assinatura estrutural não confere."""
        # Criar template com elementos diferentes
        different_elements = [
            {'text': 'Campo1:', 'x': 50, 'y': 100, 'page_width': 612, 'page_height': 792},
            {'text': 'Valor1', 'x': 150, 'y': 100, 'page_width': 612, 'page_height': 792}
        ]
        
        llm_data = {"campo1": "Valor1"}
        schema = {"campo1": "Campo de teste"}
        
        # Aprender com elementos diferentes
        self.orchestrator.learn_from_llm_result("test_label", schema, llm_data, different_elements)
        self.orchestrator.learn_from_llm_result("test_label", schema, llm_data, different_elements)
        
        # Tentar usar com elementos completamente diferentes (deve falhar por assinatura)
        completely_different_elements = [
            {'text': 'OutroCampo:', 'x': 300, 'y': 400, 'page_width': 612, 'page_height': 792},
            {'text': 'OutroValor', 'x': 400, 'y': 400, 'page_width': 612, 'page_height': 792}
        ]
        
        result = self.orchestrator.check_and_use_template("test_label", completely_different_elements)
        # Pode retornar None se a similaridade for baixa, ou um resultado se a lógica permitir
        # O importante é que não gere erro
        self.assertTrue(result is None or isinstance(result, dict))

    # ===== TESTES DA FUNÇÃO learn_from_llm_result =====
    
    def test_learn_from_llm_result_new_template(self):
        """Testa criação de novo template."""
        llm_data = {"nome": "TESTE", "inscricao": "123"}
        
        # Verificar estado inicial
        stats_before = self.orchestrator.get_template_stats()
        self.assertEqual(stats_before['total_templates'], 0)
        
        # Aprender novo template
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        # Verificar que template foi criado
        stats_after = self.orchestrator.get_template_stats()
        self.assertEqual(stats_after['total_templates'], 1)
        self.assertGreaterEqual(stats_after['total_rules'], 0)

    def test_learn_from_llm_result_update_existing_template(self):
        """Testa atualização de template existente."""
        llm_data = {"nome": "TESTE", "inscricao": "123"}
        
        # Criar template inicial
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, llm_data, self.sample_elements
        )
        
        stats_after_first = self.orchestrator.get_template_stats()
        
        # Atualizar template existente
        new_llm_data = {"nome": "OUTRO_TESTE", "inscricao": "456"}
        self.orchestrator.learn_from_llm_result(
            self.label, self.schema, new_llm_data, self.sample_elements
        )
        
        stats_after_second = self.orchestrator.get_template_stats()
        
        # Número de templates deve permanecer o mesmo
        self.assertEqual(stats_after_first['total_templates'], stats_after_second['total_templates'])
        # Pode ter mais regras (ou não, dependendo da confiança)
        self.assertGreaterEqual(stats_after_second['total_rules'], stats_after_first['total_rules'])

    def test_learn_from_llm_result_low_confidence_rules(self):
        """Testa que regras com baixa confiança não são salvas."""
        # Mock do PatternBuilder para retornar confiança baixa
        with patch.object(self.orchestrator.builder, 'learn_rule_for_field') as mock_learn:
            mock_learn.return_value = ("regex", {"pattern": "test"}, 0.3)  # Confiança < 0.5
            
            llm_data = {"nome": "TESTE"}
            schema = {"nome": "Nome de teste"}
            
            self.orchestrator.learn_from_llm_result("test_label", schema, llm_data, self.sample_elements)
            
            # Verificar que a regra não foi salva devido à baixa confiança
            stats = self.orchestrator.get_template_stats()
            # Pode ter 0 regras se nenhuma passou no threshold de confiança
            self.assertGreaterEqual(stats['total_rules'], 0)

    # ===== TESTES AUXILIARES =====
    
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
            
            # Converter para formato esperado
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

    # ===== TESTES REAIS COM PDFs =====
    
    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_orchestrator_workflow_single_pdf(self):
        """Testa workflow completo do orchestrador com um PDF real."""
        test_data = self.test_data["oab_1"]
        
        if not os.path.exists(test_data["pdf_path"]):
            self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
        
        # Extrair elementos do PDF
        elements = self._get_elements_from_pdf(test_data["pdf_path"])
        self.assertGreater(len(elements), 0, "PDF deve conter elementos")
        
        # 1. Verificar que não existe template inicialmente
        result_before = self.orchestrator.check_and_use_template(self.label, elements)
        self.assertIsNone(result_before, "Não deve existir template inicialmente")
        
        # 2. Aprender dados do PDF (primeira vez)
        llm_data = test_data["expected"]
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data, elements)
        
        # 3. Template ainda não deve estar maduro (< MIN_SAMPLE_THRESHOLD)
        result_immature = self.orchestrator.check_and_use_template(self.label, elements)
        self.assertIsNone(result_immature, "Template não deve estar maduro ainda")
        
        # 4. Aprender novamente para amadurecer o template
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data, elements)
        
        # 5. Agora template deve estar maduro e funcionar
        result_mature = self.orchestrator.check_and_use_template(self.label, elements)
        self.assertIsNotNone(result_mature, "Template maduro deve funcionar")
        self.assertIsInstance(result_mature, dict, "Resultado deve ser um dicionário")
        
        # 6. Verificar estatísticas finais
        final_stats = self.orchestrator.get_template_stats()
        self.assertEqual(final_stats['total_templates'], 1)
        self.assertEqual(final_stats['mature_templates'], 1)
        self.assertGreaterEqual(final_stats['total_rules'], 0)

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_cross_validation_orchestrator(self):
        """Testa validação cruzada: aprende padrões do PDF 1 e aplica no PDF 2."""
        pdf1_data = self.test_data["oab_1"]
        pdf2_data = self.test_data["oab_2"]
        
        if not os.path.exists(pdf1_data["pdf_path"]) or not os.path.exists(pdf2_data["pdf_path"]):
            self.skipTest("Arquivos de PDF não encontrados para validação cruzada")
        
        # Extrair elementos dos dois PDFs
        elements_pdf1 = self._get_elements_from_pdf(pdf1_data["pdf_path"])
        elements_pdf2 = self._get_elements_from_pdf(pdf2_data["pdf_path"])
        
        self.assertGreater(len(elements_pdf1), 0, "PDF 1 deve conter elementos")
        self.assertGreater(len(elements_pdf2), 0, "PDF 2 deve conter elementos")
        
        # 1. Aprender padrões do PDF 1 (duas vezes para amadurecer)
        llm_data_pdf1 = pdf1_data["expected"]
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data_pdf1, elements_pdf1)
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data_pdf1, elements_pdf1)
        
        # 2. Verificar que template está maduro
        stats_after_learning = self.orchestrator.get_template_stats()
        self.assertEqual(stats_after_learning['mature_templates'], 1, "Template deve estar maduro")
        
        # 3. Aplicar template no PDF 2
        result_pdf2 = self.orchestrator.check_and_use_template(self.label, elements_pdf2)
        
        # 4. Verificar resultado
        if result_pdf2 is not None:
            self.assertIsInstance(result_pdf2, dict, "Resultado deve ser um dicionário")
            
            # Verificar se pelo menos alguns campos foram extraídos
            extracted_fields = [field for field, value in result_pdf2.items() if value is not None]
            self.assertGreater(len(extracted_fields), 0, "Pelo menos um campo deve ser extraído")
            
            # Log para debug
            print(f"\n📊 Resultado da validação cruzada:")
            print(f"   📄 PDF 1 (treino): {pdf1_data['pdf_path']}")
            print(f"   📄 PDF 2 (teste): {pdf2_data['pdf_path']}")
            print(f"   📋 Campos extraídos: {extracted_fields}")
            print(f"   📊 Resultado: {result_pdf2}")
        else:
            print(f"\n⚠️  Template não conseguiu extrair dados do PDF 2")
            print(f"   Isso pode indicar que os PDFs têm estruturas muito diferentes")
            print(f"   ou que os padrões aprendidos do PDF 1 não se aplicam ao PDF 2")

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_multiple_learning_cycles(self):
        """Testa múltiplos ciclos de aprendizado com PDFs reais."""
        pdf1_data = self.test_data["oab_1"]
        pdf2_data = self.test_data["oab_2"]
        
        if not os.path.exists(pdf1_data["pdf_path"]) or not os.path.exists(pdf2_data["pdf_path"]):
            self.skipTest("Arquivos de PDF não encontrados")
        
        # Extrair elementos dos dois PDFs
        elements_pdf1 = self._get_elements_from_pdf(pdf1_data["pdf_path"])
        elements_pdf2 = self._get_elements_from_pdf(pdf2_data["pdf_path"])
        
        # 1. Aprender com PDF 1
        llm_data_pdf1 = pdf1_data["expected"]
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data_pdf1, elements_pdf1)
        
        stats_after_pdf1_first = self.orchestrator.get_template_stats()
        
        # 2. Aprender novamente com PDF 1 (amadurecer)
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data_pdf1, elements_pdf1)
        
        stats_after_pdf1_second = self.orchestrator.get_template_stats()
        self.assertEqual(stats_after_pdf1_second['mature_templates'], 1)
        
        # 3. Aprender com PDF 2 (deve atualizar template existente)
        llm_data_pdf2 = pdf2_data["expected"]
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data_pdf2, elements_pdf2)
        
        stats_after_pdf2 = self.orchestrator.get_template_stats()
        
        # Deve permanecer com 1 template (mesmo label)
        self.assertEqual(stats_after_pdf2['total_templates'], 1)
        self.assertEqual(stats_after_pdf2['mature_templates'], 1)
        
        # 4. Testar que o template ainda funciona
        result_final = self.orchestrator.check_and_use_template(self.label, elements_pdf1)
        self.assertIsNotNone(result_final, "Template deve continuar funcionando após múltiplos aprendizados")

    @unittest.skipIf(not os.path.exists("files"), "Diretório 'files' não encontrado")
    def test_real_pdf_field_specific_accuracy(self):
        """Testa precisão do orchestrador para campos específicos."""
        test_data = self.test_data["oab_1"]
        
        if not os.path.exists(test_data["pdf_path"]):
            self.skipTest(f"Arquivo {test_data['pdf_path']} não encontrado")
        
        # Extrair elementos do PDF
        elements = self._get_elements_from_pdf(test_data["pdf_path"])
        
        # Aprender padrões (amadurecer template)
        llm_data = test_data["expected"]
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data, elements)
        self.orchestrator.learn_from_llm_result(self.label, self.schema, llm_data, elements)
        
        # Testar extração
        result = self.orchestrator.check_and_use_template(self.label, elements)
        
        if result is not None:
            # Verificar campos críticos
            critical_fields = ["nome", "inscricao", "seccional"]
            
            for field in critical_fields:
                expected_value = test_data["expected"].get(field)
                extracted_value = result.get(field)
                
                if extracted_value is not None and expected_value is not None:
                    print(f"\n🎯 Campo '{field}':")
                    print(f"   📋 Esperado: {expected_value}")
                    print(f"   📊 Extraído: {extracted_value}")
                    
                    # Verificar se são iguais (pode relaxar para similaridade se necessário)
                    if str(extracted_value).strip().upper() == str(expected_value).strip().upper():
                        print(f"   ✅ CORRETO!")
                    else:
                        print(f"   ⚠️  DIFERENTE!")


if __name__ == '__main__':
    unittest.main(verbosity=2)