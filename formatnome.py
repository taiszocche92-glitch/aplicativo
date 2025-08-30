#!/usr/bin/env python3
"""
Script para formatar o campo informação do contexto identificação paciente
"""
import json
import os
import glob
import re

class FormatadorIdentificacao:
    def __init__(self):
        self.diretorio_base = "ESTAÇÕES A SEREM AUDITADAS"

    def formatar_identificacao(self, texto):
        """Formata o texto de identificação do paciente em estrutura organizada"""
        if not isinstance(texto, str):
            return texto

        # Padrões comuns de identificação
        padroes = [
            r"([A-Za-zÀ-ÿ\s]+),\s*(\d+)\s*anos?,\s*([A-Za-zÀ-ÿ]+),\s*([A-Za-zÀ-ÿ\s]+)\s*e\s*([A-Za-zÀ-ÿ]+)",
            r"([A-Za-zÀ-ÿ\s]+),\s*(\d+)\s*anos?,\s*([A-Za-zÀ-ÿ]+),\s*([A-Za-zÀ-ÿ\s]+)",
            r"([A-Za-zÀ-ÿ\s]+),\s*(\d+)\s*anos?,\s*([A-Za-zÀ-ÿ]+)"
        ]

        for padrao in padroes:
            match = re.search(padrao, texto)
            if match:
                grupos = match.groups()
                nome = grupos[0].strip()
                idade = grupos[1].strip()
                genero = grupos[2].strip() if len(grupos) > 2 else ""
                profissao = grupos[3].strip() if len(grupos) > 3 else ""
                estado_civil = grupos[4].strip() if len(grupos) > 4 else ""

                # Monta estrutura formatada
                partes = []
                if nome: partes.append(f"Nome: {nome}")
                if idade: partes.append(f"Idade: {idade} anos")
                if genero: partes.append(f"Gênero: {genero}")
                if profissao: partes.append(f"Profissão: {profissao}")
                if estado_civil: partes.append(f"Estado Civil: {estado_civil}")

                return "\n".join(partes)

        # Se não conseguir parsear, retorna o texto original
        return texto

    def processar_arquivo(self, arquivo_json):
        """Processa um arquivo JSON para formatar identificação do paciente"""
        try:
            with open(arquivo_json, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            modificado = False

            if 'materiaisDisponiveis' in dados and 'informacoesVerbaisSimulado' in dados['materiaisDisponiveis']:
                for item in dados['materiaisDisponiveis']['informacoesVerbaisSimulado']:
                    if item.get('contextoOuPerguntaChave') == 'IDENTIFICAÇÃO DO PACIENTE':
                        if 'informacao' in item:
                            texto_original = item['informacao']
                            texto_formatado = self.formatar_identificacao(texto_original)

                            if texto_formatado != texto_original:
                                item['informacao'] = texto_formatado
                                modificado = True
                                print(f"📝 Formatação aplicada em: {arquivo_json}")
                                print(f"   Antes: {texto_original}")
                                print(f"   Depois: {texto_formatado}")

            if modificado:
                # Salva o arquivo
                with open(arquivo_json, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
                return True
            else:
                print(f"ℹ️ Nenhuma formatação necessária em: {arquivo_json}")
                return False

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo_json}: {str(e)}")
            return False

    def processar_todos_arquivos(self):
        """Processa todos os arquivos JSON no diretório"""
        if not os.path.exists(self.diretorio_base):
            print(f"❌ Diretório {self.diretorio_base} não encontrado")
            return

        arquivos_json = glob.glob(os.path.join(self.diretorio_base, "*.json"))
        processados = 0
        formatados = 0

        for arquivo in arquivos_json:
            processados += 1
            if self.processar_arquivo(arquivo):
                formatados += 1

        print(f"\n📊 Resumo:")
        print(f"   Arquivos processados: {processados}")
        print(f"   Arquivos formatados: {formatados}")

if __name__ == "__main__":
    formatador = FormatadorIdentificacao()
    formatador.processar_todos_arquivos()
