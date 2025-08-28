import json
import pathlib
import sys

def remove_metadata_fields(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        modified = False
        fields_to_remove = ['id', 'created_at', 'created_by', 'source', 'tema_original', 'especialidade_original', 'titulo', 'sync_status']

        for field in fields_to_remove:
            if field in data:
                del data[field]
                modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        return True, modified
    except Exception as e:
        return False, str(e)

def main():
    current_dir = pathlib.Path('.')
    json_files = list(current_dir.rglob('*.json'))

    processed = 0
    modified = 0
    errors = []

    for file_path in json_files:
        processed += 1
        success, result = remove_metadata_fields(file_path)
        if success:
            if result:  # modified is True
                modified += 1
        else:
            errors.append((str(file_path), result))

    print(f"Arquivos processados: {processed}")
    print(f"Arquivos modificados: {modified}")
    print(f"Erros: {len(errors)}")
    if errors:
        print("Erros encontrados:")
        for file, error in errors:
            print(f"  {file}: {error}")

if __name__ == "__main__":
    main()
