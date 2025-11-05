#!/usr/bin/env python3
"""
Exemplo prático do TemplateDatabase usando os arquivos OAB
Este script demonstra como o banco de dados funciona na prática
"""

import os
import json
from core.store.database import TemplateDatabase
from core.connectors.llm_connector import LLMConnector

def extrair_texto_pdf_com_llm_connector(pdf_path):
    """
    Extrai texto estruturado de um PDF usando os métodos do LLMConnector
    """
    try:
        # Cria instância do LLMConnector para usar seus métodos
        llm_connector = LLMConnector()
        
        # Usa os métodos privados do LLMConnector para processar o PDF
        elements = llm_connector._parse_pdf_elements(pdf_path)
        texto = llm_connector._build_structured_text(elements)
        
        return texto
    except Exception as e:
        print(f"Erro ao processar PDF {pdf_path} com LLMConnector: {e}")
        return f"Texto simulado do arquivo {os.path.basename(pdf_path)}"

def extrair_assinatura_estrutural(texto):
    """
    Extrai palavras-chave que formam a "assinatura estrutural" do documento
    """
    # Palavras-chave comuns em documentos OAB
    keywords_oab = [
        'oab', 'exame', 'ordem', 'advogados', 'brasil', 'questão', 'prova',
        'direito', 'lei', 'código', 'artigo', 'constituição', 'processo',
        'recurso', 'decisão', 'tribunal', 'juiz', 'advogado', 'cliente',
        'petição', 'contestação', 'apelação', 'embargo', 'mandado'
    ]
    
    texto_lower = texto.lower()
    assinatura = []
    
    for keyword in keywords_oab:
        if keyword in texto_lower:
            assinatura.append(keyword)
    
    # Adiciona algumas palavras baseadas no tamanho e estrutura
    if len(texto) > 5000:
        assinatura.append('documento_longo')
    if 'questão' in texto_lower and 'alternativa' in texto_lower:
        assinatura.append('questao_multipla_escolha')
    if 'caso' in texto_lower and 'situação' in texto_lower:
        assinatura.append('caso_pratico')
    
    return list(set(assinatura))  # Remove duplicatas

def simular_regras_extracao(tipo_documento):
    """
    Simula regras de extração baseadas no tipo de documento
    """
    regras = []
    
    if 'questao_multipla_escolha' in tipo_documento:
        regras.extend([
            {
                'field_name': 'numero_questao',
                'rule_type': 'regex',
                'rule_data': {'pattern': r'(?:Questão|QUESTÃO)\s*(\d+)'},
                'confidence': 0.85
            },
            {
                'field_name': 'alternativas',
                'rule_type': 'regex', 
                'rule_data': {'pattern': r'[A-E]\)\s*(.+?)(?=[A-E]\)|$)'},
                'confidence': 0.80
            },
            {
                'field_name': 'area_direito',
                'rule_type': 'relative_context',
                'rule_data': {'anchor_text': 'Área:', 'direction': 'after', 'max_distance': 20},
                'confidence': 0.75
            }
        ])
    
    if 'caso_pratico' in tipo_documento:
        regras.extend([
            {
                'field_name': 'situacao_fato',
                'rule_type': 'relative_context',
                'rule_data': {'anchor_text': 'Situação:', 'direction': 'after', 'max_distance': 200},
                'confidence': 0.80
            },
            {
                'field_name': 'pergunta',
                'rule_type': 'relative_context',
                'rule_data': {'anchor_text': 'Pergunta:', 'direction': 'after', 'max_distance': 100},
                'confidence': 0.85
            }
        ])
    
    # Regras gerais para documentos OAB
    regras.extend([
        {
            'field_name': 'numero_inscricao',
            'rule_type': 'regex',
            'rule_data': {'pattern': r'(?:Inscrição|OAB)\s*[:\-]?\s*(\d+)'},
            'confidence': 0.90
        },
        {
            'field_name': 'data_prova',
            'rule_type': 'regex',
            'rule_data': {'pattern': r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'},
            'confidence': 0.75
        }
    ])
    
    return regras

def exemplo_pratico_database():
    """
    Demonstração prática do TemplateDatabase com arquivos OAB
    """
    print("🎯 EXEMPLO PRÁTICO: TemplateDatabase com arquivos OAB")
    print("=" * 60)
    
    # 1. Inicializa o banco de dados
    print("\n📁 1. Inicializando banco de dados...")
    db = TemplateDatabase()
    print("✅ Banco inicializado em: ./persistent_data/templates.db")
    
    # 2. Processa cada arquivo PDF
    arquivos_oab = ['files/oab_1.pdf', 'files/oab_2.pdf', 'files/oab_3.pdf']
    templates_criados = []
    
    for i, arquivo in enumerate(arquivos_oab, 1):
        print(f"\n📄 2.{i} Processando {arquivo}...")
        
        # Extrai texto do PDF usando métodos do LLMConnector
        texto = extrair_texto_pdf_com_llm_connector(arquivo)

        print(f"   📝 Texto extraído: {len(texto)} caracteres")
        
        # 🔍 IMPRIME O TEXTO EXTRAÍDO PARA VERIFICAÇÃO
        print(f"\n📋 TEXTO EXTRAÍDO DO {arquivo}:")
        print("=" * 80)
        print(texto[:1000] + "..." if len(texto) > 1000 else texto)
        print("=" * 80)
        
        # Cria assinatura estrutural
        assinatura = extrair_assinatura_estrutural(texto)
        print(f"   🔍 Assinatura encontrada: {assinatura}")
        
        # Cria template no banco
        label_template = f"oab_documento_{i}"
        
        # Verifica se já existe
        template_existente = db.find_template_by_label(label_template)
        if template_existente:
            print(f"   ⚠️  Template '{label_template}' já existe, atualizando...")
            template_id = template_existente['id']
            db.update_template_signature(template_id, assinatura)
        else:
            print(f"   ➕ Criando novo template '{label_template}'...")
            template_id = db.create_template(label_template, assinatura)
        
        templates_criados.append({
            'id': template_id,
            'label': label_template,
            'arquivo': arquivo,
            'assinatura': assinatura
        })
        
        # Adiciona regras de extração
        regras = simular_regras_extracao(assinatura)
        print(f"   📋 Adicionando {len(regras)} regras de extração...")
        
        for regra in regras:
            db.add_extraction_rule(
                template_id,
                regra['field_name'],
                regra['rule_type'],
                regra['rule_data'],
                regra['confidence']
            )
        
        print(f"   ✅ Template criado com ID: {template_id}")
    
    # 3. Demonstra consultas ao banco
    print(f"\n🔎 3. CONSULTANDO DADOS DO BANCO")
    print("=" * 40)
    
    for template_info in templates_criados:
        print(f"\n📋 Template: {template_info['label']}")
        print(f"   📁 Arquivo: {template_info['arquivo']}")
        print(f"   🆔 ID: {template_info['id']}")
        
        # Busca template no banco
        template_db = db.find_template_by_label(template_info['label'])
        if template_db:
            print(f"   📊 Samples: {template_db['sample_count']}")
            print(f"   🎯 Confiança: {template_db['confidence']}")
            print(f"   📅 Criado: {template_db['created_at']}")
            print(f"   🔄 Atualizado: {template_db['updated_at']}")
            
            # Mostra assinatura armazenada
            assinatura_db = json.loads(template_db['structural_signature'])
            print(f"   🔍 Assinatura: {assinatura_db}")
            
            # Busca regras de extração
            regras_db = db.get_extraction_rules(template_info['id'])
            print(f"   📝 Regras de extração ({len(regras_db)}):")
            
            for regra in regras_db:
                rule_data = json.loads(regra['rule_data'])
                print(f"      • {regra['field_name']}: {regra['rule_type']}")
                print(f"        Dados: {rule_data}")
                print(f"        Confiança: {regra['confidence']}")
    
    # 4. Demonstra busca por padrões
    print(f"\n🔍 4. BUSCAS E ANÁLISES")
    print("=" * 30)
    
    # Encontra templates com palavras-chave específicas
    print("\n🎯 Templates que contêm 'questao_multipla_escolha':")
    for template_info in templates_criados:
        template_db = db.find_template_by_label(template_info['label'])
        if template_db:
            assinatura = json.loads(template_db['structural_signature'])
            if 'questao_multipla_escolha' in assinatura:
                print(f"   ✅ {template_info['label']} ({template_info['arquivo']})")
    
    print("\n📊 Templates que contêm 'direito':")
    for template_info in templates_criados:
        template_db = db.find_template_by_label(template_info['label'])
        if template_db:
            assinatura = json.loads(template_db['structural_signature'])
            if 'direito' in assinatura:
                print(f"   ✅ {template_info['label']} ({template_info['arquivo']})")
    
    # 5. Estatísticas finais
    print(f"\n📈 5. ESTATÍSTICAS FINAIS")
    print("=" * 25)
    print(f"📁 Total de templates criados: {len(templates_criados)}")
    
    total_regras = 0
    for template_info in templates_criados:
        regras = db.get_extraction_rules(template_info['id'])
        total_regras += len(regras)
    
    print(f"📝 Total de regras de extração: {total_regras}")
    print(f"💾 Banco de dados salvo em: {db.db_path}")
    
    print(f"\n🎉 DEMONSTRAÇÃO CONCLUÍDA!")
    print("=" * 30)
    print("💡 O banco agora contém:")
    print("   • Templates com assinaturas estruturais dos PDFs")
    print("   • Regras de extração específicas para cada tipo")
    print("   • Metadados de confiança e versionamento")
    print("   • Histórico de criação e atualização")

if __name__ == '__main__':
    exemplo_pratico_database()