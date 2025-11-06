#!/usr/bin/env python3
"""
Teste real do LLMConnector com padrões extraídos do pattern_builder.py
"""

import json
import os
import sys

# Add the current directory to the path to import from core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.connectors.llm_connector import LLMConnector
from core.learning.pattern_builder import PatternBuilder
from core.learning.rule_executor import RuleExecutor
from core.learning.template_orchestrator import TemplateOrchestrator


def converter_elementos_para_dicionarios(elements_raw):
    """
    Converte elementos da biblioteca unstructured para dicionários 
    no formato esperado pelo PatternBuilder.
    
    Args:
        elements_raw: Lista de elementos da biblioteca unstructured
        
    Returns:
        Lista de dicionários com formato compatível
    """
    elements_converted = []
    
    for elem in elements_raw:
        # Filtrar elementos sem texto
        if not hasattr(elem, 'text') or not elem.text or not elem.text.strip():
            continue
            
        # Extrair coordenadas dos metadados
        x, y = 0, 0
        page_width, page_height = 612, 792  # Valores padrão para PDF (8.5" x 11")
        
        if hasattr(elem, 'metadata') and elem.metadata:
            coordinates = getattr(elem.metadata, 'coordinates', None)
            if coordinates and hasattr(coordinates, 'points'):
                # Pegar o primeiro ponto como referência
                if coordinates.points:
                    point = coordinates.points[0]
                    # Verificar se point é uma tupla (x, y) ou um objeto com atributos
                    if isinstance(point, (tuple, list)) and len(point) >= 2:
                        x, y = point[0], point[1]
                    else:
                        # Fallback para o formato de objeto
                        x = getattr(point, 'x', 0)
                        y = getattr(point, 'y', 0)
            
            # Tentar obter dimensões da página
            page_number = getattr(elem.metadata, 'page_number', 1)
            # Para simplificar, usar dimensões padrão ou calcular aproximadamente
            # baseado nas coordenadas máximas encontradas
        
        element_dict = {
            'text': elem.text.strip(),
            'x': x,
            'y': y,
            'page_width': page_width,
            'page_height': page_height
        }
        
        elements_converted.append(element_dict)
    
    return elements_converted

def converter_padroes_para_rules(padroes_extraidos: dict) -> list:
    """
    Converte padrões extraídos pelo PatternBuilder para o formato esperado pelo RuleExecutor.
    
    Args:
        padroes_extraidos: Dicionário com padrões extraídos {campo: {type, data, confidence}}
        
    Returns:
        Lista de regras no formato do RuleExecutor
    """
    rules = []
    
    for campo, padrao_info in padroes_extraidos.items():
        rule_type = padrao_info["type"]
        rule_data = padrao_info["data"]
        
        # Converter para o formato do RuleExecutor
        rule = {
            "field_name": campo,
            "rule_type": rule_type,
            "rule_data": json.dumps(rule_data)
        }
        
        rules.append(rule)
    
    return rules

def teste_real_oab():
    """Teste real com padrões extraídos do PDF oab_1.pdf e aplicação no oab_2.pdf"""
    
    # Verificar se a API key está configurada
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY não encontrada no arquivo .env")
        print("Por favor, configure sua API key no arquivo .env:")
        print("OPENAI_API_KEY=sua_chave_aqui")
        return
    
    print("🔧 Iniciando teste real com extração de padrões...")
    
    # Configurar dados do teste
    pdf1_path = "files/oab_1.pdf"
    pdf2_path = "files/oab_2.pdf"
    pdf3_path = "files/oab_3.pdf"
    label = "carteira_oab"
    schema = {
        "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
        "inscricao": "Número de inscrição do profissional",
        "seccional": "Seccional do profissional",
        "categoria": "Categoria, pode ser ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO, ESTAGIARIA",
        "situacao": "Situação do profissional, normalmente no canto inferior direito."
    }
    
    # Resultados esperados
    resultado_esperado_pdf1 = {
        "nome": "JOANA D'ARC",
        "inscricao": "101943",
        "seccional": "PR",
        "categoria": "Suplementar",
        "situacao": "Situação Regular"
    }
    
    resultado_esperado_pdf2 = {
        "nome": "LUIS FILIPE ARAUJO AMARAL",
        "inscricao": "101943",
        "seccional": "PR",
        "categoria": "Suplementar",
        "situacao": "Situação Regular"
    }

    resultado_esperado_pdf3 = {
        "nome": "SON GOKU",
        "inscricao": "101943",
        "seccional": "PR",
        "categoria": "Suplementar",
        "situacao": "Situação Regular"

    }
    
    print(f"📄 PDF 1 (para extração de padrões): {pdf1_path}")
    print(f"📄 PDF 2 (para aplicação de padrões): {pdf2_path}")
    print(f"📄 PDF 3 (para teste com TemplateOrchestrator): {pdf3_path}")
    print(f"🏷️  Label: {label}")
    print("📋 Schema:")
    for key, desc in schema.items():
        print(f"   - {key}: {desc}")
    
    try:
        # Verificar se os arquivos existem
        if not os.path.exists(pdf1_path):
            print(f"❌ Arquivo não encontrado: {pdf1_path}")
            return
        if not os.path.exists(pdf2_path):
            print(f"❌ Arquivo não encontrado: {pdf2_path}")
            return
        if not os.path.exists(pdf3_path):
            print(f"❌ Arquivo não encontrado: {pdf3_path}")
            return
            
        # Inicializar componentes
        print("\n🤖 Inicializando LLMConnector, PatternBuilder e TemplateOrchestrator...")
        connector = LLMConnector()
        pattern_builder = PatternBuilder()
        orchestrator = TemplateOrchestrator()
        
        # === ETAPA 1: EXTRAIR DADOS DO PRIMEIRO PDF COM GPT ===
        print("\n" + "="*60)
        print("📊 ETAPA 1: Extraindo dados do primeiro PDF com GPT")
        print("="*60)
        
        resultado_json_pdf1 = connector.run_extraction(pdf1_path, label, schema)
        resultado_pdf1 = json.loads(resultado_json_pdf1)
        
        print("✅ Extração do PDF 1 concluída!")
        print("📊 Resultado obtido:")
        print(json.dumps(resultado_pdf1, indent=2, ensure_ascii=False))
        
        # === ETAPA 2: EXTRAIR PADRÕES DOS DADOS DO PRIMEIRO PDF ===
        print("\n" + "="*60)
        print("🧠 ETAPA 2: Extraindo padrões do primeiro PDF")
        print("="*60)
        
        # Obter elementos estruturados do primeiro PDF
        elements_raw_pdf1 = connector._parse_pdf_elements(pdf1_path)
        print(f"📊 Elementos brutos encontrados no PDF 1: {len(elements_raw_pdf1)}")
        
        # Converter elementos para formato esperado pelo PatternBuilder
        elements_pdf1 = converter_elementos_para_dicionarios(elements_raw_pdf1)
        print(f"📊 Elementos convertidos no PDF 1: {len(elements_pdf1)}")
        
        # Extrair padrões para cada campo
        padroes_extraidos = {}
        print("\n🔍 Extraindo padrões para cada campo:")
        
        for campo, valor in resultado_pdf1.items():
            print(f"\n   🔎 Analisando campo '{campo}' com valor '{valor}':")
            
            rule_type, rule_data, confidence = pattern_builder.learn_rule_for_field(
                campo, valor, elements_pdf1
            )
            
            padroes_extraidos[campo] = {
                "type": rule_type,
                "data": rule_data,
                "confidence": confidence,
                "original_value": valor
            }
            
            print(f"      📋 Tipo de regra: {rule_type}")
            print(f"      📊 Confiança: {confidence:.2f}")
            
            if rule_type == "hybrid":
                print(f"      🔗 Regras híbridas ({len(rule_data['rules'])} regras):")
                for i, rule in enumerate(rule_data['rules']):
                    print(f"         {i+1}. {rule['type']}: {rule['data']} (conf: {rule['confidence']:.2f})")
            elif rule_type != "none":
                print(f"      📝 Dados da regra: {rule_data}")
            else:
                print(f"      ⚠️  Razão: {rule_data.get('reason', 'desconhecida')}")
        
        print("\n" + "="*40)
        print("📋 RESUMO DOS PADRÕES EXTRAÍDOS:")
        print("="*40)
        for campo, info in padroes_extraidos.items():
            print(f"• {campo}: {info['type']} (conf: {info['confidence']:.2f})")
        
        # === ETAPA 3: EXTRAIR DADOS DO SEGUNDO PDF COM GPT (PARA COMPARAÇÃO) ===
        print("\n" + "="*60)
        print("📊 ETAPA 3: Extraindo dados do segundo PDF com GPT (para comparação)")
        print("="*60)
        
        resultado_json_pdf2 = connector.run_extraction(pdf2_path, label, schema)
        resultado_pdf2_gpt = json.loads(resultado_json_pdf2)
        
        print("✅ Extração do PDF 2 com GPT concluída!")
        print("📊 Resultado obtido com GPT:")
        print(json.dumps(resultado_pdf2_gpt, indent=2, ensure_ascii=False))
        
        # === ETAPA 4: APLICAR PADRÕES NO SEGUNDO PDF ===
        print("\n" + "="*60)
        print("🎯 ETAPA 4: Aplicando padrões extraídos no segundo PDF")
        print("="*60)
        
        # Obter elementos estruturados do segundo PDF
        elements_raw_pdf2 = connector._parse_pdf_elements(pdf2_path)
        print(f"📊 Elementos brutos encontrados no PDF 2: {len(elements_raw_pdf2)}")
        
        # Converter elementos para formato esperado pelo PatternBuilder
        elements_pdf2 = converter_elementos_para_dicionarios(elements_raw_pdf2)
        print(f"📊 Elementos convertidos no PDF 2: {len(elements_pdf2)}")
        
        # Converter padrões extraídos para formato do RuleExecutor
        rules_for_executor = converter_padroes_para_rules(padroes_extraidos)
        print(f"📊 Regras convertidas para RuleExecutor: {len(rules_for_executor)}")
        
        # Aplicar regras usando RuleExecutor
        rule_executor = RuleExecutor()
        resultado_pdf2_padroes = rule_executor.execute_all_rules(rules_for_executor, elements_pdf2)
        
        print("\n✅ Aplicação de padrões concluída!")
        print("📊 Resultado obtido com padrões:")
        print(json.dumps(resultado_pdf2_padroes, indent=2, ensure_ascii=False))
        
        # === ETAPA 5: COMPARAÇÃO DE RESULTADOS ===
        print("\n" + "="*60)
        print("📈 ETAPA 5: Comparação de resultados")
        print("="*60)
        
        print("\n🎯 Resultado esperado para PDF 2:")
        print(json.dumps(resultado_esperado_pdf2, indent=2, ensure_ascii=False))
        
        print("\n🔍 Comparação GPT vs Padrões vs Esperado:")
        comparar_resultados(resultado_esperado_pdf2, resultado_pdf2_gpt, resultado_pdf2_padroes)
        
        # === ETAPA 6: ENSINAR O TEMPLATEORCHESTRATOR COM OS DADOS DO PDF 1 ===
        print("\n" + "="*60)
        print("🎓 ETAPA 6: Ensinando TemplateOrchestrator com dados do PDF 1")
        print("="*60)
        
        # Ensinar o orchestrator com os dados do PDF 1
        print("📚 Ensinando o TemplateOrchestrator com os dados extraídos do PDF 1...")
        orchestrator.learn_from_llm_result(label, schema, resultado_pdf1, elements_pdf1)
        
        # Mostrar estatísticas do template
        stats = orchestrator.get_template_stats()
        print("📊 Estatísticas do banco de templates:")
        print(f"   📝 Total de templates: {stats['total_templates']}")
        print(f"   📋 Total de regras: {stats['total_rules']}")
        print(f"   🎯 Templates maduros: {stats['mature_templates']}")
        print(f"   📊 Limite mínimo de amostras: {stats['min_sample_threshold']}")
        print(f"   🎯 Confiança mínima para salvar regra: {stats['min_rule_confidence']}")
        
        # === ETAPA 7: ENSINAR O TEMPLATEORCHESTRATOR COM OS DADOS DO PDF 2 ===
        print("\n" + "="*60)
        print("🎓 ETAPA 7: Ensinando TemplateOrchestrator com dados do PDF 2")
        print("="*60)
        
        # Ensinar o orchestrator com os dados do PDF 2
        print("📚 Ensinando o TemplateOrchestrator com os dados extraídos do PDF 2...")
        orchestrator.learn_from_llm_result(label, schema, resultado_pdf2_gpt, elements_pdf2)
        
        # Mostrar estatísticas atualizadas
        stats = orchestrator.get_template_stats()
        print("📊 Estatísticas atualizadas do banco de templates:")
        print(f"   📝 Total de templates: {stats['total_templates']}")
        print(f"   📋 Total de regras: {stats['total_rules']}")
        print(f"   🎯 Templates maduros: {stats['mature_templates']}")
        
        # === ETAPA 8: TESTE COM PDF 3 USANDO TEMPLATEORCHESTRATOR ===
        print("\n" + "="*60)
        print("🚀 ETAPA 8: Testando PDF 3 com TemplateOrchestrator")
        print("="*60)
        
        # Obter elementos do PDF 3
        elements_raw_pdf3 = connector._parse_pdf_elements(pdf3_path)
        print(f"📊 Elementos brutos encontrados no PDF 3: {len(elements_raw_pdf3)}")
        
        elements_pdf3 = converter_elementos_para_dicionarios(elements_raw_pdf3)
        print(f"📊 Elementos convertidos no PDF 3: {len(elements_pdf3)}")
        
        # Tentar usar template existente
        print("🔍 Tentando usar template existente para extrair dados do PDF 3...")
        resultado_pdf3_template = orchestrator.check_and_use_template(label, elements_pdf3)
        
        if resultado_pdf3_template:
            print("✅ Template encontrado e aplicado com sucesso!")
            print("📊 Resultado obtido com TemplateOrchestrator:")
            print(json.dumps(resultado_pdf3_template, indent=2, ensure_ascii=False))
        else:
            print("⚠️  Template não pôde ser aplicado (pode não estar maduro o suficiente)")
            print("📥 Extraindo dados do PDF 3 com GPT para comparação...")
            
            # Fallback para GPT se template não funcionar
            resultado_json_pdf3 = connector.run_extraction(pdf3_path, label, schema)
            resultado_pdf3_gpt = json.loads(resultado_json_pdf3)
            
            print("📊 Resultado obtido com GPT:")
            print(json.dumps(resultado_pdf3_gpt, indent=2, ensure_ascii=False))
            
            # Ensinar o orchestrator com os dados do PDF 3
            print("📚 Ensinando o TemplateOrchestrator com os dados extraídos do PDF 3...")
            orchestrator.learn_from_llm_result(label, schema, resultado_pdf3_gpt, elements_pdf3)
            
            resultado_pdf3_template = resultado_pdf3_gpt
        
        # === ETAPA 9: COMPARAÇÃO FINAL COM PDF 3 ===
        print("\n" + "="*60)
        print("📈 ETAPA 9: Comparação final com PDF 3")
        print("="*60)
        
        print("\n🎯 Resultado esperado para PDF 3:")
        print(json.dumps(resultado_esperado_pdf3, indent=2, ensure_ascii=False))
        
        # Extrair dados do PDF 3 com GPT para comparação direta
        print("\n📥 Extraindo dados do PDF 3 com GPT para comparação...")
        resultado_json_pdf3_gpt = connector.run_extraction(pdf3_path, label, schema)
        resultado_pdf3_gpt_comparacao = json.loads(resultado_json_pdf3_gpt)
        
        print("\n🔍 Comparação GPT vs TemplateOrchestrator vs Esperado:")
        comparar_resultados_triplo(resultado_esperado_pdf3, resultado_pdf3_gpt_comparacao, resultado_pdf3_template)
        
        # Estatísticas finais
        stats_final = orchestrator.get_template_stats()
        print(f"\n📊 Estatísticas finais do banco de templates:")
        print(f"   📝 Total de templates: {stats_final['total_templates']}")
        print(f"   📋 Total de regras: {stats_final['total_rules']}")
        print(f"   🎯 Templates maduros: {stats_final['mature_templates']}")
            
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()


def comparar_resultados(esperado: dict, resultado_gpt: dict, resultado_padroes: dict):
    """
    Compara os resultados obtidos por GPT e por padrões com o resultado esperado.
    """
    print("\n📊 Comparação detalhada:")
    print("-" * 80)
    print(f"{'Campo':<15} {'Esperado':<20} {'GPT':<20} {'Padrões':<20} {'Status'}")
    print("-" * 80)
    
    acertos_gpt = 0
    acertos_padroes = 0
    total_campos = len(esperado)
    
    for campo, valor_esperado in esperado.items():
        valor_gpt = resultado_gpt.get(campo, "N/A")
        valor_padroes = resultado_padroes.get(campo, "N/A")
        
        # Normalizar para comparação
        def normalizar(valor):
            if valor is None:
                return "null"
            return str(valor).strip().lower()
        
        esperado_norm = normalizar(valor_esperado)
        gpt_norm = normalizar(valor_gpt)
        padroes_norm = normalizar(valor_padroes)
        
        # Verificar acertos
        gpt_correto = esperado_norm == gpt_norm
        padroes_correto = esperado_norm == padroes_norm
        
        if gpt_correto:
            acertos_gpt += 1
        if padroes_correto:
            acertos_padroes += 1
        
        # Status visual
        status = ""
        if gpt_correto and padroes_correto:
            status = "✅✅"
        elif gpt_correto and not padroes_correto:
            status = "✅❌"
        elif not gpt_correto and padroes_correto:
            status = "❌✅"
        else:
            status = "❌❌"
        
        print(f"{campo:<15} {str(valor_esperado):<20} {str(valor_gpt):<20} {str(valor_padroes):<20} {status}")
    
    print("-" * 80)
    
    # Calcular precisões
    precisao_gpt = (acertos_gpt / total_campos) * 100
    precisao_padroes = (acertos_padroes / total_campos) * 100
    
    print(f"\n📈 Resultados finais:")
    print(f"   🤖 GPT: {acertos_gpt}/{total_campos} campos corretos ({precisao_gpt:.1f}%)")
    print(f"   🧠 Padrões: {acertos_padroes}/{total_campos} campos corretos ({precisao_padroes:.1f}%)")
    
    if precisao_padroes > precisao_gpt:
        print(f"   🏆 Padrões superaram o GPT por {precisao_padroes - precisao_gpt:.1f} pontos!")
    elif precisao_gpt > precisao_padroes:
        print(f"   🤖 GPT superou os padrões por {precisao_gpt - precisao_padroes:.1f} pontos!")
    else:
        print(f"   🤝 Empate! Ambos obtiveram {precisao_gpt:.1f}% de precisão!")
    
    return precisao_gpt, precisao_padroes


def comparar_resultados_triplo(esperado: dict, resultado_gpt: dict, resultado_template: dict):
    """
    Compara os resultados obtidos por GPT e por TemplateOrchestrator com o resultado esperado.
    """
    print("\n📊 Comparação detalhada:")
    print("-" * 90)
    print(f"{'Campo':<15} {'Esperado':<20} {'GPT':<20} {'TemplateOrch':<20} {'Status'}")
    print("-" * 90)
    
    acertos_gpt = 0
    acertos_template = 0
    total_campos = len(esperado)
    
    for campo, valor_esperado in esperado.items():
        valor_gpt = resultado_gpt.get(campo, "N/A")
        valor_template = resultado_template.get(campo, "N/A")
        
        # Normalizar para comparação
        def normalizar(valor):
            if valor is None:
                return "null"
            return str(valor).strip().lower()
        
        esperado_norm = normalizar(valor_esperado)
        gpt_norm = normalizar(valor_gpt)
        template_norm = normalizar(valor_template)
        
        # Verificar acertos
        gpt_correto = esperado_norm == gpt_norm
        template_correto = esperado_norm == template_norm
        
        if gpt_correto:
            acertos_gpt += 1
        if template_correto:
            acertos_template += 1
        
        # Status visual
        status = ""
        if gpt_correto and template_correto:
            status = "✅✅"
        elif gpt_correto and not template_correto:
            status = "✅❌"
        elif not gpt_correto and template_correto:
            status = "❌✅"
        else:
            status = "❌❌"
        
        print(f"{campo:<15} {str(valor_esperado):<20} {str(valor_gpt):<20} {str(valor_template):<20} {status}")
    
    print("-" * 90)
    
    # Calcular precisões
    precisao_gpt = (acertos_gpt / total_campos) * 100
    precisao_template = (acertos_template / total_campos) * 100
    
    print(f"\n📈 Resultados finais:")
    print(f"   🤖 GPT: {acertos_gpt}/{total_campos} campos corretos ({precisao_gpt:.1f}%)")
    print(f"   🎭 TemplateOrchestrator: {acertos_template}/{total_campos} campos corretos ({precisao_template:.1f}%)")
    
    if precisao_template > precisao_gpt:
        print(f"   🏆 TemplateOrchestrator superou o GPT por {precisao_template - precisao_gpt:.1f} pontos!")
    elif precisao_gpt > precisao_template:
        print(f"   🤖 GPT superou o TemplateOrchestrator por {precisao_gpt - precisao_template:.1f} pontos!")
    else:
        print(f"   🤝 Empate! Ambos obtiveram {precisao_gpt:.1f}% de precisão!")
    
    return precisao_gpt, precisao_template

def teste_build_structured_text():
    """Teste específico da função _build_structured_text com PDFs reais"""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY não encontrada. Pulando teste real.")
        return
    
    print("\n🔧 Testando função _build_structured_text com PDFs reais...")
    
    connector = LLMConnector()
    
    # Teste com oab_1.pdf
    test_files = [
        {
            "file": "files/oab_1.pdf",
            "expected_content": ["JOANA D'ARC", "101943", "PR", "SUPLEMENTAR", "SITUAÇÃO REGULAR"]
        },
        {
            "file": "files/oab_2.pdf", 
            "expected_content": ["LUIS FILIPE ARAUJO AMARAL", "101943", "PR", "SUPLEMENTAR", "SITUAÇÃO REGULAR"]
        },
        {
            "file": "files/oab_3.pdf",
            "expected_content": ["SON GOKU", "101943", "PR", "SUPLEMENTAR", "SITUAÇÃO REGULAR"]
        }
    ]
    
    for test_case in test_files:
        file_path = test_case["file"]
        expected_content = test_case["expected_content"]
        
        if not os.path.exists(file_path):
            print(f"⚠️  Arquivo {file_path} não encontrado. Pulando...")
            continue
            
        print(f"\n📄 Testando: {file_path}")
        
        try:
            # Parse do PDF usando unstructured
            elements = connector._parse_pdf_elements(file_path)
            print(f"   📊 Elementos encontrados: {len(elements)}")
            
            # Estruturar o texto
            structured_text = connector._build_structured_text(elements)
            print(f"   📝 Texto estruturado ({len(structured_text)} caracteres):")
            
            # Mostrar as primeiras linhas
            lines = structured_text.split('\n')
            print(f"   📋 Total de linhas: {len(lines)}")
            print("   🔍 Primeiras 10 linhas:")
            for i, line in enumerate(lines[:10]):
                print(f"      {i+1:2d}: {line}")
            
            # Verificar se o conteúdo esperado está presente
            print("   ✅ Verificando conteúdo esperado:")
            content_found = 0
            for expected in expected_content:
                if expected.upper() in structured_text.upper():
                    print(f"      ✅ '{expected}' encontrado")
                    content_found += 1
                else:
                    print(f"      ❌ '{expected}' NÃO encontrado")
            
            precisao = (content_found / len(expected_content)) * 100
            print(f"   📈 Precisão de conteúdo: {content_found}/{len(expected_content)} ({precisao:.1f}%)")
            
            if precisao == 100:
                print(f"   🎉 Perfeito! Todo o conteúdo esperado foi encontrado em {file_path}")
            elif precisao >= 80:
                print(f"   👍 Muito bom! A maioria do conteúdo foi encontrada em {file_path}")
            else:
                print(f"   ⚠️  Atenção! Parte do conteúdo não foi encontrada em {file_path}")
                
        except Exception as e:
            print(f"   ❌ Erro ao processar {file_path}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    teste_real_oab()
    print("\n" + "="*60)
    teste_build_structured_text()