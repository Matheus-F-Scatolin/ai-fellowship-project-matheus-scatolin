import unittest
import hashlib
import json
from core.store.key_gen import CacheKeyBuilder


class TestCacheKeyBuilder(unittest.TestCase):
    
    def setUp(self):
        """Setup test data"""
        self.pdf_content1 = b"PDF content example 1"
        self.pdf_content2 = b"PDF content example 2"
        self.label = "carteira_oab"
        self.schema1 = {"nome": "str", "numero": "str"}
        self.schema2 = {"numero": "str", "nome": "str"}  # Same content, different order
        self.field_name = "nome"
    
    def test_generate_l1_l2_key_format(self):
        """Test L1/L2 key format"""
        key = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content1, self.label, self.schema1
        )
        
        # Should have 3 parts separated by ':'
        parts = key.split(':')
        self.assertEqual(len(parts), 3)
        
        # Each part should be a valid hex string (64 chars for SHA256)
        self.assertEqual(len(parts[0]), 64)  # PDF hash
        self.assertEqual(parts[1], self.label)  # Label
        self.assertEqual(len(parts[2]), 64)  # Schema hash
    
    def test_generate_l3_field_key_format(self):
        """Test L3 field key format"""
        key = CacheKeyBuilder.generate_l3_field_key(
            self.pdf_content1, self.label, self.field_name
        )
        
        # Should start with 'field:' and have 4 parts
        self.assertTrue(key.startswith('field:'))
        parts = key.split(':')
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], 'field')
        self.assertEqual(len(parts[1]), 64)  # PDF hash
        self.assertEqual(parts[2], self.label)
        self.assertEqual(parts[3], self.field_name)
    
    def test_deterministic_keys(self):
        """Test that same inputs generate same keys"""
        key1 = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content1, self.label, self.schema1
        )
        key2 = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content1, self.label, self.schema1
        )
        
        self.assertEqual(key1, key2)
    
    def test_schema_order_independence(self):
        """Test that schema order doesn't affect key generation"""
        key1 = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content1, self.label, self.schema1
        )
        key2 = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content1, self.label, self.schema2
        )
        
        self.assertEqual(key1, key2)
    
    def test_different_inputs_generate_different_keys(self):
        """Test that different inputs generate different keys"""
        key1 = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content1, self.label, self.schema1
        )
        key2 = CacheKeyBuilder.generate_l1_l2_key(
            self.pdf_content2, self.label, self.schema1
        )
        
        self.assertNotEqual(key1, key2)
    
    def test_hash_content(self):
        """Test content hashing"""
        hash1 = CacheKeyBuilder._hash_content(self.pdf_content1)
        hash2 = CacheKeyBuilder._hash_content(self.pdf_content1)
        hash3 = CacheKeyBuilder._hash_content(self.pdf_content2)
        
        # Same content should generate same hash
        self.assertEqual(hash1, hash2)
        # Different content should generate different hash
        self.assertNotEqual(hash1, hash3)
        # Should be valid SHA256 (64 hex chars)
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))
    
    def test_hash_schema(self):
        """Test schema hashing"""
        hash1 = CacheKeyBuilder._hash_schema(self.schema1)
        hash2 = CacheKeyBuilder._hash_schema(self.schema2)
        
        # Same schema content in different order should generate same hash
        self.assertEqual(hash1, hash2)
        # Should be valid SHA256 (64 hex chars)
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))


if __name__ == '__main__':
    unittest.main()