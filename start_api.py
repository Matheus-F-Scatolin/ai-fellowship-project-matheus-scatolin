#!/usr/bin/env python3
"""
Script para iniciar a API de extração de dados
"""

import uvicorn
import os
import sys

def verificar_dependencias():
    """Verifica se as dependências estão instaladas"""
    try:
        from core.api_server import app
        print("✅ Todas as dependências estão disponíveis!")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("💡 Execute: pip install -r requirements.txt")
        return False

def verificar_openai_key():
    """Verifica se a chave da OpenAI está configurada"""
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY não encontrada!")
        print("💡 Crie um arquivo .env com:")
        print("   OPENAI_API_KEY=sua_chave_aqui")
        print("\n⚠️  A API funcionará, mas as extrações com LLM falharão!")
        return False
    else:
        print("✅ OPENAI_API_KEY configurada!")
        return True

def main():
    print("🚀 INICIANDO API DE EXTRAÇÃO DE DADOS")
    print("=" * 50)
    
    # Verificações
    if not verificar_dependencias():
        sys.exit(1)
    
    verificar_openai_key()
    
    print("\n📡 Iniciando servidor API...")
    print("🌐 URL: http://localhost:8000")
    print("📚 Documentação: http://localhost:8000/docs")
    print("🔧 Para parar: Ctrl+C")
    print("-" * 50)
    
    try:
        # Importar app
        from core.api_server import app
        
        # Iniciar servidor
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,  # Desabilitar reload para produção
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n⏹️  Servidor parado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()