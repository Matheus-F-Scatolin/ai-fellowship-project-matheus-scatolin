#!/usr/bin/env python3
"""
Teste real do LLMConnector com o arquivo oab_1.pdf
"""

import json
import os
from core.connectors.llm_connector import LLMConnector

def teste_real_oab():
    """Teste real com o PDF oab_1.pdf"""
    
    # Verificar se a API key está configurada
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY não encontrada no arquivo .env")
        print("Por favor, configure sua API key no arquivo .env:")
        print("OPENAI_API_KEY=sua_chave_aqui")
        return
    
    print("🔧 Iniciando teste real do LLMConnector...")
    
    # Configurar dados do teste
    pdf_path = "files/oab_1.pdf"
    label = "carteira_oab"
    schema = {
        "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
        "inscricao": "Número de inscrição do profissional",
        "seccional": "Seccional do profissional",
        "categoria": "Categoria, pode ser ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO, ESTAGIARIA",
        "situacao": "Situação do profissional, normalmente no canto inferior direito."
    }
    
    # Resultado esperado
    resultado_esperado = {
        "nome": "JOANA D'ARC",
        "inscricao": "101943",
        "seccional": "PR",
        "categoria": "Suplementar",
        "situacao": "Situação Regular"
    }
    
    print(f"📄 Arquivo PDF: {pdf_path}")
    print(f"🏷️  Label: {label}")
    print("📋 Schema:")
    for key, desc in schema.items():
        print(f"   - {key}: {desc}")
    
    print("\n🎯 Resultado esperado:")
    print(json.dumps(resultado_esperado, indent=2, ensure_ascii=False))
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(pdf_path):
            print(f"❌ Arquivo não encontrado: {pdf_path}")
            return
            
        # Inicializar o conector
        print("\n🤖 Inicializando LLMConnector...")
        connector = LLMConnector()
        
        # Executar extração
        print("⚡ Executando extração...")
        resultado_json = connector.run_extraction(pdf_path, label, schema)
        
        # Parse do resultado
        resultado = json.loads(resultado_json)
        
        print("\n✅ Extração concluída!")
        print("📊 Resultado obtido:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        # Comparar resultados
        print("\n🔍 Comparação com resultado esperado:")
        campos_corretos = 0
        total_campos = len(resultado_esperado)
        
        for campo, valor_esperado in resultado_esperado.items():
            valor_obtido = resultado.get(campo, "CAMPO_NAO_ENCONTRADO")
            
            # Normalizar para comparação (case insensitive e remover espaços)
            valor_esperado_norm = str(valor_esperado).strip().lower()
            valor_obtido_norm = str(valor_obtido).strip().lower()
            
            if valor_esperado_norm == valor_obtido_norm:
                print(f"   ✅ {campo}: '{valor_obtido}' (correto)")
                campos_corretos += 1
            else:
                print(f"   ❌ {campo}: obtido '{valor_obtido}' | esperado '{valor_esperado}'")
        
        # Calcular precisão
        precisao = (campos_corretos / total_campos) * 100
        print(f"\n📈 Precisão: {campos_corretos}/{total_campos} campos corretos ({precisao:.1f}%)")
        
        if precisao == 100:
            print("🎉 Perfeito! Todos os campos foram extraídos corretamente!")
        elif precisao >= 80:
            print("👍 Muito bom! A maioria dos campos foi extraída corretamente.")
        elif precisao >= 60:
            print("⚠️  Razoável. Alguns campos precisam de ajuste.")
        else:
            print("🔧 Precisa melhorar. Verifique o prompt ou processamento.")
            
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    teste_real_oab()