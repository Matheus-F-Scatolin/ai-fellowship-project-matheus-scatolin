import hashlib
import json
from typing import Dict


class CacheKeyBuilder:
    """
    Classe para geração de chaves de cache determinísticas.
    
    Utiliza hashlib.sha256 para criar chaves únicas e determinísticas
    baseadas no conteúdo do PDF, label e schema. Para os mesmos inputs,
    sempre gera a mesma chave, garantindo consistência no cache.
    """
    
    @staticmethod
    def generate_l1_l2_key(pdf_bytes: bytes, label: str, schema: Dict[str, str]) -> str:
        """
        Gera uma chave para cache L1/L2 baseada no PDF, label e schema.
        
        Args:
            pdf_bytes: Conteúdo do PDF em bytes
            label: Label do documento (ex: 'carteira_oab')
            schema: Dicionário com o schema de campos
            
        Returns:
            Chave no formato: {pdf_hash}:{label}:{schema_hash}
            
        Example:
            "a591a6d4...:carteira_oab:3f7b2e1c..."
        """
        pdf_hash = CacheKeyBuilder._hash_content(pdf_bytes)
        schema_hash = CacheKeyBuilder._hash_schema(schema)
        return f"{pdf_hash}:{label}:{schema_hash}"
    
    @staticmethod
    def generate_l3_field_key(pdf_bytes: bytes, label: str, field_name: str) -> str:
        """
        Gera uma chave para cache L3 específica para um campo.
        
        Args:
            pdf_bytes: Conteúdo do PDF em bytes
            label: Label do documento (ex: 'carteira_oab')
            field_name: Nome do campo específico (ex: 'nome')
            
        Returns:
            Chave no formato: field:{pdf_hash}:{label}:{field_name}
            
        Example:
            "field:a591a6d4...:carteira_oab:nome"
        """
        pdf_hash = CacheKeyBuilder._hash_content(pdf_bytes)
        return f"field:{pdf_hash}:{label}:{field_name}"
    
    @staticmethod
    def _hash_content(content: bytes) -> str:
        """
        Gera hash SHA256 do conteúdo em bytes.
        
        Args:
            content: Conteúdo em bytes para fazer hash
            
        Returns:
            Hash SHA256 em formato hexadecimal
        """
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def _hash_schema(schema: Dict[str, str]) -> str:
        """
        Gera hash SHA256 determinístico de um dicionário schema.
        
        Normaliza o dicionário ordenando as chaves para garantir que
        dicionários com o mesmo conteúdo mas em ordens diferentes
        gerem o mesmo hash.
        
        Args:
            schema: Dicionário com o schema de campos
            
        Returns:
            Hash SHA256 em formato hexadecimal
        """
        # Normaliza o dicionário ordenando as chaves
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()