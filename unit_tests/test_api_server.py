import unittest
import json
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import pytest

# Import the modules we want to test
from core.api_server import app, ExtractionPipeline, ExtractionResponse, HealthResponse, lifespan


class TestExtractionPipeline(unittest.TestCase):
    """Unit tests for the ExtractionPipeline class"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.pipeline = ExtractionPipeline()
        
    def test_singleton_pattern(self):
        """Test that ExtractionPipeline follows singleton pattern"""
        pipeline1 = ExtractionPipeline()
        pipeline2 = ExtractionPipeline()
        
        # Both instances should be the same object
        self.assertIs(pipeline1, pipeline2)
        
    def test_initialization(self):
        """Test pipeline initialization"""
        pipeline = ExtractionPipeline()
        
        # Should have stats attribute
        self.assertTrue(hasattr(pipeline, 'stats'))
        self.assertIn('start_time', pipeline.stats)
        self.assertTrue(hasattr(pipeline, 'initialized'))
        self.assertTrue(pipeline.initialized)
        
    def test_extract_method(self):
        """Test the extract method returns expected structure"""
        pdf_bytes = b"fake pdf content"
        label = "test_label"
        schema = {"field1": "description1", "field2": "description2"}
        
        result = self.pipeline.extract(pdf_bytes, label, schema)
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        
        # Should contain expected fields
        self.assertIn("field_1", result)
        self.assertIn("field_2", result)
        self.assertIn("_pipeline", result)
        
        # Check pipeline metadata
        self.assertEqual(result["_pipeline"]["method"], "mock")
        self.assertIsInstance(result["_pipeline"]["time"], (int, float))


class TestPydanticModels(unittest.TestCase):
    """Unit tests for Pydantic models"""
    
    def test_extraction_response_model(self):
        """Test ExtractionResponse model validation"""
        data = {
            "success": True,
            "data": {"field1": "value1"},
            "metadata": {"time": 0.5}
        }
        
        response = ExtractionResponse(**data)
        
        self.assertTrue(response.success)
        self.assertEqual(response.data, {"field1": "value1"})
        self.assertEqual(response.metadata, {"time": 0.5})
        
    def test_health_response_model(self):
        """Test HealthResponse model validation"""
        data = {
            "status": "healthy",
            "version": "1.0-test"
        }
        
        response = HealthResponse(**data)
        
        self.assertEqual(response.status, "healthy")
        self.assertEqual(response.version, "1.0-test")


class TestAPIEndpoints(unittest.TestCase):
    """Unit tests for FastAPI endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.client = TestClient(app)
        
    def test_root_endpoint(self):
        """Test root endpoint (/"""
        response = self.client.get("/")
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["name"], "PDF Data Extraction API")
        self.assertEqual(data["version"], "1.0-custom")
        self.assertEqual(data["status"], "running")
        self.assertIn("docs", data)
        
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0-custom")
        
    def test_stats_endpoint(self):
        """Test stats endpoint"""
        response = self.client.get("/stats")
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["message"], "stats_not_implemented_yet")
        
    def test_extract_endpoint_success(self):
        """Test successful extraction endpoint"""
        # Create fake PDF file
        pdf_content = b"fake pdf content for testing"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        # Form data
        form_data = {
            "label": "test_document",
            "extraction_schema": json.dumps({
                "nome": "Nome completo",
                "idade": "Idade da pessoa"
            })
        }
        
        response = self.client.post("/extract", files=files, data=form_data)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        self.assertIn("metadata", data)
        
        # Check metadata structure
        metadata = data["metadata"]
        self.assertIn("request_time", metadata)
        self.assertIn("file_name", metadata)
        self.assertIn("file_size", metadata)
        self.assertIn("label", metadata)
        self.assertIn("schema_fields", metadata)
        
        self.assertEqual(metadata["file_name"], "test.pdf")
        self.assertEqual(metadata["file_size"], len(pdf_content))
        self.assertEqual(metadata["label"], "test_document")
        
    def test_extract_endpoint_invalid_json_schema(self):
        """Test extraction endpoint with invalid JSON schema"""
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        # Invalid JSON schema
        form_data = {
            "label": "test_document",
            "extraction_schema": "invalid json schema"
        }
        
        response = self.client.post("/extract", files=files, data=form_data)
        
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("JSON válido", data["detail"])
        
    def test_extract_endpoint_missing_file(self):
        """Test extraction endpoint without file"""
        form_data = {
            "label": "test_document",
            "extraction_schema": json.dumps({"field": "description"})
        }
        
        response = self.client.post("/extract", data=form_data)
        
        self.assertEqual(response.status_code, 422)  # Validation error
        
    def test_extract_endpoint_missing_label(self):
        """Test extraction endpoint without label"""
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        form_data = {
            "extraction_schema": json.dumps({"field": "description"})
        }
        
        response = self.client.post("/extract", files=files, data=form_data)
        
        self.assertEqual(response.status_code, 422)  # Validation error
        
    def test_extract_endpoint_missing_schema(self):
        """Test extraction endpoint without extraction schema"""
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        form_data = {
            "label": "test_document"
        }
        
        response = self.client.post("/extract", files=files, data=form_data)
        
        self.assertEqual(response.status_code, 422)  # Validation error
        
    @patch('core.api_server.pipeline.extract')
    def test_extract_endpoint_internal_error(self, mock_extract):
        """Test extraction endpoint when pipeline raises exception"""
        # Mock pipeline to raise exception
        mock_extract.side_effect = Exception("Pipeline error")
        
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        form_data = {
            "label": "test_document",
            "extraction_schema": json.dumps({"field": "description"})
        }
        
        response = self.client.post("/extract", files=files, data=form_data)
        
        self.assertEqual(response.status_code, 500)
        
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("Erro interno na extração", data["detail"])


class TestAPIIntegration(unittest.TestCase):
    """Integration tests for the API"""
    
    def setUp(self):
        """Set up test client"""
        self.client = TestClient(app)
        
    def test_full_extraction_workflow(self):
        """Test complete extraction workflow"""
        # Prepare test data
        pdf_content = b"Sample PDF content for integration test"
        schema = {
            "nome": "Nome completo da pessoa",
            "cpf": "CPF do documento",
            "endereco": "Endereço residencial"
        }
        
        files = {"file": ("integration_test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        form_data = {
            "label": "integration_test",
            "extraction_schema": json.dumps(schema)
        }
        
        # Make request
        response = self.client.post("/extract", files=files, data=form_data)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verify structure
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        self.assertIn("metadata", data)
        
        # Verify data separation (no fields starting with _)
        extracted_data = data["data"]
        for key in extracted_data.keys():
            self.assertFalse(key.startswith("_"), f"Data field {key} should not start with _")
            
        # Verify metadata contains pipeline info
        metadata = data["metadata"]
        self.assertIn("_pipeline", metadata)
        self.assertEqual(metadata["label"], "integration_test")
        self.assertEqual(len(metadata["schema_fields"]), 3)
        self.assertIn("nome", metadata["schema_fields"])
        self.assertIn("cpf", metadata["schema_fields"])
        self.assertIn("endereco", metadata["schema_fields"])


class TestLifespanEvents(unittest.TestCase):
    """Unit tests for Lifespan events"""
    
    @patch('builtins.print')
    def test_lifespan_context_manager(self, mock_print):
        """Test lifespan context manager startup and shutdown"""
        # This test simulates what FastAPI does internally with lifespan
        import asyncio
        
        async def test_lifespan():
            async with lifespan(app) as context:
                # During this time, startup should have been called
                pass
            # After exiting, shutdown should have been called
        
        # Run the async context manager
        asyncio.run(test_lifespan())
        
        # Verify both startup and shutdown messages were printed
        expected_calls = [
            unittest.mock.call("--- API Iniciada (Versão Customizada) ---"),
            unittest.mock.call("--- API Encerrada ---")
        ]
        mock_print.assert_has_calls(expected_calls)


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling scenarios"""
    
    def setUp(self):
        """Set up test client"""
        self.client = TestClient(app)
        
    def test_invalid_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = self.client.get("/nonexistent")
        self.assertEqual(response.status_code, 404)
        
    def test_wrong_http_method(self):
        """Test using wrong HTTP method"""
        response = self.client.get("/extract")  # Should be POST
        self.assertEqual(response.status_code, 405)  # Method not allowed
        
    def test_malformed_request_data(self):
        """Test with malformed multipart data"""
        # Attempt to send JSON instead of form data
        response = self.client.post(
            "/extract", 
            json={"label": "test", "schema": "{}"}
        )
        self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)