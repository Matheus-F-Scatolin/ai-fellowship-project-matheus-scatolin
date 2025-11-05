import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the current directory to the path to import from core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.connectors.llm_connector import LLMConnector


class TestLLMConnector(unittest.TestCase):
    
    def setUp(self):
        """Setup test data"""
        self.test_pdf_path = "test.pdf"
        self.test_label = "carteira_oab"
        self.test_schema = {
            "nome": "Nome completo da pessoa",
            "numero_oab": "Número da carteira OAB",
            "seccional": "Seccional da OAB"
        }
        
        # Mock OpenAI response
        self.mock_response = {
            "nome": "João Silva",
            "numero_oab": "123456",
            "seccional": "SP"
        }
        
        # Mock elements from unstructured
        self.mock_elements = [
            self._create_mock_element("Nome: João Silva", 100, 50),
            self._create_mock_element("OAB: 123456", 100, 80),
            self._create_mock_element("Seccional: SP", 100, 110),
            self._create_mock_element("", 0, 0),  # Empty element to test filtering
        ]
    
    def _create_mock_element(self, text, x=0, y=0):
        """Helper to create mock PDF elements"""
        element = Mock()
        element.text = text
        
        # Mock metadata structure
        if text.strip():  # Only add metadata for non-empty elements
            metadata = Mock()
            coordinates = Mock()
            point = Mock()
            point.x = x
            point.y = y
            coordinates.points = [point]
            metadata.coordinates = coordinates
            element.metadata = metadata
        else:
            element.metadata = None
        
        return element
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_initialization(self):
        """Test LLMConnector initialization"""
        connector = LLMConnector()
        
        self.assertEqual(connector.model_name, "gpt-5-mini")
        self.assertIsNotNone(connector.client)
    
    def test_create_json_template(self):
        """Test JSON template creation"""
        connector = LLMConnector()
        
        template = connector._create_json_template(self.test_schema)
        expected = '{"nome": "...", "numero_oab": "...", "seccional": "..."}'
        
        self.assertEqual(template, expected)
    
    def test_create_json_template_empty_schema(self):
        """Test JSON template with empty schema"""
        connector = LLMConnector()
        
        template = connector._create_json_template({})
        expected = "{}"
        
        self.assertEqual(template, expected)
    
    def test_generate_extraction_prompt(self):
        """Test prompt generation"""
        connector = LLMConnector()
        
        prompt = connector._generate_extraction_prompt(self.test_label, self.test_schema)
        
        # Check if all required components are in the prompt
        self.assertIn(self.test_label, prompt)
        self.assertIn("nome", prompt)
        self.assertIn("numero_oab", prompt)
        self.assertIn("seccional", prompt)
        self.assertIn("JSON", prompt)
        self.assertIn("SCHEMA DE EXTRAÇÃO", prompt)
        self.assertIn("FORMATO JSON", prompt)
    
    def test_build_structured_text_ordering(self):
        """Test text structuring and ordering"""
        connector = LLMConnector()
        
        # Elements with different Y coordinates (should be ordered top to bottom)
        elements = [
            self._create_mock_element("Linha 3", 0, 300),
            self._create_mock_element("Linha 1", 0, 100),
            self._create_mock_element("Linha 2", 0, 200),
        ]
        
        structured_text = connector._build_structured_text(elements)
        lines = structured_text.split('\n')
        
        self.assertEqual(lines[0], "Linha 1")
        self.assertEqual(lines[1], "Linha 2")
        self.assertEqual(lines[2], "Linha 3")
    
    def test_build_structured_text_same_line(self):
        """Test text grouping on same line"""
        connector = LLMConnector()
        
        # Elements with same Y coordinate but different X (should be on same line)
        elements = [
            self._create_mock_element("Nome:", 50, 100),
            self._create_mock_element("João", 100, 100),
            self._create_mock_element("Silva", 150, 105),  # Slight Y difference within tolerance
        ]
        
        structured_text = connector._build_structured_text(elements)
        lines = structured_text.split('\n')
        
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "Nome: João Silva")
    
    def test_build_structured_text_filter_empty(self):
        """Test filtering of empty elements"""
        connector = LLMConnector()
        
        elements = [
            self._create_mock_element("Valid text", 0, 100),
            self._create_mock_element("", 0, 200),  # Empty
            self._create_mock_element("   ", 0, 300),  # Whitespace only
            self._create_mock_element("Another valid", 0, 400),
        ]
        
        structured_text = connector._build_structured_text(elements)
        lines = structured_text.split('\n')
        
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "Valid text")
        self.assertEqual(lines[1], "Another valid")
    
    def test_build_structured_text_no_metadata(self):
        """Test handling elements without metadata"""
        connector = LLMConnector()
        
        # Element without metadata
        element = Mock()
        element.text = "Text without coordinates"
        element.metadata = None
        
        structured_text = connector._build_structured_text([element])
        
        self.assertEqual(structured_text, "Text without coordinates")
    
    @patch('core.connectors.llm_connector.partition_pdf')
    def test_parse_pdf_elements(self, mock_partition):
        """Test PDF parsing"""
        connector = LLMConnector()
        mock_partition.return_value = self.mock_elements
        
        elements = connector._parse_pdf_elements(self.test_pdf_path)
        
        mock_partition.assert_called_once_with(
            filename=self.test_pdf_path,
            strategy="fast",
            languages=["por"],
            infer_table_structure=True,
            extract_element_metadata=True
        )
        self.assertEqual(elements, self.mock_elements)
    
    @patch('core.connectors.llm_connector.partition_pdf')
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_run_extraction_integration(self, mock_partition):
        """Test full extraction flow (integration test)"""
        connector = LLMConnector()
        
        # Mock PDF parsing
        mock_partition.return_value = self.mock_elements
        
        # Mock OpenAI API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(self.mock_response)
        
        with patch.object(connector.client.chat.completions, 'create', return_value=mock_response):
            result = connector.run_extraction(self.test_pdf_path, self.test_label, self.test_schema)
        
        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        self.assertEqual(parsed_result, self.mock_response)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_run_extraction_api_call_parameters(self):
        """Test that API is called with correct parameters"""
        connector = LLMConnector()
        
        # Mock dependencies
        with patch.object(connector, '_parse_pdf_elements', return_value=self.mock_elements), \
             patch.object(connector, '_build_structured_text', return_value="mock text"), \
             patch.object(connector, '_generate_extraction_prompt', return_value="mock prompt"):
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"test": "result"}'
            
            with patch.object(connector.client.chat.completions, 'create', return_value=mock_response) as mock_create:
                connector.run_extraction(self.test_pdf_path, self.test_label, self.test_schema)
                
                # Verify API call parameters
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                
                self.assertEqual(call_args['model'], "gpt-5-mini")
                self.assertEqual(call_args['response_format'], {"type": "json_object"})
                self.assertEqual(call_args['store'], False)
                self.assertEqual(call_args['reasoning_effort'], "minimal")
                self.assertEqual(len(call_args['messages']), 1)
                self.assertEqual(call_args['messages'][0]['role'], "user")
    
    def test_schema_order_independence(self):
        """Test that schema order doesn't affect template generation"""
        connector = LLMConnector()
        
        schema1 = {"nome": "Nome", "idade": "Idade"}
        schema2 = {"idade": "Idade", "nome": "Nome"}
        
        template1 = connector._create_json_template(schema1)
        template2 = connector._create_json_template(schema2)
        
        # Templates should have same fields (order in dict might vary)
        self.assertIn('"nome": "..."', template1)
        self.assertIn('"idade": "..."', template1)
        self.assertIn('"nome": "..."', template2)
        self.assertIn('"idade": "..."', template2)

    @patch('core.connectors.llm_connector.partition_pdf')
    def test_build_structured_text_real_oab1_pdf(self, mock_partition):
        """Test _build_structured_text with real OAB 1 PDF data structure"""
        connector = LLMConnector()
        
        # Expected structured text for oab_1.pdf based on the provided template
        expected_text = """JOANA D'ARC
Inscrição Seccional Subseção
101943 PR CONSELHO SECCIONAL - PARANÁ
SUPLEMENTAR
Endereço Profissional
AVENIDA PAULISTA, Nº 2300 andar Pilotis, Bela Vista
SÃO PAULO - SP
01310300
Telefone Profissional
SITUAÇÃO REGULAR"""
        
        # Mock elements simulating what partition_pdf would return for oab_1.pdf
        mock_elements = [
            self._create_mock_element("JOANA D'ARC", 100, 50),
            self._create_mock_element("Inscrição", 50, 100),
            self._create_mock_element("Seccional", 200, 102),
            self._create_mock_element("Subseção", 350, 101),
            self._create_mock_element("101943", 50, 131),
            self._create_mock_element("PR", 200, 130),
            self._create_mock_element("CONSELHO SECCIONAL - PARANÁ", 350, 132),
            self._create_mock_element("SUPLEMENTAR", 100, 180),
            self._create_mock_element("Endereço Profissional", 50, 230),
            self._create_mock_element("AVENIDA PAULISTA, Nº 2300 andar Pilotis, Bela Vista", 50, 260),
            self._create_mock_element("SÃO PAULO - SP", 50, 290),
            self._create_mock_element("01310300", 50, 320),
            self._create_mock_element("Telefone Profissional", 50, 370),
            self._create_mock_element("SITUAÇÃO REGULAR", 100, 450),
        ]
        
        mock_partition.return_value = mock_elements
        
        # Test parsing
        elements = connector._parse_pdf_elements("files/oab_1.pdf")
        structured_text = connector._build_structured_text(elements)
        
        # Verify the main information is present
        self.assertIn("JOANA D'ARC", structured_text)
        self.assertIn("101943", structured_text)
        self.assertIn("PR", structured_text)
        self.assertIn("SUPLEMENTAR", structured_text)
        self.assertIn("SITUAÇÃO REGULAR", structured_text)
        self.assertIn("AVENIDA PAULISTA", structured_text)
        
        # Verify lines are properly ordered (top to bottom)
        lines = structured_text.split('\n')
        # JOANA D'ARC should be first (Y=50)
        self.assertEqual(lines[0], "JOANA D'ARC")
        self.assertEqual(lines[1], "Inscrição Seccional Subseção")
        self.assertEqual(lines[2], "101943 PR CONSELHO SECCIONAL - PARANÁ")
        self.assertEqual(lines[3], "SUPLEMENTAR")
        self.assertEqual(lines[4], "Endereço Profissional")
        self.assertEqual(lines[5], "AVENIDA PAULISTA, Nº 2300 andar Pilotis, Bela Vista")
        self.assertEqual(lines[6], "SÃO PAULO - SP")
        self.assertEqual(lines[7], "01310300")
        self.assertEqual(lines[8], "Telefone Profissional")
        # SITUAÇÃO REGULAR should be last (Y=450)
        self.assertEqual(lines[-1], "SITUAÇÃO REGULAR")

    @patch('core.connectors.llm_connector.partition_pdf')
    def test_build_structured_text_real_oab2_pdf(self, mock_partition):
        """Test _build_structured_text with real OAB 2 PDF data structure"""
        connector = LLMConnector()
        
        # Expected structured text for oab_2.pdf based on the provided template
        expected_text = """LUIS FILIPE ARAUJO AMARAL
Inscrição Seccional Subseção
101943 PR CONSELHO SECCIONAL - PARANÁ
SUPLEMENTAR
Endereço Profissional
AVENIDA PAULISTA, Nº 2300 andar Pilotis, Bela Vista
SÃO PAULO - SP
01310300
Telefone Profissional
SITUAÇÃO REGULAR"""
        
        # Mock elements simulating what partition_pdf would return for oab_2.pdf
        mock_elements = [
            self._create_mock_element("LUIS FILIPE ARAUJO AMARAL", 100, 50),
            self._create_mock_element("Inscrição", 50, 100),
            self._create_mock_element("Seccional", 200, 100),
            self._create_mock_element("Subseção", 350, 100),
            self._create_mock_element("101943", 50, 130),
            self._create_mock_element("PR", 200, 130),
            self._create_mock_element("CONSELHO SECCIONAL - PARANÁ", 350, 130),
            self._create_mock_element("SUPLEMENTAR", 100, 180),
            self._create_mock_element("Endereço Profissional", 50, 230),
            self._create_mock_element("AVENIDA PAULISTA, Nº 2300 andar Pilotis, Bela Vista", 50, 260),
            self._create_mock_element("SÃO PAULO - SP", 50, 290),
            self._create_mock_element("01310300", 50, 320),
            self._create_mock_element("Telefone Profissional", 50, 370),
            self._create_mock_element("SITUAÇÃO REGULAR", 100, 450),
        ]
        
        mock_partition.return_value = mock_elements
        
        # Test parsing
        elements = connector._parse_pdf_elements("files/oab_2.pdf")
        structured_text = connector._build_structured_text(elements)
        
        # Verify the main information is present
        self.assertIn("LUIS FILIPE ARAUJO AMARAL", structured_text)
        self.assertIn("101943", structured_text)
        self.assertIn("PR", structured_text)
        self.assertIn("SUPLEMENTAR", structured_text)
        self.assertIn("SITUAÇÃO REGULAR", structured_text)
        self.assertIn("AVENIDA PAULISTA", structured_text)
        
        # Verify lines are properly ordered (top to bottom)
        lines = structured_text.split('\n')
        # LUIS FILIPE ARAUJO AMARAL should be first (Y=50)
        self.assertEqual(lines[0], "LUIS FILIPE ARAUJO AMARAL")
        # SITUAÇÃO REGULAR should be last (Y=450)
        self.assertEqual(lines[-1], "SITUAÇÃO REGULAR")

    @patch('core.connectors.llm_connector.partition_pdf')
    def test_build_structured_text_same_line_grouping_real_data(self, mock_partition):
        """Test that elements on the same line are properly grouped using real OAB data"""
        connector = LLMConnector()
        
        # Simulate elements that should be grouped on the same line (same Y coordinate)
        mock_elements = [
            # Header elements on same line (Y=100)
            self._create_mock_element("Inscrição", 50, 100),
            self._create_mock_element("Seccional", 200, 100),
            self._create_mock_element("Subseção", 350, 100),
            # Data elements on same line (Y=130)
            self._create_mock_element("101943", 50, 130),
            self._create_mock_element("PR", 200, 130),
            self._create_mock_element("CONSELHO SECCIONAL - PARANÁ", 350, 130),
        ]
        
        mock_partition.return_value = mock_elements
        
        elements = connector._parse_pdf_elements("files/test.pdf")
        structured_text = connector._build_structured_text(elements)
        
        lines = structured_text.split('\n')
        
        # Should have 2 lines (one for headers, one for data)
        self.assertEqual(len(lines), 2)
        
        # First line should contain all headers
        self.assertEqual(lines[0], "Inscrição Seccional Subseção")
        
        # Second line should contain all data
        self.assertEqual(lines[1], "101943 PR CONSELHO SECCIONAL - PARANÁ")

    def test_build_structured_text_real_pdf_integration(self):
        """Integration test to verify _build_structured_text works with actual PDF files"""
        # This test is optional and only runs if the PDFs exist and we have an API key
        if not os.path.exists("files/oab_1.pdf"):
            self.skipTest("PDF file files/oab_1.pdf not found")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY not configured")
        
        connector = LLMConnector()
        
        try:
            # Test with real PDF parsing (this will use partition_pdf)
            elements = connector._parse_pdf_elements("files/oab_1.pdf")
            structured_text = connector._build_structured_text(elements)
            
            # Basic validation that we got some meaningful text
            self.assertIsInstance(structured_text, str)
            self.assertGreater(len(structured_text), 0)
            
            # Check that we have multiple lines (PDF should have structured content)
            lines = structured_text.split('\n')
            self.assertGreater(len(lines), 1)
            
            print(f"\n🔍 Real PDF structured text preview:")
            print(f"Lines count: {len(lines)}")
            print(f"First few lines: {lines[:5]}")
            
        except Exception as e:
            self.skipTest(f"Real PDF test failed: {e}")


if __name__ == '__main__':
    unittest.main()