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


if __name__ == '__main__':
    unittest.main()