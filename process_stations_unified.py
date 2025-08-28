#!/usr/bin/env python3
"""
Script unificado para processamento completo de arquivos JSON das estações.

Este script combina as funcionalidades de:
1. Renomeação de arquivos baseada no tituloEstacao
2. Remoção do bloco _validation_issues
3. Remoção de campos de metadados

O script processa todos os arquivos .json recursivamente no diretório atual,
executando as operações em sequência e gerando um relatório detalhado.
"""

import os
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

def sanitize_filename(title):
    """Sanitiza o título para criar um nome de arquivo válido."""
    if not title:
        return "sem_titulo"

    # Remove caracteres especiais e substitui espaços por underscore
    sanitized = re.sub(r'[^\w\s-]', '', title)
    sanitized = re.sub(r'[\s]+', '_', sanitized)

    # Limita o comprimento a 100 caracteres
    if len(sanitized) > 100:
        sanitized = sanitized[:100]

    # Remove underscores no início e fim
    sanitized = sanitized.strip('_')

    # Se ficou vazio, usa um nome padrão
    if not sanitized:
        sanitized = "titulo_sanitizado"

    return sanitized.lower()

def remove_validation_issues(data):
    """
    Remove o bloco _validation_issues do JSON.

    Args:
        data (dict): Dados JSON carregados

    Returns:
        tuple: (dados_modificados, removido, erro)
    """
    try:
        if "_validation_issues" in data:
            del data["_validation_issues"]
            return data, True, None
        else:
            return data, False, "Campo _validation_issues não encontrado"
    except Exception as e:
        return data, False, f"Erro ao remover _validation_issues: {str(e)}"

def remove_metadata_fields(data):
    """
    Remove campos de metadados específicos do JSON.

    Args:
        data (dict): Dados JSON carregados

    Returns:
        tuple: (dados_modificados, campos_removidos, erro)
    """
    try:
        fields_to_remove = ['id', 'created_at', 'created_by', 'source', 'tema_original',
                           'especialidade_original', 'titulo', 'sync_status']
        removed_fields = []

        for field in fields_to_remove:
            if field in data:
                del data[field]
                removed_fields.append(field)

        return data, removed_fields, None
    except Exception as e:
        return data, [], f"Erro ao remover campos de metadados: {str(e)}"

def process_single_file(file_path):
    """
    Processa um arquivo JSON individual executando todas as operações.

    Args:
        file_path (str): Caminho para o arquivo

    Returns:
        tuple: (sucesso, operacoes_realizadas, erro)
    """
    operations = {
        'renamed': False,
        'validation_issues_removed': False,
        'metadata_fields_removed': [],
        'new_path': file_path
    }

    try:
        # Ler o conteúdo do arquivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse do JSON
        data = json.loads(content)

        # 1. RENOMEAÇÃO: Extrair título da estação e preparar novo nome
        titulo_estacao = data.get('tituloEstacao', '')
        original_path = file_path

        if titulo_estacao:
            new_filename = sanitize_filename(titulo_estacao) + '.json'
        else:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            new_filename = sanitize_filename(base_name) + '.json'

        # Caminho completo do novo arquivo
        dir_path = os.path.dirname(file_path)
        new_file_path = os.path.join(dir_path, new_filename)

        # Verificar se já existe um arquivo com o mesmo nome
        counter = 1
        while os.path.exists(new_file_path) and new_file_path != file_path:
            name_without_ext = os.path.splitext(new_filename)[0]
            new_filename = f"{name_without_ext}_{counter}.json"
            new_file_path = os.path.join(dir_path, new_filename)
            counter += 1

        # 2. REMOÇÃO DE _validation_issues
        data, validation_removed, validation_error = remove_validation_issues(data)
        if validation_error:
            return False, operations, validation_error

        # 3. REMOÇÃO DE CAMPOS DE METADADOS
        data, metadata_removed, metadata_error = remove_metadata_fields(data)
        if metadata_error:
            return False, operations, metadata_error

        # Salvar o arquivo modificado
        modified_content = json.dumps(data, indent=2, ensure_ascii=False)

        # Se o nome mudou, salvar no novo caminho, senão sobrescrever
        if new_file_path != file_path:
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            # Remover arquivo antigo
            os.remove(file_path)
            operations['renamed'] = True
            operations['new_path'] = new_file_path
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

        # Atualizar operações realizadas
        operations['validation_issues_removed'] = validation_removed
        operations['metadata_fields_removed'] = metadata_removed

        return True, operations, None

    except json.JSONDecodeError as e:
        return False, operations, f"Erro ao fazer parse do JSON: {str(e)}"
    except Exception as e:
        return False, operations, f"Erro geral: {str(e)}"

def find_json_files(directory):
    """Encontra todos os arquivos .json recursivamente no diretório."""
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def generate_report(processed_files, successful_operations, errors, start_time, end_time):
    """Gera um relatório detalhado das operações realizadas."""
    report = []
    report.append("=" * 80)
    report.append("RELATÓRIO DE PROCESSAMENTO UNIFICADO DE ARQUIVOS JSON")
    report.append("=" * 80)
    report.append("")

    # Informações gerais
    report.append(f"Data e hora do processamento: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Duração: {(end_time - start_time).total_seconds():.2f} segundos")
    report.append("")

    # Estatísticas gerais
    total_files = len(processed_files)
    successful_files = len(successful_operations)
    error_files = len(errors)

    report.append("ESTATÍSTICAS GERAIS:")
    report.append("-" * 40)
    report.append(f"Total de arquivos JSON encontrados: {total_files}")
    report.append(f"Arquivos processados com sucesso: {successful_files}")
    report.append(f"Arquivos com erro: {error_files}")
    report.append("")

    # Estatísticas das operações
    renamed_count = sum(1 for ops in successful_operations.values() if ops['renamed'])
    validation_removed_count = sum(1 for ops in successful_operations.values() if ops['validation_issues_removed'])
    metadata_removed_count = sum(1 for ops in successful_operations.values() if ops['metadata_fields_removed'])

    report.append("OPERAÇÕES REALIZADAS:")
    report.append("-" * 40)
    report.append(f"Arquivos renomeados: {renamed_count}")
    report.append(f"Blocos _validation_issues removidos: {validation_removed_count}")
    report.append(f"Arquivos com metadados removidos: {metadata_removed_count}")
    report.append("")

    # Detalhes dos arquivos processados com sucesso
    if successful_operations:
        report.append("ARQUIVOS PROCESSADOS COM SUCESSO:")
        report.append("-" * 50)
        for file_path, operations in successful_operations.items():
            report.append(f"Arquivo: {file_path}")
            if operations['renamed']:
                report.append(f"  → Renomeado para: {os.path.basename(operations['new_path'])}")
            if operations['validation_issues_removed']:
                report.append("  → Bloco _validation_issues removido")
            if operations['metadata_fields_removed']:
                report.append(f"  → Campos de metadados removidos: {', '.join(operations['metadata_fields_removed'])}")
            report.append("")

    # Erros encontrados
    if errors:
        report.append("ERROS ENCONTRADOS:")
        report.append("-" * 40)
        for file_path, error in errors.items():
            report.append(f"Arquivo: {file_path}")
            report.append(f"Erro: {error}")
            report.append("")

    # Resumo final
    report.append("=" * 80)
    report.append("RESUMO FINAL")
    report.append("=" * 80)
    report.append(f"Processamento concluído: {successful_files}/{total_files} arquivos processados com sucesso")

    if successful_files == total_files:
        report.append("✓ Todos os arquivos foram processados com sucesso!")
    else:
        report.append(f"⚠ {error_files} arquivo(s) apresentou(aram) erro(s)")

    return "\n".join(report)

def main():
    """Função principal do script."""
    start_time = datetime.now()
    current_dir = Path.cwd()

    print("INICIANDO PROCESSAMENTO UNIFICADO DE ARQUIVOS JSON")
    print("=" * 60)
    print(f"Diretório atual: {current_dir}")
    print(f"Hora de início: {start_time.strftime('%H:%M:%S')}")
    print()

    # Encontrar todos os arquivos JSON
    json_files = find_json_files(current_dir)
    print(f"Encontrados {len(json_files)} arquivos JSON")
    print()

    if not json_files:
        print("Nenhum arquivo JSON encontrado para processar.")
        return

    # Estatísticas
    successful_operations = {}
    errors = {}
    processed_count = 0

    # Processar cada arquivo
    for file_path in json_files:
        processed_count += 1
        relative_path = os.path.relpath(file_path, current_dir)

        print(f"[{processed_count}/{len(json_files)}] Processando: {relative_path}")

        success, operations, error = process_single_file(file_path)

        if success:
            successful_operations[file_path] = operations
            print("  ✓ Processado com sucesso")
            if operations['renamed']:
                print(f"    → Renomeado: {os.path.basename(operations['new_path'])}")
            if operations['validation_issues_removed']:
                print("    → _validation_issues removido")
            if operations['metadata_fields_removed']:
                print(f"    → Metadados removidos: {len(operations['metadata_fields_removed'])} campos")
        else:
            errors[file_path] = error
            print(f"  ✗ Erro: {error}")

        print()

    end_time = datetime.now()

    # Gerar relatório
    print("Gerando relatório final...")
    print()

    report = generate_report(json_files, successful_operations, errors, start_time, end_time)

    # Salvar relatório em arquivo
    report_filename = f"relatorio_processamento_unificado_{start_time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)

    print("=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)
    print(report)
    print()
    print(f"Relatório salvo em: {report_filename}")

if __name__ == "__main__":
    main()
