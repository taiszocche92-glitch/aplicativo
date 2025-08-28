import os
import json
import re
import shutil

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

def rename_station_files():
    """Renomeia arquivos JSON das estações baseado no campo tituloEstacao."""
    current_dir = os.getcwd()
    renamed_files = []
    errors = []
    processed_files = []

    print(f"Processando arquivos JSON em: {current_dir}")

    # Percorre recursivamente todos os arquivos .json
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                processed_files.append(file_path)

                try:
                    # Lê o conteúdo do arquivo JSON
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Extrai o título da estação
                    titulo_estacao = data.get('tituloEstacao', '')

                    if titulo_estacao:
                        # Sanitiza o título
                        new_filename = sanitize_filename(titulo_estacao) + '.json'
                    else:
                        # Fallback: usa o nome original sem extensão
                        base_name = os.path.splitext(file)[0]
                        new_filename = sanitize_filename(base_name) + '.json'

                    # Caminho completo do novo arquivo
                    new_file_path = os.path.join(root, new_filename)

                    # Verifica se já existe um arquivo com o mesmo nome
                    counter = 1
                    while os.path.exists(new_file_path) and new_file_path != file_path:
                        name_without_ext = os.path.splitext(new_filename)[0]
                        new_filename = f"{name_without_ext}_{counter}.json"
                        new_file_path = os.path.join(root, new_filename)
                        counter += 1

                    # Renomeia o arquivo se o nome mudou
                    if file_path != new_file_path:
                        os.rename(file_path, new_file_path)
                        renamed_files.append({
                            'original': file_path,
                            'novo': new_file_path,
                            'titulo': titulo_estacao if titulo_estacao else 'N/A (usou nome original)'
                        })
                        print(f"Renomeado: {file_path} -> {new_file_path}")
                    else:
                        print(f"Arquivo já tem o nome correto: {file_path}")

                except json.JSONDecodeError as e:
                    errors.append({
                        'arquivo': file_path,
                        'erro': f'Erro ao ler JSON: {str(e)}'
                    })
                    print(f"Erro ao processar {file_path}: {str(e)}")
                except Exception as e:
                    errors.append({
                        'arquivo': file_path,
                        'erro': f'Erro geral: {str(e)}'
                    })
                    print(f"Erro ao processar {file_path}: {str(e)}")

    return processed_files, renamed_files, errors

def generate_report(processed_files, renamed_files, errors):
    """Gera um relatório das operações realizadas."""
    report = []
    report.append("=" * 60)
    report.append("RELATÓRIO DE RENOMEAÇÃO DE ARQUIVOS JSON")
    report.append("=" * 60)
    report.append("")

    report.append(f"Total de arquivos JSON processados: {len(processed_files)}")
    report.append(f"Arquivos renomeados com sucesso: {len(renamed_files)}")
    report.append(f"Erros encontrados: {len(errors)}")
    report.append("")

    if renamed_files:
        report.append("ARQUIVOS RENOMEADOS:")
        report.append("-" * 40)
        for item in renamed_files:
            report.append(f"Original: {item['original']}")
            report.append(f"Novo: {item['novo']}")
            report.append(f"Título: {item['titulo']}")
            report.append("")

    if errors:
        report.append("ERROS ENCONTRADOS:")
        report.append("-" * 40)
        for error in errors:
            report.append(f"Arquivo: {error['arquivo']}")
            report.append(f"Erro: {error['erro']}")
            report.append("")

    if not renamed_files and not errors:
        report.append("Nenhum arquivo precisou ser renomeado.")
        report.append("")

    report.append("=" * 60)

    return "\n".join(report)

if __name__ == "__main__":
    print("Iniciando renomeação dos arquivos JSON das estações...")
    print()

    processed, renamed, errors = rename_station_files()

    print()
    print("Geração do relatório...")

    report = generate_report(processed, renamed, errors)

    # Salva o relatório em um arquivo
    with open('relatorio_renomeacao.txt', 'w', encoding='utf-8') as f:
        f.write(report)

    print("Relatório salvo em: relatorio_renomeacao.txt")
    print()
    print(report)
