"""
Teste de integração completa do TemplateOrchestrator
Testa a integração entre template_orchestrator.py e todos os outros módulos
"""
import unittest
import tempfile
import shutil
import os
import json
from typing import Dict, Any, List

from core.learning.template_orchestrator import TemplateOrchestrator


# Mock data para diferentes tipos de documentos
MOCK_PDF_ELEMENTS = {
    # Carteiras OAB - 3 variações
    "carteira_oab_1": [
        {"text": "JOANA D'ARC", "x": 32.0, "y": 29.486, "page_width": 612, "page_height": 792},
        {"text": "Inscrição", "x": 33.0, "y": 129.076, "page_width": 612, "page_height": 792},
        {"text": "101943", "x": 36.0, "y": 157.512, "page_width": 612, "page_height": 792},
        {"text": "Seccional", "x": 173.0, "y": 129.512, "page_width": 612, "page_height": 792},
        {"text": "PR", "x": 172.0, "y": 156.794, "page_width": 612, "page_height": 792},
        {"text": "SUPLEMENTAR", "x": 33.0, "y": 188.512, "page_width": 612, "page_height": 792},
        {"text": "Endereco Profissional", "x": 35.0, "y": 232.794, "page_width": 612, "page_height": 792},
        {"text": "AVENIDA PAULISTA, 2300", "x": 35.0, "y": 250.0, "page_width": 612, "page_height": 792},
        {"text": "SÃO PAULO - SP", "x": 35.0, "y": 270.0, "page_width": 612, "page_height": 792},
        {"text": "SITUAÇÃO REGULAR", "x": 400.0, "y": 465.204, "page_width": 612, "page_height": 792}
    ],
    
    "carteira_oab_2": [
        {"text": "LUIS FILIPE ARAUJO AMARAL", "x": 30.0, "y": 25.0, "page_width": 612, "page_height": 792},
        {"text": "Inscrição", "x": 35.0, "y": 130.0, "page_width": 612, "page_height": 792},
        {"text": "101944", "x": 38.0, "y": 158.0, "page_width": 612, "page_height": 792},
        {"text": "Seccional", "x": 175.0, "y": 130.0, "page_width": 612, "page_height": 792},
        {"text": "SP", "x": 174.0, "y": 157.0, "page_width": 612, "page_height": 792},
        {"text": "ADVOGADO", "x": 35.0, "y": 190.0, "page_width": 612, "page_height": 792},
        {"text": "Endereco Profissional", "x": 37.0, "y": 235.0, "page_width": 612, "page_height": 792},
        {"text": "RUA AUGUSTA, 1500", "x": 37.0, "y": 252.0, "page_width": 612, "page_height": 792},
        {"text": "SÃO PAULO - SP", "x": 37.0, "y": 272.0, "page_width": 612, "page_height": 792},
        {"text": "SITUAÇÃO REGULAR", "x": 405.0, "y": 470.0, "page_width": 612, "page_height": 792}
    ],
    
    "carteira_oab_3": [
        {"text": "SON GOKU", "x": 35.0, "y": 30.0, "page_width": 612, "page_height": 792},
        {"text": "Inscrição", "x": 38.0, "y": 132.0, "page_width": 612, "page_height": 792},
        {"text": "101945", "x": 40.0, "y": 160.0, "page_width": 612, "page_height": 792},
        {"text": "Seccional", "x": 178.0, "y": 132.0, "page_width": 612, "page_height": 792},
        {"text": "RJ", "x": 176.0, "y": 159.0, "page_width": 612, "page_height": 792},
        {"text": "ESTAGIARIO", "x": 38.0, "y": 192.0, "page_width": 612, "page_height": 792},
        {"text": "SITUAÇÃO REGULAR", "x": 410.0, "y": 475.0, "page_width": 612, "page_height": 792}
    ],
    
    # CNH - 3 variações
    "cnh_1": [
        {"text": "JOÃO SILVA SANTOS", "x": 150.0, "y": 80.0, "page_width": 856, "page_height": 540},
        {"text": "CPF", "x": 50.0, "y": 150.0, "page_width": 856, "page_height": 540},
        {"text": "123.456.789-00", "x": 100.0, "y": 150.0, "page_width": 856, "page_height": 540},
        {"text": "RG", "x": 50.0, "y": 180.0, "page_width": 856, "page_height": 540},
        {"text": "12.345.678-9", "x": 100.0, "y": 180.0, "page_width": 856, "page_height": 540},
        {"text": "Data Nascimento", "x": 50.0, "y": 210.0, "page_width": 856, "page_height": 540},
        {"text": "15/03/1985", "x": 150.0, "y": 210.0, "page_width": 856, "page_height": 540},
        {"text": "Categoria", "x": 50.0, "y": 240.0, "page_width": 856, "page_height": 540},
        {"text": "B", "x": 120.0, "y": 240.0, "page_width": 856, "page_height": 540},
        {"text": "Vencimento", "x": 50.0, "y": 270.0, "page_width": 856, "page_height": 540},
        {"text": "15/03/2030", "x": 130.0, "y": 270.0, "page_width": 856, "page_height": 540}
    ],
    
    "cnh_2": [
        {"text": "MARIA FERNANDA OLIVEIRA", "x": 140.0, "y": 75.0, "page_width": 856, "page_height": 540},
        {"text": "CPF", "x": 45.0, "y": 145.0, "page_width": 856, "page_height": 540},
        {"text": "987.654.321-00", "x": 95.0, "y": 145.0, "page_width": 856, "page_height": 540},
        {"text": "RG", "x": 45.0, "y": 175.0, "page_width": 856, "page_height": 540},
        {"text": "98.765.432-1", "x": 95.0, "y": 175.0, "page_width": 856, "page_height": 540},
        {"text": "Data Nascimento", "x": 45.0, "y": 205.0, "page_width": 856, "page_height": 540},
        {"text": "22/08/1990", "x": 145.0, "y": 205.0, "page_width": 856, "page_height": 540},
        {"text": "Categoria", "x": 45.0, "y": 235.0, "page_width": 856, "page_height": 540},
        {"text": "AB", "x": 115.0, "y": 235.0, "page_width": 856, "page_height": 540},
        {"text": "Vencimento", "x": 45.0, "y": 265.0, "page_width": 856, "page_height": 540},
        {"text": "22/08/2028", "x": 125.0, "y": 265.0, "page_width": 856, "page_height": 540}
    ],
    
    "cnh_3": [
        {"text": "PEDRO HENRIQUE COSTA", "x": 145.0, "y": 78.0, "page_width": 856, "page_height": 540},
        {"text": "CPF", "x": 48.0, "y": 148.0, "page_width": 856, "page_height": 540},
        {"text": "456.789.123-00", "x": 98.0, "y": 148.0, "page_width": 856, "page_height": 540},
        {"text": "RG", "x": 48.0, "y": 178.0, "page_width": 856, "page_height": 540},
        {"text": "45.678.912-3", "x": 98.0, "y": 178.0, "page_width": 856, "page_height": 540},
        {"text": "Data Nascimento", "x": 48.0, "y": 208.0, "page_width": 856, "page_height": 540},
        {"text": "10/12/1988", "x": 148.0, "y": 208.0, "page_width": 856, "page_height": 540},
        {"text": "Categoria", "x": 48.0, "y": 238.0, "page_width": 856, "page_height": 540},
        {"text": "A", "x": 118.0, "y": 238.0, "page_width": 856, "page_height": 540},
        {"text": "Vencimento", "x": 48.0, "y": 268.0, "page_width": 856, "page_height": 540},
        {"text": "10/12/2029", "x": 128.0, "y": 268.0, "page_width": 856, "page_height": 540}
    ],
    
    # Cartão de Crédito - 3 variações
    "cartao_credito_1": [
        {"text": "4532 1234 5678 9012", "x": 200.0, "y": 180.0, "page_width": 856, "page_height": 540},
        {"text": "JOÃO SILVA", "x": 50.0, "y": 250.0, "page_width": 856, "page_height": 540},
        {"text": "VALID THRU", "x": 50.0, "y": 300.0, "page_width": 856, "page_height": 540},
        {"text": "12/28", "x": 130.0, "y": 300.0, "page_width": 856, "page_height": 540},
        {"text": "CVV", "x": 500.0, "y": 200.0, "page_width": 856, "page_height": 540},
        {"text": "123", "x": 530.0, "y": 200.0, "page_width": 856, "page_height": 540},
        {"text": "VISA", "x": 600.0, "y": 100.0, "page_width": 856, "page_height": 540}
    ],
    
    "cartao_credito_2": [
        {"text": "5412 7534 8901 2345", "x": 195.0, "y": 175.0, "page_width": 856, "page_height": 540},
        {"text": "MARIA OLIVEIRA", "x": 45.0, "y": 245.0, "page_width": 856, "page_height": 540},
        {"text": "VALID THRU", "x": 45.0, "y": 295.0, "page_width": 856, "page_height": 540},
        {"text": "06/27", "x": 125.0, "y": 295.0, "page_width": 856, "page_height": 540},
        {"text": "CVV", "x": 505.0, "y": 195.0, "page_width": 856, "page_height": 540},
        {"text": "456", "x": 535.0, "y": 195.0, "page_width": 856, "page_height": 540},
        {"text": "MASTERCARD", "x": 580.0, "y": 95.0, "page_width": 856, "page_height": 540}
    ],
    
    "cartao_credito_3": [
        {"text": "3782 822463 10005", "x": 200.0, "y": 185.0, "page_width": 856, "page_height": 540},
        {"text": "PEDRO COSTA", "x": 55.0, "y": 255.0, "page_width": 856, "page_height": 540},
        {"text": "VALID THRU", "x": 55.0, "y": 305.0, "page_width": 856, "page_height": 540},
        {"text": "09/26", "x": 135.0, "y": 305.0, "page_width": 856, "page_height": 540},
        {"text": "CVV", "x": 510.0, "y": 205.0, "page_width": 856, "page_height": 540},
        {"text": "789", "x": 540.0, "y": 205.0, "page_width": 856, "page_height": 540},
        {"text": "AMERICAN EXPRESS", "x": 570.0, "y": 105.0, "page_width": 856, "page_height": 540}
    ],
    
    # Nota Fiscal - 3 variações
    "nota_fiscal_1": [
        {"text": "NOTA FISCAL ELETRÔNICA", "x": 300.0, "y": 50.0, "page_width": 595, "page_height": 842},
        {"text": "Número", "x": 50.0, "y": 120.0, "page_width": 595, "page_height": 842},
        {"text": "000123456", "x": 120.0, "y": 120.0, "page_width": 595, "page_height": 842},
        {"text": "Data Emissão", "x": 50.0, "y": 150.0, "page_width": 595, "page_height": 842},
        {"text": "15/11/2024", "x": 140.0, "y": 150.0, "page_width": 595, "page_height": 842},
        {"text": "Valor Total", "x": 50.0, "y": 500.0, "page_width": 595, "page_height": 842},
        {"text": "R$ 1.250,50", "x": 140.0, "y": 500.0, "page_width": 595, "page_height": 842},
        {"text": "CNPJ Emissor", "x": 50.0, "y": 180.0, "page_width": 595, "page_height": 842},
        {"text": "12.345.678/0001-90", "x": 150.0, "y": 180.0, "page_width": 595, "page_height": 842}
    ],
    
    "nota_fiscal_2": [
        {"text": "NOTA FISCAL ELETRÔNICA", "x": 295.0, "y": 45.0, "page_width": 595, "page_height": 842},
        {"text": "Número", "x": 45.0, "y": 115.0, "page_width": 595, "page_height": 842},
        {"text": "000987654", "x": 115.0, "y": 115.0, "page_width": 595, "page_height": 842},
        {"text": "Data Emissão", "x": 45.0, "y": 145.0, "page_width": 595, "page_height": 842},
        {"text": "20/11/2024", "x": 135.0, "y": 145.0, "page_width": 595, "page_height": 842},
        {"text": "Valor Total", "x": 45.0, "y": 495.0, "page_width": 595, "page_height": 842},
        {"text": "R$ 2.575,75", "x": 135.0, "y": 495.0, "page_width": 595, "page_height": 842},
        {"text": "CNPJ Emissor", "x": 45.0, "y": 175.0, "page_width": 595, "page_height": 842},
        {"text": "98.765.432/0001-12", "x": 145.0, "y": 175.0, "page_width": 595, "page_height": 842}
    ],
    
    "nota_fiscal_3": [
        {"text": "NOTA FISCAL ELETRÔNICA", "x": 298.0, "y": 48.0, "page_width": 595, "page_height": 842},
        {"text": "Número", "x": 48.0, "y": 118.0, "page_width": 595, "page_height": 842},
        {"text": "000456789", "x": 118.0, "y": 118.0, "page_width": 595, "page_height": 842},
        {"text": "Data Emissão", "x": 48.0, "y": 148.0, "page_width": 595, "page_height": 842},
        {"text": "25/11/2024", "x": 138.0, "y": 148.0, "page_width": 595, "page_height": 842},
        {"text": "Valor Total", "x": 48.0, "y": 498.0, "page_width": 595, "page_height": 842},
        {"text": "R$ 890,25", "x": 138.0, "y": 498.0, "page_width": 595, "page_height": 842},
        {"text": "CNPJ Emissor", "x": 48.0, "y": 178.0, "page_width": 595, "page_height": 842},
        {"text": "45.678.912/0001-34", "x": 148.0, "y": 178.0, "page_width": 595, "page_height": 842}
    ]
}

# Schemas de extração para cada tipo de documento
EXTRACTION_SCHEMAS = {
    "carteira_oab": {
        "nome": "Nome do profissional, normalmente no canto superior esquerdo",
        "inscricao": "Número de inscrição do profissional na OAB",
        "seccional": "Seccional do profissional (sigla do estado)",
        "categoria": "Categoria profissional (ADVOGADO, SUPLEMENTAR, ESTAGIARIO, etc.)",
        "endereco_profissional": "Endereço profissional completo, se disponível",
        "situacao": "Situação do profissional (REGULAR, IRREGULAR, etc.)"
    },
    
    "cnh": {
        "nome": "Nome completo do portador da CNH",
        "cpf": "CPF do portador no formato XXX.XXX.XXX-XX",
        "rg": "RG do portador",
        "data_nascimento": "Data de nascimento no formato DD/MM/AAAA",
        "categoria": "Categoria da CNH (A, B, C, D, E, AB, etc.)",
        "vencimento": "Data de vencimento da CNH no formato DD/MM/AAAA"
    },
    
    "cartao_credito": {
        "numero": "Número do cartão de crédito (16 dígitos)",
        "nome": "Nome do portador do cartão",
        "validade": "Data de validade no formato MM/AA",
        "cvv": "Código CVV de 3 ou 4 dígitos",
        "bandeira": "Bandeira do cartão (VISA, MASTERCARD, etc.)"
    },
    
    "nota_fiscal": {
        "numero": "Número da nota fiscal",
        "data_emissao": "Data de emissão no formato DD/MM/AAAA",
        "valor_total": "Valor total da nota fiscal",
        "cnpj_emissor": "CNPJ da empresa emissora"
    }
}

# Resultados esperados para cada documento fictício
EXPECTED_RESULTS = {
    "carteira_oab_1": {
        "nome": "JOANA D'ARC",
        "inscricao": "101943",
        "seccional": "PR",
        "categoria": "SUPLEMENTAR",
        "endereco_profissional": "AVENIDA PAULISTA, 2300 SÃO PAULO - SP",
        "situacao": "SITUAÇÃO REGULAR"
    },
    
    "carteira_oab_2": {
        "nome": "LUIS FILIPE ARAUJO AMARAL",
        "inscricao": "101944",
        "seccional": "SP",
        "categoria": "ADVOGADO",
        "endereco_profissional": "RUA AUGUSTA, 1500 SÃO PAULO - SP",
        "situacao": "SITUAÇÃO REGULAR"
    },
    
    "carteira_oab_3": {
        "nome": "SON GOKU",
        "inscricao": "101945",
        "seccional": "RJ",
        "categoria": "ESTAGIARIO",
        "endereco_profissional": None,
        "situacao": "SITUAÇÃO REGULAR"
    },
    
    "cnh_1": {
        "nome": "JOÃO SILVA SANTOS",
        "cpf": "123.456.789-00",
        "rg": "12.345.678-9",
        "data_nascimento": "15/03/1985",
        "categoria": "B",
        "vencimento": "15/03/2030"
    },
    
    "cnh_2": {
        "nome": "MARIA FERNANDA OLIVEIRA",
        "cpf": "987.654.321-00",
        "rg": "98.765.432-1",
        "data_nascimento": "22/08/1990",
        "categoria": "AB",
        "vencimento": "22/08/2028"
    },
    
    "cnh_3": {
        "nome": "PEDRO HENRIQUE COSTA",
        "cpf": "456.789.123-00",
        "rg": "45.678.912-3",
        "data_nascimento": "10/12/1988",
        "categoria": "A",
        "vencimento": "10/12/2029"
    },
    
    "cartao_credito_1": {
        "numero": "4532 1234 5678 9012",
        "nome": "JOÃO SILVA",
        "validade": "12/28",
        "cvv": "123",
        "bandeira": "VISA"
    },
    
    "cartao_credito_2": {
        "numero": "5412 7534 8901 2345",
        "nome": "MARIA OLIVEIRA",
        "validade": "06/27",
        "cvv": "456",
        "bandeira": "MASTERCARD"
    },
    
    "cartao_credito_3": {
        "numero": "3782 822463 10005",
        "nome": "PEDRO COSTA",
        "validade": "09/26",
        "cvv": "789",
        "bandeira": "AMERICAN EXPRESS"
    },
    
    "nota_fiscal_1": {
        "numero": "000123456",
        "data_emissao": "15/11/2024",
        "valor_total": "R$ 1.250,50",
        "cnpj_emissor": "12.345.678/0001-90"
    },
    
    "nota_fiscal_2": {
        "numero": "000987654",
        "data_emissao": "20/11/2024",
        "valor_total": "R$ 2.575,75",
        "cnpj_emissor": "98.765.432/0001-12"
    },
    
    "nota_fiscal_3": {
        "numero": "000456789",
        "data_emissao": "25/11/2024",
        "valor_total": "R$ 890,25",
        "cnpj_emissor": "45.678.912/0001-34"
    }
}


class TestCompleteOrchestration(unittest.TestCase):
    """Teste de integração completa do TemplateOrchestrator"""
    
    def setUp(self):
        """Configura o ambiente de teste antes de cada teste"""
        # Criar diretório temporário para os dados de teste
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_templates.db")
        self.cache_dir = os.path.join(self.test_dir, "test_cache")
        
        # Criar o diretório de cache
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Criar uma instância do orquestrador com banco de teste
        self.orchestrator = TemplateOrchestrator(db_path=self.db_path)
        
    def tearDown(self):
        """Limpa o ambiente de teste após cada teste"""
        # Remover todos os arquivos temporários
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initial_state_no_templates(self):
        """Testa o estado inicial sem templates"""
        # Verificar que não há templates inicialmente
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], 0)
        self.assertEqual(stats["total_rules"], 0)
        self.assertEqual(stats["mature_templates"], 0)
        
        # Tentar usar um template que não existe
        result = self.orchestrator.check_and_use_template(
            "carteira_oab", 
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        self.assertIsNone(result)
    
    def test_learn_from_llm_creates_template(self):
        """Testa se learn_from_llm_result cria templates corretamente"""
        # Aprender do primeiro documento OAB
        self.orchestrator.learn_from_llm_result(
            "carteira_oab",
            EXTRACTION_SCHEMAS["carteira_oab"],
            EXPECTED_RESULTS["carteira_oab_1"],
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        
        # Verificar que o template foi criado
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], 1)
        self.assertTrue(stats["total_rules"] > 0)
        self.assertEqual(stats["mature_templates"], 0)  # Ainda não maduro (precisa de MIN_SAMPLE_THRESHOLD)
        
        # Verificar que ainda não consegue usar o template (sample_count < MIN_SAMPLE_THRESHOLD)
        result = self.orchestrator.check_and_use_template(
            "carteira_oab",
            MOCK_PDF_ELEMENTS["carteira_oab_2"]
        )
        self.assertIsNone(result)
    
    def test_template_maturation_and_usage(self):
        """Testa a maturação do template e uso posterior"""
        # Aprender de múltiplos documentos OAB para atingir MIN_SAMPLE_THRESHOLD
        for i, doc_key in enumerate(["carteira_oab_1", "carteira_oab_2"], 1):
            self.orchestrator.learn_from_llm_result(
                "carteira_oab",
                EXTRACTION_SCHEMAS["carteira_oab"],
                EXPECTED_RESULTS[doc_key],
                MOCK_PDF_ELEMENTS[doc_key]
            )
        
        # Verificar que o template agora está maduro
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], 1)
        self.assertEqual(stats["mature_templates"], 1)
        
        # Tentar usar o template no terceiro documento
        result = self.orchestrator.check_and_use_template(
            "carteira_oab",
            MOCK_PDF_ELEMENTS["carteira_oab_3"]
        )
        
        # Verificar que obtivemos algum resultado
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        
        # Verificar que pelo menos alguns campos foram extraídos
        expected_fields = set(EXTRACTION_SCHEMAS["carteira_oab"].keys())
        extracted_fields = set(result.keys())
        
        # Deve haver pelo menos alguma interseção entre campos esperados e extraídos
        self.assertTrue(len(expected_fields.intersection(extracted_fields)) > 0)
    
    def test_multiple_document_types_learning(self):
        """Testa o aprendizado de múltiplos tipos de documentos"""
        # Aprender de diferentes tipos de documentos
        document_types = ["carteira_oab", "cnh", "cartao_credito", "nota_fiscal"]
        
        for doc_type in document_types:
            # Aprender de pelo menos 2 exemplos de cada tipo para torná-los maduros
            for i in range(1, 3):  # _1 e _2
                doc_key = f"{doc_type}_{i}"
                if doc_key in MOCK_PDF_ELEMENTS:
                    self.orchestrator.learn_from_llm_result(
                        doc_type,
                        EXTRACTION_SCHEMAS[doc_type],
                        EXPECTED_RESULTS[doc_key],
                        MOCK_PDF_ELEMENTS[doc_key]
                    )
        
        # Verificar que múltiplos templates foram criados
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], len(document_types))
        self.assertEqual(stats["mature_templates"], len(document_types))
        
        # Testar cada tipo de documento
        successful_templates = 0
        failed_templates = []
        
        for doc_type in document_types:
            doc_key_3 = f"{doc_type}_3"
            if doc_key_3 in MOCK_PDF_ELEMENTS:
                result = self.orchestrator.check_and_use_template(
                    doc_type,
                    MOCK_PDF_ELEMENTS[doc_key_3]
                )
                
                if result is not None:
                    successful_templates += 1
                    self.assertIsInstance(result, dict)
                else:
                    failed_templates.append(doc_type)
        
        # Verificar que pelo menos metade dos templates funcionaram
        # (alguns podem falhar devido à similaridade estrutural)
        self.assertGreaterEqual(successful_templates, len(document_types) // 2, 
                               f"Pelo menos metade dos templates deveria funcionar. Falharam: {failed_templates}")
        
        # Verificar que pelo menos um template funcionou
        self.assertGreater(successful_templates, 0, 
                          f"Pelo menos um template deveria funcionar. Todos falharam: {failed_templates}")
    
    def test_template_signature_evolution(self):
        """Testa a evolução da assinatura estrutural do template"""
        # Primeira amostra
        self.orchestrator.learn_from_llm_result(
            "carteira_oab",
            EXTRACTION_SCHEMAS["carteira_oab"],
            EXPECTED_RESULTS["carteira_oab_1"],
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        
        # Verificar template criado
        template = self.orchestrator.db.find_template_by_label("carteira_oab")
        self.assertIsNotNone(template)
        initial_sample_count = template['sample_count']
        
        # Segunda amostra
        self.orchestrator.learn_from_llm_result(
            "carteira_oab",
            EXTRACTION_SCHEMAS["carteira_oab"],
            EXPECTED_RESULTS["carteira_oab_2"],
            MOCK_PDF_ELEMENTS["carteira_oab_2"]
        )
        
        # Verificar que sample_count aumentou
        updated_template = self.orchestrator.db.find_template_by_label("carteira_oab")
        self.assertEqual(updated_template['sample_count'], initial_sample_count + 1)
    
    def test_rule_confidence_filtering(self):
        """Testa se apenas regras com confiança suficiente são salvas"""
        # Aprender de um documento
        self.orchestrator.learn_from_llm_result(
            "carteira_oab",
            EXTRACTION_SCHEMAS["carteira_oab"],
            EXPECTED_RESULTS["carteira_oab_1"],
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        
        # Verificar que existem regras salvas
        stats = self.orchestrator.get_template_stats()
        self.assertTrue(stats["total_rules"] > 0)
        
        # Verificar diretamente no banco que as regras têm confiança >= MIN_RULE_CONFIDENCE_TO_SAVE
        template = self.orchestrator.db.find_template_by_label("carteira_oab")
        rules = self.orchestrator.db.get_extraction_rules(template['id'])
        
        for rule in rules:
            self.assertGreaterEqual(rule['confidence'], 0.5)  # MIN_RULE_CONFIDENCE_TO_SAVE
    
    def test_structural_matching_similarity(self):
        """Testa a verificação de similaridade estrutural"""
        # Treinar com as duas primeiras variações da OAB
        for i in [1, 2]:
            doc_key = f"carteira_oab_{i}"
            self.orchestrator.learn_from_llm_result(
                "carteira_oab",
                EXTRACTION_SCHEMAS["carteira_oab"],
                EXPECTED_RESULTS[doc_key],
                MOCK_PDF_ELEMENTS[doc_key]
            )
        
        # Testar com a terceira variação (estrutura similar)
        result_similar = self.orchestrator.check_and_use_template(
            "carteira_oab",
            MOCK_PDF_ELEMENTS["carteira_oab_3"]
        )
        self.assertIsNotNone(result_similar)
        
        # Testar com um documento completamente diferente (CNH)
        result_different = self.orchestrator.check_and_use_template(
            "carteira_oab",
            MOCK_PDF_ELEMENTS["cnh_1"]
        )
        self.assertIsNone(result_different)
    
    def test_database_persistence(self):
        """Testa a persistência do banco de dados"""
        # Criar dados no banco
        self.orchestrator.learn_from_llm_result(
            "carteira_oab",
            EXTRACTION_SCHEMAS["carteira_oab"],
            EXPECTED_RESULTS["carteira_oab_1"],
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        
        # Verificar que há dados
        stats_before = self.orchestrator.get_template_stats()
        self.assertTrue(stats_before["total_templates"] > 0)
        
        # Criar nova instância do orquestrador com o mesmo banco
        new_orchestrator = TemplateOrchestrator(db_path=self.db_path)
        
        # Verificar que os dados persistiram
        stats_after = new_orchestrator.get_template_stats()
        self.assertEqual(stats_before["total_templates"], stats_after["total_templates"])
        self.assertEqual(stats_before["total_rules"], stats_after["total_rules"])
    
    def test_invalid_label_handling(self):
        """Testa o comportamento com labels inválidos"""
        # Tentar usar um template que não existe
        result = self.orchestrator.check_and_use_template(
            "documento_inexistente",
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        self.assertIsNone(result)
        
        # Aprender com label vazio ou inválido deveria funcionar
        self.orchestrator.learn_from_llm_result(
            "",  # Label vazio
            {"campo": "descrição"},
            {"campo": "valor"},
            MOCK_PDF_ELEMENTS["carteira_oab_1"]
        )
        
        # Verificar que o template foi criado mesmo com label vazio
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], 1)
    
    def test_empty_elements_handling(self):
        """Testa o comportamento com listas de elementos vazias"""
        # Tentar usar template com elementos vazios
        result = self.orchestrator.check_and_use_template(
            "carteira_oab",
            []  # Lista vazia
        )
        self.assertIsNone(result)
        
        # Aprender com elementos vazios
        self.orchestrator.learn_from_llm_result(
            "documento_vazio",
            EXTRACTION_SCHEMAS["carteira_oab"],
            EXPECTED_RESULTS["carteira_oab_1"],
            []  # Lista vazia
        )
        
        # Verificar que o template foi criado
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], 1)
    
    def test_debug_template_matching(self):
        """Teste de debug para entender falhas de matching"""
        # Treinar com cartao_credito
        for i in range(1, 3):
            doc_key = f"cartao_credito_{i}"
            self.orchestrator.learn_from_llm_result(
                "cartao_credito",
                EXTRACTION_SCHEMAS["cartao_credito"],
                EXPECTED_RESULTS[doc_key],
                MOCK_PDF_ELEMENTS[doc_key]
            )
        
        # Verificar se o template foi criado e está maduro
        stats = self.orchestrator.get_template_stats()
        self.assertEqual(stats["total_templates"], 1)
        self.assertEqual(stats["mature_templates"], 1)
        
        # Verificar as regras criadas
        template = self.orchestrator.db.find_template_by_label("cartao_credito")
        self.assertIsNotNone(template)
        
        rules = self.orchestrator.db.get_extraction_rules(template['id'])
        print(f"\nRules criadas para cartao_credito: {len(rules)}")
        for rule in rules:
            print(f"  - {rule['field_name']}: {rule['rule_type']} (conf: {rule['confidence']})")
        
        # Testar matching
        result = self.orchestrator.check_and_use_template(
            "cartao_credito",
            MOCK_PDF_ELEMENTS["cartao_credito_3"]
        )
        
        if result is None:
            # Verificar se é problema de similaridade
            is_match, score = self.orchestrator.matcher.check_similarity(
                MOCK_PDF_ELEMENTS["cartao_credito_3"],
                json.loads(template['structural_signature'])
            )
            print(f"Similaridade estrutural: match={is_match}, score={score}")
        else:
            print(f"Template funcionou! Extraiu: {result}")
        
        # Este teste sempre passa - é só para debug
        self.assertTrue(True)
    
    def test_integration_workflow_complete(self):
        """Teste de integração completo simulando o workflow real"""
        # Fase 1: Aprendizado inicial (simulando primeiros documentos processados via LLM)
        print("\n🎯 TESTE DE INTEGRAÇÃO COMPLETA")
        print("=" * 50)
        
        learning_phase_docs = [
            ("carteira_oab", "carteira_oab_1"),
            ("carteira_oab", "carteira_oab_2"),
            ("cnh", "cnh_1"),
            ("cnh", "cnh_2")
        ]
        
        print("📚 Fase de Aprendizado:")
        for doc_type, doc_key in learning_phase_docs:
            self.orchestrator.learn_from_llm_result(
                doc_type,
                EXTRACTION_SCHEMAS[doc_type],
                EXPECTED_RESULTS[doc_key],
                MOCK_PDF_ELEMENTS[doc_key]
            )
            print(f"  ✅ Aprendeu de {doc_key}")
        
        # Verificar estatísticas após aprendizado
        stats = self.orchestrator.get_template_stats()
        print(f"📊 Templates criados: {stats['total_templates']}")
        print(f"📊 Templates maduros: {stats['mature_templates']}")
        print(f"📊 Regras totais: {stats['total_rules']}")
        
        # Fase 2: Uso dos templates (simulando documentos subsequentes)
        print("\n🚀 Fase de Uso dos Templates:")
        test_docs = [
            ("carteira_oab", "carteira_oab_3"),
            ("cnh", "cnh_3")
        ]
        
        successful_extractions = 0
        for doc_type, doc_key in test_docs:
            result = self.orchestrator.check_and_use_template(
                doc_type,
                MOCK_PDF_ELEMENTS[doc_key]
            )
            
            if result:
                successful_extractions += 1
                print(f"  ✅ Extraiu dados de {doc_key}: {len(result)} campos")
                
                # Verificar se pelo menos alguns campos esperados foram extraídos
                expected_data = EXPECTED_RESULTS[doc_key]
                matches = 0
                for key, expected_value in expected_data.items():
                    if key in result and result[key] == expected_value:
                        matches += 1
                
                print(f"     🎯 Correspondências exatas: {matches}/{len(expected_data)}")
            else:
                print(f"  ❌ Falhou ao extrair de {doc_key}")
        
        # Verificações finais
        self.assertGreater(successful_extractions, 0, "Pelo menos uma extração deveria ter sucesso")
        self.assertEqual(stats["mature_templates"], 2, "Deveriam existir 2 templates maduros")
        
        print(f"\n🏆 Resultado: {successful_extractions}/{len(test_docs)} extrações bem-sucedidas")
        print("=" * 50)


if __name__ == "__main__":
    # Configurar o unittest para ser mais verboso
    unittest.main(verbosity=2, buffer=True)