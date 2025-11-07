#!/usr/bin/env python3
"""
Script para processar todos os casos do dataset.json através da API de extração
"""

import json
import os
import time
import requests
from datetime import datetime
from typing import Dict, Any, List

# Configuração da API
API_BASE_URL = "http://localhost:8000"
DATASET_FILE = "dataset.json"
OUTPUTS_FILE = "outputs.json"
FILES_DIR = "files"

def verificar_api_rodando():
    """Verifica se a API está rodando"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"⚠️  API respondeu com status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API não está rodando!")
        print("💡 Para iniciar a API, execute em outro terminal:")
        print("   python start_api.py")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar API: {e}")
        return False

def carregar_dataset():
    """Carrega o dataset.json"""
    try:
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        print(f"✅ Dataset carregado: {len(dataset)} casos encontrados")
        return dataset
    except FileNotFoundError:
        print(f"❌ Arquivo {DATASET_FILE} não encontrado!")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar {DATASET_FILE}: {e}")
        return None

def extrair_dados_pdf(pdf_path: str, label: str, schema: Dict[str, str]) -> Dict[str, Any]:
    """Extrai dados de um PDF usando a API"""
    
    # Verificar se arquivo existe
    full_path = os.path.join(FILES_DIR, pdf_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {full_path}")
    
    # Preparar dados para a requisição
    with open(full_path, 'rb') as f:
        files = {'file': (pdf_path, f, 'application/pdf')}
        data = {
            'label': label,
            'extraction_schema': json.dumps(schema)
        }
        
        # Fazer requisição para a API
        response = requests.post(f"{API_BASE_URL}/extract", files=files, data=data, timeout=60)
    
    if response.status_code == 200:
        return response.json()
    else:
        error_msg = f"Erro na API (status {response.status_code}): {response.text}"
        raise Exception(error_msg)

def formatar_resultado_console(caso_num: int, total_casos: int, pdf_path: str, resultado: Dict[str, Any]) -> None:
    """Formata e exibe o resultado no console"""
    
    print(f"\n{'='*80}")
    print(f"📄 CASO {caso_num}/{total_casos}: {pdf_path}")
    print(f"{'='*80}")
    
    # Dados extraídos
    dados = resultado.get('data', {})
    metadata = resultado.get('metadata', {})
    
    # Informações básicas
    print(f"📏 Tamanho do arquivo: {metadata.get('file_size', 0)} bytes")
    print(f"⏱️  Tempo de extração: {metadata.get('request_time', 0):.2f}s")
    
    # Pipeline info
    pipeline_info = metadata.get('_pipeline', {})
    metodo = pipeline_info.get('method', 'N/A')
    passos = pipeline_info.get('steps', [])
    print(f"🔄 Método usado: {metodo}")
    if passos:
        print(f"🔗 Passos executados: {' → '.join(passos)}")
    
    # Dados extraídos
    print(f"\n📊 DADOS EXTRAÍDOS:")
    print("-" * 40)
    
    if dados:
        for campo, valor in dados.items():
            # Truncar valores muito longos para exibição
            valor_display = str(valor)
            if len(valor_display) > 50:
                valor_display = valor_display[:47] + "..."
            
            status = "✅" if valor is not None and str(valor).strip() else "❌"
            print(f"  {status} {campo:<20}: {valor_display}")
    else:
        print("  ⚠️  Nenhum dado extraído")
    
    # Resumo
    campos_preenchidos = sum(1 for v in dados.values() if v is not None and str(v).strip())
    total_campos = len(dados)
    precisao = (campos_preenchidos / total_campos * 100) if total_campos > 0 else 0
    
    print("-" * 40)
    print(f"📈 {campos_preenchidos}/{total_campos} campos preenchidos ({precisao:.1f}%)")

def processar_dataset():
    """Processa todos os casos do dataset"""
    
    print("🚀 PROCESSAMENTO DO DATASET COMPLETO")
    print("=" * 60)
    
    # 1. Verificar se API está rodando
    if not verificar_api_rodando():
        return False
    
    print("✅ API está rodando e acessível!")
    
    # 2. Carregar dataset
    dataset = carregar_dataset()
    if not dataset:
        return False
    
    # 3. Preparar estrutura de outputs
    outputs = {
        "timestamp": datetime.now().isoformat(),
        "total_casos": len(dataset),
        "api_base_url": API_BASE_URL,
        "casos": []
    }
    
    # 4. Processar cada caso
    casos_processados = 0
    casos_com_erro = 0
    tempo_total_inicio = time.time()
    
    for i, caso in enumerate(dataset, 1):
        pdf_path = caso.get('pdf_path')
        label = caso.get('label')
        schema = caso.get('extraction_schema')
        
        print(f"\n🔄 Processando caso {i}/{len(dataset)}: {pdf_path}")
        
        # Validar dados do caso
        if not pdf_path or not label or not schema:
            print(f"❌ Caso {i} inválido: dados obrigatórios faltando")
            casos_com_erro += 1
            
            outputs["casos"].append({
                "caso_numero": i,
                "pdf_path": pdf_path,
                "label": label,
                "schema": schema,
                "sucesso": False,
                "erro": "Dados obrigatórios faltando",
                "resultado": None
            })
            continue
        
        try:
            # Processar extração
            inicio = time.time()
            resultado = extrair_dados_pdf(pdf_path, label, schema)
            tempo_processamento = time.time() - inicio
            
            # Exibir resultado no console
            formatar_resultado_console(i, len(dataset), pdf_path, resultado)
            
            # Salvar no outputs
            outputs["casos"].append({
                "caso_numero": i,
                "pdf_path": pdf_path,
                "label": label,
                "schema": schema,
                "sucesso": True,
                "tempo_processamento": tempo_processamento,
                "resultado": resultado
            })
            
            casos_processados += 1
            
        except Exception as e:
            print(f"❌ Erro no caso {i}: {e}")
            casos_com_erro += 1
            
            outputs["casos"].append({
                "caso_numero": i,
                "pdf_path": pdf_path,
                "label": label,
                "schema": schema,
                "sucesso": False,
                "erro": str(e),
                "resultado": None
            })
    
    # 5. Estatísticas finais
    tempo_total = time.time() - tempo_total_inicio
    
    outputs["estatisticas"] = {
        "casos_processados": casos_processados,
        "casos_com_erro": casos_com_erro,
        "taxa_sucesso": (casos_processados / len(dataset) * 100) if dataset else 0,
        "tempo_total_segundos": tempo_total,
        "tempo_medio_por_caso": (tempo_total / len(dataset)) if dataset else 0
    }
    
    # 6. Salvar outputs
    try:
        with open(OUTPUTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Resultados salvos em: {OUTPUTS_FILE}")
    except Exception as e:
        print(f"\n❌ Erro ao salvar outputs: {e}")
        return False
    
    # 7. Exibir resumo final
    print(f"\n🎯 RESUMO FINAL")
    print("=" * 50)
    print(f"📊 Total de casos: {len(dataset)}")
    print(f"✅ Processados com sucesso: {casos_processados}")
    print(f"❌ Casos com erro: {casos_com_erro}")
    print(f"📈 Taxa de sucesso: {outputs['estatisticas']['taxa_sucesso']:.1f}%")
    print(f"⏱️  Tempo total: {tempo_total:.2f}s")
    print(f"⚡ Tempo médio por caso: {outputs['estatisticas']['tempo_medio_por_caso']:.2f}s")
    
    if casos_processados == len(dataset):
        print("\n🏆 TODOS OS CASOS PROCESSADOS COM SUCESSO!")
    elif casos_processados > casos_com_erro:
        print("\n👍 MAIORIA DOS CASOS PROCESSADOS COM SUCESSO!")
    else:
        print("\n😞 MUITOS CASOS COM ERRO - VERIFICAR PROBLEMAS!")
    
    return True

def obter_stats_api():
    """Obtém estatísticas da API após processamento"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            
            print(f"\n📊 ESTATÍSTICAS DA API PÓS-PROCESSAMENTO:")
            print("-" * 50)
            
            pipeline_stats = stats.get('pipeline', {})
            print(f"🔄 Total de requisições na API: {pipeline_stats.get('total_requests', 0)}")
            print(f"💾 Cache hits L1/L2: {pipeline_stats.get('cache_hits_l1_l2', 0)}")
            print(f"🔄 Cache hits L3: {pipeline_stats.get('cache_hits_l3', 0)}")
            print(f"🎭 Template hits: {pipeline_stats.get('template_hits', 0)}")
            print(f"🤖 LLM calls (full): {pipeline_stats.get('llm_calls_full', 0)}")
            print(f"🆘 LLM calls (fallback): {pipeline_stats.get('llm_calls_fallback', 0)}")
            
            template_stats = stats.get('templates', {})
            print(f"📝 Templates aprendidos: {template_stats.get('total_templates', 0)}")
            print(f"🎯 Templates maduros: {template_stats.get('mature_templates', 0)}")
            
        else:
            print("⚠️  Não foi possível obter estatísticas da API")
    except Exception:
        print("⚠️  Erro ao obter estatísticas da API")

if __name__ == "__main__":
    print("📁 EXTRAÇÃO DE DADOS DO DATASET COMPLETO")
    print("=" * 60)
    
    try:
        # Verificar se arquivos necessários existem
        if not os.path.exists(DATASET_FILE):
            print(f"❌ Arquivo {DATASET_FILE} não encontrado!")
            exit(1)
        
        if not os.path.exists(FILES_DIR):
            print(f"❌ Diretório {FILES_DIR} não encontrado!")
            exit(1)
        
        # Processar dataset
        sucesso = processar_dataset()
        
        if sucesso:
            # Mostrar estatísticas da API
            obter_stats_api()
            
            print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
            print(f"📄 Resultados disponíveis em: {OUTPUTS_FILE}")
            print(f"🔍 Para análise detalhada, abra o arquivo JSON gerado.")
            
        else:
            print(f"\n❌ PROCESSAMENTO FALHOU!")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Processamento interrompido pelo usuário")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erro durante o processamento: {e}")
        import traceback
        traceback.print_exc()
        exit(1)