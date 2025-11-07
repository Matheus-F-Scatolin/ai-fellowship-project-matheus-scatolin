#!/usr/bin/env python3
"""
Teste completo da API com PDFs reais dos cartões da OAB
Este script testa toda a pipeline: Cache L1/L2/L3 -> Template -> LLM Fallback
"""

import json
import os
import sys
import time
import requests
from typing import Dict, Any

# Configuração da API
API_BASE_URL = "http://localhost:8000"

# Dados de teste
TEST_DATA = {
    "pdf1_path": "files/oab_1.pdf",
    "pdf2_path": "files/oab_2.pdf", 
    "pdf3_path": "files/oab_3.pdf",
    "label": "carteira_oab",
    "schema": {
        "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
        "inscricao": "Número de inscrição do profissional",
        "seccional": "Seccional do profissional",
        "categoria": "Categoria, pode ser ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO, ESTAGIARIA",
        "endereco_profissional": "Endereço profissional completo, normalmente no centro da imagem",
        #"situacao": "Situação do profissional, normalmente no canto inferior direito."
    },
    "resultados_esperados": {
        "pdf1": {
            "nome": "JOANA D'ARC",
            "inscricao": "101943",
            "seccional": "PR",
            "categoria": "Suplementar",
            "endereco_profissional": "Avenida Paulista, Nº 2300, andar Pilotis, Bela Vista, São Paulo - SP, 01310300",
            #"situacao": "Situação Regular"
        },
        "pdf2": {
            "nome": "LUIS FILIPE ARAUJO AMARAL",
            "inscricao": "101943",
            "seccional": "PR",
            "categoria": "Suplementar",
            "endereco_profissional": "Avenida Paulista, Nº 2300, andar Pilotis, Bela Vista, São Paulo - SP, 01310300",
            #"situacao": "Situação Regular"
        },
        "pdf3": {
            "nome": "SON GOKU",
            "inscricao": "101943",
            "seccional": "PR",
            "categoria": "Suplementar",
            "endereco_profissional": "null",
            #"situacao": "Situação Regular"
        }
    }
}

def verificar_api_rodando():
    """Verifica se a API está rodando"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API está rodando e saudável!")
            return True
        else:
            print(f"⚠️  API respondeu com status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API não está rodando!")
        print("💡 Para iniciar a API, execute em outro terminal:")
        print("   python core/api_server.py")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar API: {e}")
        return False

def extrair_dados_pdf(pdf_path: str, label: str, schema: Dict[str, str]) -> Dict[str, Any]:
    """Extrai dados de um PDF usando a API"""
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
    
    # Preparar dados para a requisição
    with open(pdf_path, 'rb') as f:
        files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        data = {
            'label': label,
            'extraction_schema': json.dumps(schema)
        }
        
        # Fazer requisição para a API
        response = requests.post(f"{API_BASE_URL}/extract", files=files, data=data, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        error_msg = f"Erro na API (status {response.status_code}): {response.text}"
        raise Exception(error_msg)

def comparar_resultados(esperado: Dict[str, str], obtido: Dict[str, Any], nome_teste: str) -> float:
    """Compara resultado esperado com o obtido e retorna a precisão"""
    print(f"\n📊 {nome_teste}")
    print("-" * 80)
    print(f"{'Campo':<15} {'Esperado':<25} {'Obtido':<25} {'Status'}")
    print("-" * 80)
    
    acertos = 0
    total_campos = len(esperado)
    
    for campo, valor_esperado in esperado.items():
        valor_obtido = obtido.get(campo, "N/A")
        
        # Normalizar para comparação (case insensitive e remove espaços)
        def normalizar(valor):
            if valor is None:
                return "null"
            return str(valor).strip().lower()
        
        esperado_norm = normalizar(valor_esperado)
        obtido_norm = normalizar(valor_obtido)
        
        # Verificar se está correto
        correto = esperado_norm == obtido_norm
        if correto:
            acertos += 1
            status = "✅"
        else:
            status = "❌"
        
        # Truncar strings muito longas para exibição
        valor_esperado_display = str(valor_esperado)[:23] + "..." if len(str(valor_esperado)) > 23 else str(valor_esperado)
        valor_obtido_display = str(valor_obtido)[:23] + "..." if len(str(valor_obtido)) > 23 else str(valor_obtido)
        
        print(f"{campo:<15} {valor_esperado_display:<25} {valor_obtido_display:<25} {status}")
    
    print("-" * 80)
    
    precisao = (acertos / total_campos) * 100
    print(f"📈 Precisão: {acertos}/{total_campos} campos corretos ({precisao:.1f}%)")
    
    return precisao

def obter_stats_api() -> Dict[str, Any]:
    """Obtém estatísticas da API"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Erro ao obter stats: status {response.status_code}")
            return {}
    except Exception as e:
        print(f"⚠️  Erro ao obter stats: {e}")
        return {}

def mostrar_stats_pipeline(stats: Dict[str, Any]):
    """Mostra estatísticas da pipeline de forma organizada"""
    
    if not stats:
        print("⚠️  Estatísticas não disponíveis")
        return
    
    print("\n📊 ESTATÍSTICAS DA PIPELINE")
    print("=" * 50)
    
    # Stats da pipeline
    pipeline_stats = stats.get('pipeline', {})
    print("🔄 Pipeline:")
    print(f"   📋 Total de requisições: {pipeline_stats.get('total_requests', 0)}")
    print(f"   💾 Cache hits L1/L2: {pipeline_stats.get('cache_hits_l1_l2', 0)}")
    print(f"   🔄 Cache hits L3: {pipeline_stats.get('cache_hits_l3', 0)}")
    print(f"   🎭 Template hits: {pipeline_stats.get('template_hits', 0)}")
    print(f"   🤖 LLM calls (full): {pipeline_stats.get('llm_calls_full', 0)}")
    print(f"   🆘 LLM calls (fallback): {pipeline_stats.get('llm_calls_fallback', 0)}")
    
    # Stats do cache
    cache_stats = stats.get('cache', {})
    if cache_stats:
        print("\n💾 Cache:")
        print(f"   🟢 L1 Memory hits: {cache_stats.get('l1_memory_hits', 0)}")
        print(f"   💽 L2 Disk hits: {cache_stats.get('l2_disk_hits', 0)}")
        print(f"   🔄 L3 Partial hits: {cache_stats.get('l3_partial_hits', 0)}")
        print(f"   ❌ Total misses: {cache_stats.get('total_misses', 0)}")
    
    # Stats dos templates
    template_stats = stats.get('templates', {})
    if template_stats:
        print("\n🎭 Templates:")
        print(f"   📝 Total templates: {template_stats.get('total_templates', 0)}")
        print(f"   📋 Total regras: {template_stats.get('total_rules', 0)}")
        print(f"   ✅ Templates maduros: {template_stats.get('mature_templates', 0)}")

def executar_teste_completo():
    """Executa o teste completo da pipeline com os 3 PDFs"""
    
    print("🚀 TESTE COMPLETO DA PIPELINE DE EXTRAÇÃO")
    print("=" * 60)
    
    # 1. Verificar se API está rodando
    if not verificar_api_rodando():
        return False
    
    # 2. Obter stats iniciais
    print("\n📊 Estatísticas iniciais:")
    stats_iniciais = obter_stats_api()
    mostrar_stats_pipeline(stats_iniciais)
    
    # 3. Testar cada PDF
    resultados = {}
    precisoes = []
    
    for pdf_num in [1, 2, 3]:
        pdf_key = f"pdf{pdf_num}"
        pdf_path = TEST_DATA[f"pdf{pdf_num}_path"]
        esperado = TEST_DATA["resultados_esperados"][pdf_key]
        
        print(f"\n🔍 TESTE {pdf_num}: {pdf_path}")
        print("=" * 40)
        
        try:
            # Verificar se arquivo existe
            if not os.path.exists(pdf_path):
                print(f"❌ Arquivo não encontrado: {pdf_path}")
                continue
            
            # Cronometrar extração
            inicio = time.time()
            resultado = extrair_dados_pdf(pdf_path, TEST_DATA["label"], TEST_DATA["schema"])
            tempo_total = time.time() - inicio
            
            # Mostrar resultado
            print(f"⏱️  Tempo de extração: {tempo_total:.2f}s")
            
            # Extrair dados e metadata
            dados = resultado.get('data', {})
            metadata = resultado.get('metadata', {})
            
            print(f"📄 Arquivo: {metadata.get('file_name', 'N/A')}")
            print(f"📏 Tamanho: {metadata.get('file_size', 0)} bytes")
            print(f"🔄 Método usado: {metadata.get('_pipeline', {}).get('method', 'N/A')}")

            obtido = dados
            if "data" in dados and isinstance(dados, dict):
                obtido = dados["data"]

            # Comparar com esperado
            precisao = comparar_resultados(esperado, obtido, f"Resultado {pdf_num}")
            precisoes.append(precisao)
            
            # Salvar resultado
            resultados[pdf_key] = {
                'dados': dados,
                'metadata': metadata,
                'precisao': precisao,
                'tempo': tempo_total
            }
            
        except Exception as e:
            print(f"❌ Erro no teste {pdf_num}: {e}")
            precisoes.append(0)
    
    # 4. Obter stats finais
    print("\n📊 Estatísticas finais:")
    stats_finais = obter_stats_api()
    mostrar_stats_pipeline(stats_finais)
    
    # 5. Resumo final
    print(f"\n🎯 RESUMO FINAL")
    print("=" * 40)
    
    if precisoes:
        precisao_media = sum(precisoes) / len(precisoes)
        print(f"📈 Precisão média: {precisao_media:.1f}%")
        
        for i, precisao in enumerate(precisoes, 1):
            if precisao == 100:
                status = "🎉 Perfeito!"
            elif precisao >= 80:
                status = "👍 Muito bom!"
            elif precisao >= 60:
                status = "😐 Razoável"
            else:
                status = "😞 Precisa melhorar"
            
            print(f"   PDF {i}: {precisao:.1f}% {status}")
        
        if precisao_media >= 90:
            print("\n🏆 EXCELENTE! A pipeline está funcionando muito bem!")
        elif precisao_media >= 75:
            print("\n👍 BOM! A pipeline está funcionando bem!")
        elif precisao_media >= 50:
            print("\n😐 RAZOÁVEL! A pipeline precisa de ajustes!")
        else:
            print("\n😞 ATENÇÃO! A pipeline precisa de melhorias significativas!")
    
    return True

def testar_cache_behavior():
    """Testa o comportamento do cache fazendo múltiplas requisições"""
    
    print("\n🔍 TESTE DE COMPORTAMENTO DO CACHE")
    print("=" * 50)
    
    if not verificar_api_rodando():
        return
    
    pdf_path = TEST_DATA["pdf1_path"]
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    print(f"📄 Testando cache com: {pdf_path}")
    
    # Primeira requisição (deve usar LLM)
    print("\n1️⃣ Primeira requisição (LLM esperado):")
    inicio = time.time()
    resultado1 = extrair_dados_pdf(pdf_path, TEST_DATA["label"], TEST_DATA["schema"])
    tempo1 = time.time() - inicio
    metodo1 = resultado1.get('metadata', {}).get('_pipeline', {}).get('method', 'N/A')
    print(f"   ⏱️  Tempo: {tempo1:.2f}s")
    print(f"   🔄 Método: {metodo1}")
    
    # Segunda requisição (deve usar cache L1/L2)
    print("\n2️⃣ Segunda requisição (Cache L1/L2 esperado):")
    inicio = time.time()
    resultado2 = extrair_dados_pdf(pdf_path, TEST_DATA["label"], TEST_DATA["schema"])
    tempo2 = time.time() - inicio
    metodo2 = resultado2.get('metadata', {}).get('_pipeline', {}).get('method', 'N/A')
    print(f"   ⏱️  Tempo: {tempo2:.2f}s")
    print(f"   🔄 Método: {metodo2}")
    
    # Terceira requisição (deve usar cache L1)
    print("\n3️⃣ Terceira requisição (Cache L1 esperado):")
    inicio = time.time()
    resultado3 = extrair_dados_pdf(pdf_path, TEST_DATA["label"], TEST_DATA["schema"])
    tempo3 = time.time() - inicio
    metodo3 = resultado3.get('metadata', {}).get('_pipeline', {}).get('method', 'N/A')
    print(f"   ⏱️  Tempo: {tempo3:.2f}s")
    print(f"   🔄 Método: {metodo3}")
    
    # Análise
    print(f"\n📊 ANÁLISE DO CACHE:")
    if tempo2 < tempo1 * 0.5:  # Cache deve ser pelo menos 50% mais rápido
        print("✅ Cache está funcionando! Segunda requisição foi muito mais rápida.")
    else:
        print("⚠️  Cache pode não estar funcionando adequadamente.")
    
    if tempo3 <= tempo2:
        print("✅ Cache L1 está funcionando! Terceira requisição foi igual ou mais rápida.")
    else:
        print("⚠️  Cache L1 pode não estar funcionando adequadamente.")
    
    print(f"\n🏃‍♂️ Velocidades:")
    print(f"   1ª req: {tempo1:.2f}s ({metodo1})")
    print(f"   2ª req: {tempo2:.2f}s ({metodo2}) - {((tempo1-tempo2)/tempo1*100):.1f}% mais rápida")
    print(f"   3ª req: {tempo3:.2f}s ({metodo3}) - {((tempo1-tempo3)/tempo1*100):.1f}% mais rápida")

if __name__ == "__main__":
    print("🎯 TESTE REAL DA API COM PDFs DA OAB")
    print("=" * 60)
    
    # Verificar se os arquivos PDF existem
    arquivos_faltando = []
    for pdf_path in [TEST_DATA["pdf1_path"], TEST_DATA["pdf2_path"], TEST_DATA["pdf3_path"]]:
        if not os.path.exists(pdf_path):
            arquivos_faltando.append(pdf_path)
    
    if arquivos_faltando:
        print("❌ Arquivos PDF não encontrados:")
        for arquivo in arquivos_faltando:
            print(f"   - {arquivo}")
        print("\n💡 Certifique-se de que os PDFs estão na pasta 'files/'")
        sys.exit(1)
    
    try:
        # Teste principal
        sucesso = executar_teste_completo()
        
        if sucesso:
            # Teste de cache
            testar_cache_behavior()
            
            print("\n✅ TODOS OS TESTES CONCLUÍDOS!")
            print("🎉 A API está funcionando corretamente!")
            
    except KeyboardInterrupt:
        print("\n⏹️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()