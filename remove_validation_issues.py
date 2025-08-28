#!/usr/bin/env python3
"""
Script para remover o bloco _validation_issues do final dos arquivos JSON das estações.

Este script:
1. Lista recursivamente todos os arquivos .json no diretório atual
2. Para cada arquivo, identifica e remove o bloco que começa com a vírgula e "_validation_issues" até o final
3. Garante que o JSON resultante seja válido (removendo a vírgula anterior ao bloco)
4. Salva os arquivos modificados no mesmo local
5. Gera um relatório dos arquivos processados e possíveis erros
"""

import os
import json
import re
from pathlib import Path

def find_json_files(directory):
    """Encontra todos os arquivos .json recursivamente no diretório."""
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def remove_validation_issues(content):
    """
    Remove o bloco _validation_issues do JSON.

    Args:
        content (str): Conteúdo do arquivo JSON como string

    Returns:
        tuple: (conteúdo_modificado, sucesso, erro)
    """
    try:
        # Parse do JSON para manipulação estruturada
        data = json.loads(content)

        # Verificar se o campo _validation_issues existe
        if "_validation_issues" in data:
            # Remover o campo _validation_issues
            del data["_validation_issues"]

            # Converter de volta para JSON formatado
            modified_content = json.dumps(data, indent=2, ensure_ascii=False)

            return modified_content, True, None
        else:
            return content, False, "Campo _validation_issues não encontrado"

    except json.JSONDecodeError as e:
        return content, False, f"Erro ao fazer parse do JSON: {str(e)}"

def validate_json(content):
    """Valida se o conteúdo é um JSON válido."""
    try:
        json.loads(content)
        return True, None
    except json.JSONDecodeError as e:
        return False, str(e)

def process_file(file_path):
    """
    Processa um arquivo JSON individual.

    Args:
        file_path (str): Caminho para o arquivo

    Returns:
        tuple: (sucesso, modificado, erro)
    """
    try:
        # Ler o conteúdo do arquivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificar se o arquivo contém o bloco _validation_issues
        if '"_validation_issues"' not in content:
            return True, False, "Arquivo não contém bloco _validation_issues"

        # Remover o bloco _validation_issues
        modified_content, removed, remove_error = remove_validation_issues(content)

        if not removed:
            return False, False, remove_error

        # Validar o JSON modificado
        is_valid, validation_error = validate_json(modified_content)
        if not is_valid:
            return False, False, f"JSON inválido após modificação: {validation_error}"

        # Salvar o arquivo modificado
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        return True, True, None

    except Exception as e:
        return False, False, f"Erro ao processar arquivo: {str(e)}"

def main():
    """Função principal do script."""
    current_dir = Path.cwd()

    print(f"Processando arquivos JSON em: {current_dir}")
    print("=" * 60)

    # Encontrar todos os arquivos JSON
    json_files = find_json_files(current_dir)
    print(f"Encontrados {len(json_files)} arquivos JSON")

    if not json_files:
        print("Nenhum arquivo JSON encontrado.")
        return

    # Estatísticas
    processed = 0
    modified = 0
    errors = []

    # Processar cada arquivo
    for file_path in json_files:
        processed += 1
        relative_path = os.path.relpath(file_path, current_dir)

        print(f"\nProcessando: {relative_path}")

        success, was_modified, error = process_file(file_path)

        if success:
            if was_modified:
                print("  ✓ Modificado com sucesso")
                modified += 1
            else:
                print("  ✓ Já estava válido")
        else:
            print(f"  ✗ Erro: {error}")
            errors.append((relative_path, error))

    # Relatório final
    print("\n" + "=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)
    print(f"Total de arquivos processados: {processed}")
    print(f"Arquivos modificados: {modified}")
    print(f"Arquivos com erro: {len(errors)}")

    if errors:
        print("\nErros encontrados:")
        for file_path, error in errors:
            print(f"  - {file_path}: {error}")

    print(f"\nProcessamento concluído. {modified} arquivos foram modificados com sucesso.")

if __name__ == "__main__":
    main()
