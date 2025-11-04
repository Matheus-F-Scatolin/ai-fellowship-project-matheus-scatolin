#!/usr/bin/env python3
"""
Script para executar os unit tests do API Server
"""

import subprocess
import sys
import os

def check_dependencies():
    """Verifica se as dependências necessárias estão instaladas"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'pytest'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Pacotes ausentes: {missing_packages}")
        print("\n📦 Para instalar as dependências, execute:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Todas as dependências estão instaladas!")
    return True

def run_tests():
    """Executa os unit tests"""
    if not check_dependencies():
        return False
        
    print("\n🧪 Executando unit tests para API Server...")
    print("=" * 60)
    
    try:
        # Adicionar o diretório raiz ao PYTHONPATH
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
        
        # Executar os testes
        result = subprocess.run([
            sys.executable, '-m', 'unittest', 
            'unit_tests.test_api_server', 
            '-v'
        ], env=env, cwd=project_root)
        
        if result.returncode == 0:
            print("\n✅ Todos os testes passaram!")
            return True
        else:
            print("\n❌ Alguns testes falharam!")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)