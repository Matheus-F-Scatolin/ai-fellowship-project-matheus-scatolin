"""
Testes unitários para TemplateDatabase
"""

import unittest
import tempfile
import os
import json
from core.store.database import TemplateDatabase


class TestTemplateDatabase(unittest.TestCase):
    
    def setUp(self):
        """Configura um banco de dados temporário para cada teste"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_templates.db')
        self.db = TemplateDatabase(self.db_path)
    
    def tearDown(self):
        """Limpa o banco de dados temporário após cada teste"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Testa se o banco é inicializado corretamente"""
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(self.db.db_path, self.db_path)
    
    def test_create_template(self):
        """Testa a criação de um template"""
        signature = ['keyword1', 'keyword2', 'keyword3']
        template_id = self.db.create_template('test_label', signature)
        
        self.assertIsInstance(template_id, int)
        self.assertGreater(template_id, 0)
    
    def test_find_template_by_label(self):
        """Testa a busca de template por label"""
        # Primeiro cria um template
        signature = ['keyword1', 'keyword2']
        template_id = self.db.create_template('test_label', signature)
        
        # Busca o template
        found_template = self.db.find_template_by_label('test_label')
        
        self.assertIsNotNone(found_template)
        self.assertEqual(found_template['label'], 'test_label')
        self.assertEqual(found_template['id'], template_id)
        self.assertEqual(found_template['sample_count'], 1)
        self.assertEqual(found_template['confidence'], 0.5)
        
        # Verifica a assinatura estrutural
        stored_signature = json.loads(found_template['structural_signature'])
        self.assertEqual(sorted(signature), stored_signature)
    
    def test_find_nonexistent_template(self):
        """Testa a busca de um template que não existe"""
        result = self.db.find_template_by_label('nonexistent_label')
        self.assertIsNone(result)
    
    def test_update_template_signature(self):
        """Testa a atualização de assinatura de template"""
        # Cria um template
        original_signature = ['keyword1', 'keyword2']
        template_id = self.db.create_template('test_label', original_signature)
        
        # Atualiza a assinatura
        new_signature = ['keyword1', 'keyword3', 'keyword4']
        self.db.update_template_signature(template_id, new_signature)
        
        # Verifica se foi atualizado
        updated_template = self.db.find_template_by_label('test_label')
        stored_signature = json.loads(updated_template['structural_signature'])
        self.assertEqual(sorted(new_signature), stored_signature)
        self.assertEqual(updated_template['sample_count'], 2)  # Deve ter incrementado
    
    def test_add_extraction_rule(self):
        """Testa a adição de regra de extração"""
        # Cria um template
        template_id = self.db.create_template('test_label', ['keyword1'])
        
        # Adiciona uma regra
        rule_data = {'pattern': r'\d{3}-\d{3}-\d{4}'}
        self.db.add_extraction_rule(template_id, 'phone', 'regex', rule_data, 0.9)
        
        # Verifica se a regra foi adicionada
        rules = self.db.get_extraction_rules(template_id)
        self.assertEqual(len(rules), 1)
        
        rule = rules[0]
        self.assertEqual(rule['field_name'], 'phone')
        self.assertEqual(rule['rule_type'], 'regex')
        self.assertEqual(rule['confidence'], 0.9)
        self.assertEqual(json.loads(rule['rule_data']), rule_data)
    
    def test_upsert_extraction_rule(self):
        """Testa o comportamento de UPSERT das regras (substitui regras existentes)"""
        # Cria um template
        template_id = self.db.create_template('test_label', ['keyword1'])
        
        # Adiciona uma regra inicial
        self.db.add_extraction_rule(template_id, 'phone', 'regex', {'pattern': 'old'}, 0.5)
        
        # Adiciona uma nova regra para o mesmo campo (deve substituir)
        self.db.add_extraction_rule(template_id, 'phone', 'regex', {'pattern': 'new'}, 0.8)
        
        # Verifica que só existe uma regra
        rules = self.db.get_extraction_rules(template_id)
        self.assertEqual(len(rules), 1)
        
        rule = rules[0]
        self.assertEqual(json.loads(rule['rule_data'])['pattern'], 'new')
        self.assertEqual(rule['confidence'], 0.8)
    
    def test_get_extraction_rules_empty(self):
        """Testa a busca de regras para um template sem regras"""
        # Cria um template
        template_id = self.db.create_template('test_label', ['keyword1'])
        
        # Busca regras (deve retornar lista vazia)
        rules = self.db.get_extraction_rules(template_id)
        self.assertEqual(len(rules), 0)
        self.assertIsInstance(rules, list)
    
    def test_multiple_rules_different_fields(self):
        """Testa múltiplas regras para campos diferentes"""
        # Cria um template
        template_id = self.db.create_template('test_label', ['keyword1'])
        
        # Adiciona múltiplas regras
        self.db.add_extraction_rule(template_id, 'phone', 'regex', {'pattern': r'\d{3}-\d{3}-\d{4}'}, 0.9)
        self.db.add_extraction_rule(template_id, 'email', 'regex', {'pattern': r'\S+@\S+'}, 0.8)
        self.db.add_extraction_rule(template_id, 'name', 'relative_context', {'anchor': 'Nome:'}, 0.7)
        
        # Verifica todas as regras
        rules = self.db.get_extraction_rules(template_id)
        self.assertEqual(len(rules), 3)
        
        field_names = {rule['field_name'] for rule in rules}
        self.assertEqual(field_names, {'phone', 'email', 'name'})


if __name__ == '__main__':
    unittest.main()