# Caching - Sistema de cache para resultados de extração
from collections import OrderedDict
from diskcache import Cache
from typing import Dict, Any, Optional
import time
from .key_gen import CacheKeyBuilder

# Constantes de configuração do cache
L2_CACHE_DIR = "./persistent_data/disk_cache"
L1_MEMORY_MAX_SIZE = 100


class CacheManager:
    """
    Gerenciador de cache multi-level (L1: Memória, L2: Disco, L3: Campos parciais).
    
    - L1: Cache em memória usando OrderedDict com LRU eviction
    - L2: Cache em disco usando diskcache para persistência
    - L3: Cache de campos individuais para hits parciais
    """
    
    def __init__(self):
        """Inicializa o gerenciador de cache multi-level."""
        self.l1_memory_cache: OrderedDict = OrderedDict()
        self.l2_disk_cache = Cache(L2_CACHE_DIR)
        self.key_builder = CacheKeyBuilder()
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
            "total_requests": 0
        }
    
    def get(self, pdf_bytes: bytes, label: str, schema: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Busca dados no cache multi-level.
        
        Args:
            pdf_bytes: Conteúdo do PDF em bytes
            label: Label do documento (ex: 'carteira_oab')
            schema: Dicionário com o schema de campos
            
        Returns:
            Dados do cache se encontrados, None caso contrário
        """
        # Incrementa contador de requisições
        self.stats["total_requests"] += 1
        
        # Gera chave L1/L2
        full_key = self.key_builder.generate_l1_l2_key(pdf_bytes, label, schema)
        
        # Verifica L1 (Memória)
        l1_result = self._check_l1(full_key)
        if l1_result is not None:
            self.stats["l1_hits"] += 1
            return l1_result
        
        # Verifica L2 (Disco)
        l2_result = self._check_l2(full_key)
        if l2_result is not None:
            self.stats["l2_hits"] += 1
            # Promove para L1
            self._add_to_l1(full_key, l2_result)
            return l2_result
        
        # Verifica L3 (Parcial)
        l3_result = self._check_l3_partial(pdf_bytes, label, schema)
        if l3_result is not None:
            self.stats["l3_hits"] += 1
            return l3_result
        
        # Cache Miss
        self.stats["misses"] += 1
        return None
    
    def set(self, pdf_bytes: bytes, label: str, schema: Dict[str, str], 
            result_data: Dict[str, Any], exec_metadata: Dict[str, Any]):
        """
        Armazena dados no cache multi-level.
        
        Args:
            pdf_bytes: Conteúdo do PDF em bytes
            label: Label do documento
            schema: Schema dos campos
            result_data: Dados extraídos
            exec_metadata: Metadados da execução
        """
        # Gera chave L1/L2
        full_key = self.key_builder.generate_l1_l2_key(pdf_bytes, label, schema)
        
        # Cria entrada do cache
        cache_entry = {
            "data": result_data,
            "metadata": exec_metadata,
            "timestamp": time.time()
        }
        
        # Adiciona ao L1
        self._add_to_l1(full_key, cache_entry)
        
        # Adiciona ao L2
        self.l2_disk_cache.set(full_key, cache_entry)
        
        # Adiciona ao L3 (campos individuais)
        self._store_l3_fields(pdf_bytes, label, result_data)
    
    def _check_l1(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Verifica e busca dados no cache L1 (memória).
        
        Args:
            key: Chave do cache
            
        Returns:
            Dados do cache L1 ou None
        """
        if key in self.l1_memory_cache:
            # Move para o fim (LRU)
            self.l1_memory_cache.move_to_end(key)
            entry = self.l1_memory_cache[key]
            
            # Adiciona metadados de cache à cópia
            entry_copy = entry.copy()
            entry_copy["_cache_info"] = {"source": "L1_MEMORY"}
            return entry_copy
        
        return None
    
    def _check_l2(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Verifica e busca dados no cache L2 (disco).
        
        Args:
            key: Chave do cache
            
        Returns:
            Dados do cache L2 ou None
        """
        entry = self.l2_disk_cache.get(key)
        if entry is not None:
            # Adiciona metadados de cache
            entry["_cache_info"] = {"source": "L2_DISK"}
            return entry
        
        return None
    
    def _add_to_l1(self, key: str, entry: Dict[str, Any]):
        """
        Adiciona entrada ao cache L1 com LRU eviction.
        
        Args:
            key: Chave do cache
            entry: Dados para armazenar
        """
        self.l1_memory_cache[key] = entry
        
        # Remove item mais antigo se exceder tamanho máximo
        if len(self.l1_memory_cache) > L1_MEMORY_MAX_SIZE:
            self.l1_memory_cache.popitem(last=False)
    
    def _check_l3_partial(self, pdf_bytes: bytes, label: str, schema: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Verifica cache L3 para hits parciais de campos individuais. Por exemplo,
        se o schema requisitado tem 5 campos e apenas 2 estão no cache L3, retorna
        esses 2 campos com indicação de que é um hit parcial.
        
        Args:
            pdf_bytes: Conteúdo do PDF em bytes
            label: Label do documento
            schema: Schema dos campos
            
        Returns:
            Dados parciais do cache L3 ou None
        """
        partial_data = {}
        found_fields = 0
        
        # Busca cada campo individual
        for field_name in schema.keys():
            field_key = self.key_builder.generate_l3_field_key(pdf_bytes, label, field_name)
            field_value = self.l2_disk_cache.get(field_key)
            
            if field_value is not None:
                partial_data[field_name] = field_value
                found_fields += 1
            else:
                partial_data[field_name] = None
        
        # Regra de retorno: pelo menos um campo encontrado E nem todos encontrados
        if found_fields > 0 and found_fields < len(schema):
            entry = {
                "data": partial_data,
                "_cache_info": {
                    "source": "L3_PARTIAL",
                    "fields_found": found_fields,
                    "fields_requested": len(schema)
                }
            }
            return entry
        
        return None
    
    def _store_l3_fields(self, pdf_bytes: bytes, label: str, result_data: Dict[str, Any]):
        """
        Armazena campos individuais no cache L3.
        
        Args:
            pdf_bytes: Conteúdo do PDF em bytes
            label: Label do documento
            result_data: Dados extraídos
        """
        for field_name, field_value in result_data.items():
            # Só armazena se o valor não for None
            if field_value is not None:
                field_key = self.key_builder.generate_l3_field_key(pdf_bytes, label, field_name)
                self.l2_disk_cache.set(field_key, field_value)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dicionário com estatísticas detalhadas do cache
        """
        # Obter tamanho do L2 em bytes
        l2_size_bytes = self.l2_disk_cache.volume()
        
        return {
            "stats": self.stats,
            "l1_memory_size": len(self.l1_memory_cache),
            "l2_disk_size_mb": l2_size_bytes / (1024 * 1024)
        }
    

# Exemplo de funcionamento da cache L3:
# 🎯 DEMONSTRAÇÃO DO CACHE L3
# ============================================================
# 📋 PASSO 1: Processamento inicial
# ✅ Armazenado: {'nome': 'João Silva', 'cpf': '123.456.789-00', 'numero': '123456'}

# 🔍 VERIFICANDO CACHE NO DISCO:
#    L2 cache size: 4 itens
#    Chave L2: c8cf63205069263734fcfe5e74c26035c087690d982e204b3c...
#    Chave L3 (nome): field:c8cf63205069263734fcfe5e74c26035c087690d982e...
#    Chave L3 (cpf): field:c8cf63205069263734fcfe5e74c26035c087690d982e...
#    Chave L3 (numero): field:c8cf63205069263734fcfe5e74c26035c087690d982e...

# 📋 PASSO 2: Nova consulta com schema diferente
# 🧹 L1 limpo para simular consulta posterior

# ✅ CACHE L3 HIT!
#    Fonte: L3_PARTIAL
#    Campos encontrados: 2
#    Campos solicitados: 4
#    Dados:
#      ✅ nome: João Silva
#      ❌ endereco: None
#      ❌ telefone: None
#      ✅ cpf: 123.456.789-00

# 💡 ECONOMIA: Não precisou reprocessar o PDF!
#    - Campos aproveitados: nome, cpf
#    - Apenas faltam: endereco, telefone

# 📋 PASSO 3: Consulta com schema totalmente diferente
# ❌ Cache miss total - campos completamente diferentes

# 📊 ESTATÍSTICAS FINAIS:
#    L1 hits: 0
#    L2 hits: 0
#    L3 hits: 1
#    Misses: 0
#    Total requests: 2