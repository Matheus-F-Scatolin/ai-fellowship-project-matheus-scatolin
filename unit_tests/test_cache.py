"""
Unit tests para o CacheManager multi-level.
"""
import unittest
import tempfile
import shutil
import time
from unittest.mock import patch, MagicMock

# Import the modules we want to test
from core.store.caching import CacheManager, L1_MEMORY_MAX_SIZE
from core.store.key_gen import CacheKeyBuilder


class TestCacheKeyBuilder(unittest.TestCase):
    """Unit tests for CacheKeyBuilder class"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.builder = CacheKeyBuilder()
        self.pdf_bytes = b"test pdf content"
        self.label = "carteira_oab"
        self.schema = {"nome": "string", "cpf": "string", "numero": "string"}
        
    def test_generate_l1_l2_key_consistency(self):
        """Test that L1/L2 key generation is consistent for same inputs"""
        key1 = self.builder.generate_l1_l2_key(self.pdf_bytes, self.label, self.schema)
        key2 = self.builder.generate_l1_l2_key(self.pdf_bytes, self.label, self.schema)
        
        self.assertEqual(key1, key2)
        self.assertIn(self.label, key1)
        
    def test_generate_l1_l2_key_format(self):
        """Test that L1/L2 key has expected format"""
        key = self.builder.generate_l1_l2_key(self.pdf_bytes, self.label, self.schema)
        
        # Should have format: {pdf_hash}:{label}:{schema_hash}
        parts = key.split(':')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[1], self.label)
        
    def test_generate_l3_field_key_consistency(self):
        """Test that L3 field key generation is consistent"""
        field_name = "nome"
        key1 = self.builder.generate_l3_field_key(self.pdf_bytes, self.label, field_name)
        key2 = self.builder.generate_l3_field_key(self.pdf_bytes, self.label, field_name)
        
        self.assertEqual(key1, key2)
        self.assertTrue(key1.startswith("field:"))
        self.assertIn(self.label, key1)
        self.assertIn(field_name, key1)
        
    def test_different_inputs_generate_different_keys(self):
        """Test that different inputs generate different keys"""
        key1 = self.builder.generate_l1_l2_key(self.pdf_bytes, self.label, self.schema)
        key2 = self.builder.generate_l1_l2_key(b"different content", self.label, self.schema)
        
        self.assertNotEqual(key1, key2)


class TestCacheManager(unittest.TestCase):
    """Unit tests for CacheManager class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        # Store original cache directory
        cls.original_cache_dir = "./persistent_data/disk_cache"
    
    @classmethod
    def tearDownClass(cls):
        """Clean up class-level fixtures."""
        # Ensure the main cache directory exists and is clean
        import os
        if os.path.exists(cls.original_cache_dir):
            # Clear any test data that might have leaked
            try:
                from diskcache import Cache
                main_cache = Cache(cls.original_cache_dir)
                # Only clear if there are test-related keys
                for key in list(main_cache):
                    if isinstance(key, str) and "test" in key.lower():
                        del main_cache[key]
                main_cache.close()
                print(f"🧹 Cache principal verificado e limpo: {cls.original_cache_dir}")
            except Exception as e:
                print(f"⚠️  Aviso durante limpeza do cache: {e}")
                pass  # Ignore errors during cleanup
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for cache tests
        self.temp_dir = tempfile.mkdtemp()
        
        # Patch the cache directory to use temp directory for the entire test
        self.cache_dir_patcher = patch('core.store.caching.L2_CACHE_DIR', self.temp_dir)
        self.cache_dir_patcher.start()
        
        # Now create the cache manager with the patched directory
        self.cache = CacheManager()
            
        # Test data
        self.pdf_bytes = b"test pdf content for caching"
        self.label = "carteira_oab"
        self.schema = {"nome": "string", "cpf": "string", "numero": "string"}
        self.result_data = {"nome": "João Silva", "cpf": "123.456.789-00", "numero": "123456"}
        self.exec_metadata = {"model": "test", "execution_time": 1.5, "timestamp": time.time()}
        
    def tearDown(self):
        """Clean up after each test."""
        # Stop the patcher
        self.cache_dir_patcher.stop()
        
        # Close the cache properly
        if hasattr(self.cache, 'l2_disk_cache'):
            self.cache.l2_disk_cache.close()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_initialization(self):
        """Test CacheManager initialization"""
        self.assertIsInstance(self.cache.l1_memory_cache, dict)
        self.assertIsInstance(self.cache.key_builder, CacheKeyBuilder)
        self.assertIn('l1_hits', self.cache.stats)
        self.assertIn('l2_hits', self.cache.stats)
        self.assertIn('l3_hits', self.cache.stats)
        self.assertIn('misses', self.cache.stats)
        self.assertIn('total_requests', self.cache.stats)
        
    def test_cache_miss_initial(self):
        """Test cache miss on first access"""
        result = self.cache.get(self.pdf_bytes, self.label, self.schema)
        
        self.assertIsNone(result)
        self.assertEqual(self.cache.stats['misses'], 1)
        self.assertEqual(self.cache.stats['total_requests'], 1)
        self.assertEqual(self.cache.stats['l1_hits'], 0)
        
    def test_set_and_get_l1_hit(self):
        """Test setting data and getting L1 cache hit"""
        # Store data in cache
        self.cache.set(self.pdf_bytes, self.label, self.schema, self.result_data, self.exec_metadata)
        
        # Retrieve data - should be L1 hit
        result = self.cache.get(self.pdf_bytes, self.label, self.schema)
        
        self.assertIsNotNone(result)
        self.assertEqual(self.cache.stats['l1_hits'], 1)
        self.assertEqual(result['_cache_info']['source'], 'L1_MEMORY')
        self.assertEqual(result['data'], self.result_data)
        self.assertEqual(result['metadata'], self.exec_metadata)
        
    def test_l1_lru_eviction(self):
        """Test L1 LRU eviction when max size exceeded"""
        # Fill L1 cache beyond max size
        for i in range(L1_MEMORY_MAX_SIZE + 5):
            test_bytes = f"test content {i}".encode()
            test_schema = {"field": f"value_{i}"}
            test_data = {"field": f"result_{i}"}
            
            self.cache.set(test_bytes, f"label_{i}", test_schema, test_data, {})
        
        # L1 should not exceed max size
        self.assertLessEqual(len(self.cache.l1_memory_cache), L1_MEMORY_MAX_SIZE)
        
    def test_l3_partial_hit(self):
        """Test L3 partial cache hit functionality"""
        # Store data first
        self.cache.set(self.pdf_bytes, self.label, self.schema, self.result_data, self.exec_metadata)
        
        # Clear L1 to force L2/L3 lookup
        self.cache.l1_memory_cache.clear()
        
        # Request with partial schema (some fields exist, some don't)
        partial_schema = {"nome": "string", "endereco": "string", "cpf": "string"}
        result = self.cache.get(self.pdf_bytes, self.label, partial_schema)
        
        # Should get L3 partial hit
        self.assertIsNotNone(result)
        self.assertEqual(result['_cache_info']['source'], 'L3_PARTIAL')
        self.assertEqual(result['_cache_info']['fields_found'], 2)  # nome, cpf
        self.assertEqual(result['_cache_info']['fields_requested'], 3)
        self.assertEqual(result['data']['nome'], 'João Silva')
        self.assertEqual(result['data']['cpf'], '123.456.789-00')
        self.assertIsNone(result['data']['endereco'])
        
    def test_get_stats(self):
        """Test get_stats method returns correct information"""
        stats = self.cache.get_stats()
        
        self.assertIn('stats', stats)
        self.assertIn('l1_memory_size', stats)
        self.assertIn('l2_disk_size_mb', stats)
        self.assertIsInstance(stats['l1_memory_size'], int)
        self.assertIsInstance(stats['l2_disk_size_mb'], (int, float))
        
    def test_l2_promotion_to_l1(self):
        """Test that L2 hits are promoted to L1"""
        # Store data
        self.cache.set(self.pdf_bytes, self.label, self.schema, self.result_data, self.exec_metadata)
        
        # Clear L1 to simulate L2 only storage
        self.cache.l1_memory_cache.clear()
        
        # Get data - should be L2 hit and promote to L1
        result = self.cache.get(self.pdf_bytes, self.label, self.schema)
        
        self.assertIsNotNone(result)
        self.assertEqual(self.cache.stats['l2_hits'], 1)
        self.assertEqual(result['_cache_info']['source'], 'L2_DISK')
        
        # Verify promotion to L1
        key = self.cache.key_builder.generate_l1_l2_key(self.pdf_bytes, self.label, self.schema)
        self.assertIn(key, self.cache.l1_memory_cache)
        
    def test_l3_fields_storage(self):
        """Test that individual fields are stored for L3 cache"""
        # Store data with some None values
        data_with_none = {"nome": "João Silva", "cpf": None, "numero": "123456"}
        self.cache.set(self.pdf_bytes, self.label, self.schema, data_with_none, self.exec_metadata)
        
        # Check that only non-None fields are stored in L3
        nome_key = self.cache.key_builder.generate_l3_field_key(self.pdf_bytes, self.label, "nome")
        cpf_key = self.cache.key_builder.generate_l3_field_key(self.pdf_bytes, self.label, "cpf")
        numero_key = self.cache.key_builder.generate_l3_field_key(self.pdf_bytes, self.label, "numero")
        
        self.assertEqual(self.cache.l2_disk_cache.get(nome_key), "João Silva")
        self.assertIsNone(self.cache.l2_disk_cache.get(cpf_key))  # Should not be stored
        self.assertEqual(self.cache.l2_disk_cache.get(numero_key), "123456")
        
    def test_cache_info_metadata(self):
        """Test that cache info metadata is properly added"""
        self.cache.set(self.pdf_bytes, self.label, self.schema, self.result_data, self.exec_metadata)
        result = self.cache.get(self.pdf_bytes, self.label, self.schema)
        
        self.assertIn('_cache_info', result)
        self.assertIn('source', result['_cache_info'])
        self.assertEqual(result['_cache_info']['source'], 'L1_MEMORY')
        
    def test_timestamp_in_cache_entry(self):
        """Test that timestamp is added to cache entries"""
        before_time = time.time()
        self.cache.set(self.pdf_bytes, self.label, self.schema, self.result_data, self.exec_metadata)
        after_time = time.time()
        
        # Get from L1
        result = self.cache.get(self.pdf_bytes, self.label, self.schema)
        
        self.assertIn('timestamp', result)
        self.assertGreaterEqual(result['timestamp'], before_time)
        self.assertLessEqual(result['timestamp'], after_time)


if __name__ == "__main__":
    unittest.main()