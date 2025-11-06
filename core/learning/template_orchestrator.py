# Template Orchestrator - Orquestração de templates de extração
import json
from typing import Dict, Any, List, Optional

from core.store.database import TemplateDatabase
from core.learning.struct_matcher import StructuralMatcher
from core.learning.pattern_builder import PatternBuilder
from core.learning.rule_executor import RuleExecutor


# Um template deve ter visto pelo menos 2 exemplos antes de confiarmos nele
MIN_SAMPLE_THRESHOLD = 2

# Uma regra só será salva no banco se tiver uma confiança mínima
MIN_RULE_CONFIDENCE_TO_SAVE = 0.5


class TemplateOrchestrator:
    """
    Classe principal que coordena todos os componentes de aprendizado
    (Database, Matcher, Builder, Executor) para executar a lógica de template.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa o orquestrador com todas as suas ferramentas.
        
        Args:
            db_path: Caminho opcional para o banco de dados. Se None, usa o padrão.
        """
        if db_path:
            self.db = TemplateDatabase(db_path=db_path)
        else:
            self.db = TemplateDatabase()  # Usa o caminho padrão
        
        self.matcher = StructuralMatcher()
        self.builder = PatternBuilder()
        self.executor = RuleExecutor()
    
    def check_and_use_template(self, label: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Via rápida: verifica se existe um template para o label e tenta usá-lo.
        
        Args:
            label: Label do template
            elements: Lista de elementos estruturais do documento
            
        Returns:
            Dados extraídos se sucesso, None se falhar
        """
        # 1. Filtro por Label
        template = self.db.find_template_by_label(label)
        
        # 2. Verificar Existência
        if not template:
            return None
        
        # 3. Verificar Confiança (Warm-up)
        if template['sample_count'] < MIN_SAMPLE_THRESHOLD:
            return None
        
        # 4. Comparar Assinaturas (Nossa Estratégia)
        saved_signature_list = json.loads(template['structural_signature'])
        is_match, score = self.matcher.check_similarity(elements, saved_signature_list)
        
        # 5. Verificar Match
        if not is_match:
            return None
        
        # 6. Match! Executar Extração Rápida
        template_id = template['id']
        rules = self.db.get_extraction_rules(template_id)
        if not rules:
            return None
        
        extracted_data = self.executor.execute_all_rules(rules, elements)
        return extracted_data
    
    def learn_from_llm_result(self, label: str, schema: Dict[str, str], 
                             llm_data: Dict[str, Any], elements: List[Dict[str, Any]]):
        """
        Aprendizado: analisa o resultado do LLM e atualiza/cria templates.
        
        Args:
            label: Label do template
            schema: Schema com descrições dos campos
            llm_data: Dados extraídos pelo LLM
            elements: Lista de elementos estruturais do documento
        """
        # 1. Verificar se template existe
        template = self.db.find_template_by_label(label)
        new_signature_set = self.matcher.extract_signature(elements)
        
        # 2. Template Existe (Atualizar)
        if template:
            template_id = template['id']
            old_signature_set = set(json.loads(template['structural_signature']))
            updated_signature = list(old_signature_set.union(new_signature_set))
            self.db.update_template_signature(template_id, updated_signature)
        # 3. Template Novo (Criar)
        else:
            template_id = self.db.create_template(label, list(new_signature_set))
        
        # 4. Aprender/Atualizar Regras para cada Campo
        for field_name, field_description in schema.items():
            field_value = llm_data.get(field_name)
            
            # Aprender a regra
            rule_type, rule_data, confidence = self.builder.learn_rule_for_field(
                field_name, field_value, elements
            )
            
            # Salvar Regra (Se Confiável)
            if confidence >= MIN_RULE_CONFIDENCE_TO_SAVE:
                self.db.add_extraction_rule(template_id, field_name, rule_type, rule_data, confidence)
    
    def get_template_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas dos templates no banco de dados.
        
        Returns:
            Dicionário com estatísticas
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Contar templates
            cursor.execute("SELECT COUNT(*) FROM templates")
            total_templates = cursor.fetchone()[0]
            
            # Contar regras
            cursor.execute("SELECT COUNT(*) FROM extraction_rules")
            total_rules = cursor.fetchone()[0]
            
            # Contar templates com sample_count >= MIN_SAMPLE_THRESHOLD
            cursor.execute("SELECT COUNT(*) FROM templates WHERE sample_count >= ?", (MIN_SAMPLE_THRESHOLD,))
            mature_templates = cursor.fetchone()[0]
            
            return {
                "total_templates": total_templates,
                "total_rules": total_rules,
                "mature_templates": mature_templates,
                "min_sample_threshold": MIN_SAMPLE_THRESHOLD,
                "min_rule_confidence": MIN_RULE_CONFIDENCE_TO_SAVE
            }