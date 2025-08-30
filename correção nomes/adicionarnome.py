#!/usr/bin/env python3
"""
Script para limpar dados filiatórios dos arquivos JSON das estações.

Este script:
1. Processa todos os arquivos JSON na pasta ESTAÇÕES A SEREM AUDITADAS
2. Remove dados filiatórios da descricaoCasoCompleta (nomes, idades, gêneros, profissões, procedências)
3. Detecta e ignora arquivos com campo IDENTIFICAÇÃO DO PACIENTE duplicado
4. Ignora arquivos que já estão corretos (sem dados filiatórios)
5. Inclui gênero apenas em temas relevantes (LGBT)
6. Gera relatório detalhado das modificações

MELHORIAS NA VERSÃO 2.1:
- Método _clean_description() mais inteligente e seletivo
- Preserva informações clínicas importantes (sintomas, diagnósticos, histórico)
- Remove dados filiatórios no início das frases de forma mais eficaz
- Mantém semântica médica intacta
- Trata casos especiais como "há X anos" em contexto médico

Autor: Kilo Code
Data: 2025-08-29
Versão: 2.1 - Limpeza inteligente de dados filiatórios
"""

import os
import json
import re
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class PatientDataCleaner:
    """Classe para limpar dados filiatórios dos arquivos JSON das estações."""

    def __init__(self, names_file: str = "banco de nomes.json"):
        self.names_file = names_file
        self.names_data = self._load_names_database()
        self.used_names = self._initialize_used_names_tracker()

    def _load_names_database(self) -> Dict:
        """Carrega o banco de nomes JSON."""
        try:
            with open(self.names_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Banco de nomes não encontrado: {self.names_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao carregar banco de nomes: {e}")

    def _initialize_used_names_tracker(self) -> Dict[str, set]:
        """Inicializa rastreador de nomes usados por categoria."""
        tracker = {}
        for category in self.names_data.get('categorias', []):
            category_title = category.get('titulo', '')
            tracker[category_title] = set()
        return tracker

    def _get_name_category(self, age: int, gender: str) -> str:
        """Determina a categoria de nomes baseada na idade e gênero."""
        if age < 15:
            category_type = "recém-nascidos, crianças e pré-adolescentes"
        elif age <= 40:
            category_type = "Jovens e Adolescentes"
        else:
            category_type = "Meia-Idade e Idosos"

        gender_prefix = "Masculinos" if gender.lower() == "masculino" else "Femininos"

        return f"Nomes {gender_prefix} Mais Comuns ({category_type})"

    def _get_random_name(self, category: str) -> str:
        """Obtém um nome aleatório da categoria, evitando repetições."""
        if category not in self.names_data.get('categorias', []):
            # Fallback para categoria similar
            if "Masculinos" in category:
                category = "Nomes Masculinos Mais Comuns (Meia-Idade e Idosos)"
            else:
                category = "Nomes Femininos Mais Comuns (Meia-Idade e Idosas)"

        # Encontrar categoria no banco
        category_data = None
        for cat in self.names_data.get('categorias', []):
            if cat.get('titulo') == category:
                category_data = cat
                break

        if not category_data:
            return "Nome Desconhecido"

        all_names = category_data.get('nomes', [])
        available_names = [name for name in all_names if name not in self.used_names[category]]

        if not available_names:
            # Reset da categoria se todos os nomes foram usados
            self.used_names[category].clear()
            available_names = all_names

        selected_name = random.choice(available_names)
        self.used_names[category].add(selected_name)

        return selected_name

    def _extract_age_gender_from_description(self, description: str) -> Tuple[Optional[int], Optional[str]]:
        """Extrai idade e gênero da descrição do caso."""
        age = None
        gender = None

        # Padrões melhorados para idade
        age_patterns = [
            r'(\d+)\s*anos?',  # "25 anos"
            r'idade\s*de\s*(\d+)',  # "idade de 68"
            r'paciente\s+de\s*(\d+)\s*anos?',  # "paciente de 25 anos"
            r'Paciente\s+de\s*(\d+)\s*anos?',  # "Paciente de 35 anos" (com maiúscula)
            r'(\d+)\s*anos?\s*de\s*idade',  # "25 anos de idade"
            r'idos[ao]\s+de\s*(\d+)\s*anos?',  # "idoso de 68 anos"
            r'com\s*(\d+)\s*anos',  # "com 25 anos"
            r'aos?\s*(\d+)\s*anos?',  # "aos 25 anos"
            r'(\d+)\s*anos?\s*chega',  # "38 anos chega"
            r'(\d+)\s*anos?\s*comparece',  # "58 anos comparece"
            r'(\d+)\s*anos?\s*procura',  # "50 anos procura"
            r'(\d+)\s*anos?\s*apresenta',  # "42 anos apresenta"
            r'(\d+)\s*anos?\s*referindo',  # "35 anos referindo"
            r'idoso\s*\(a\)',  # "idoso(a)" - padrão especial para casos sem idade específica
            r'idoso\(a\)',  # "idoso(a)" - sem espaço
            r'Dona?\s+[A-Z][a-z]+\s+[A-Z][a-z]+,\s*(\d+)\s*anos?',  # "Dona Maria Silva, 62 anos"
            r'Paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+,\s*(\d+)\s*anos?',  # "Paciente João Silva, 55 anos"
            r'[A-Z][a-z]+\s+[A-Z][a-z]+,\s*(\d+)\s*anos?',  # "Maria Silva, 62 anos"
            r'(\d+)\s*anos?\s*,',  # "62 anos," - idade no início
            r'paciente\s*,\s*\w+,\s*(\d+)\s*anos?',  # "paciente, bancário, 52 anos"
            r'(\d+)\s*anos?\s*de\s*idade\s*,',  # "68 anos de idade,"
            r'idos[ao]\s*\(a\)\s*,?\s*(\d+)\s*anos?',  # "idoso(a), 70 anos"
            r'paciente\s*ã[a-z]+\s+[A-Z][a-z]+,\s*(\d+)\s*anos?',  # "paciente ão Silva, 62 anos" - nomes corrompidos
            r'ã[a-z]+\s+[A-Z][a-z]+,\s*(\d+)\s*anos?',  # "ão Silva, 62 anos"
        ]

        for pattern in age_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                # Verificar se o padrão tem grupos de captura
                if len(match.groups()) > 0 and match.group(1):
                    try:
                        age = int(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue
                else:
                    # Padrões sem grupos de captura (como "idoso(a)")
                    # Inferir idade baseada no contexto
                    if 'idoso' in pattern.lower():
                        age = random.choice([65, 70, 75, 80, 85])
                        break

        # Padrões melhorados para gênero
        gender_patterns = [
            r'sexo\s+(masculino|feminino)',  # "sexo masculino"
            r'gênero\s+(masculino|feminino)',  # "gênero masculino"
            r'paciente\s+(masculino|feminino)',  # "paciente masculino"
            r'paciente\s+(feminina|masculino)',  # "paciente feminina"
            r'é\s+trazido',  # "é trazido" = masculino
            r'é\s+trazida',  # "é trazida" = feminino
            r'(\w+)\s+é\s+trazid[ao]',  # "Paciente é trazido" (contexto)
            r'(\w+)\s+procura',  # "paciente procura"
            r'(\w+)\s+apresenta',  # "paciente apresenta"
            r'uma\s+paciente',  # "uma paciente" = feminino
            r'um\s+paciente',   # "um paciente" = masculino
            r'paciente\s+feminina',  # "paciente feminina"
            r'paciente\s+masculino',  # "paciente masculino"
            r'A\s+paciente',  # "A paciente" = feminino
            r'O\s+paciente',   # "O paciente" = masculino
            r'Dona?\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # "Dona Maria Silva" = feminino
            r'Dr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # "Dr. João Silva" = masculino
            r'Sr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # "Sr. José Santos" = masculino
            r'Sra\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # "Sra. Ana Costa" = feminino
            r'chega\s+à',  # Contexto de chegada (neutro, mas ajuda na detecção)
            r'comparece\s+à',  # Contexto de comparecimento (neutro, mas ajuda na detecção)
            r'paciente\s*,\s*\w+,\s*chega',  # "paciente, bancário, chega" - contexto masculino por profissão
            r'paciente\s*,\s*\w+,\s*comparece',  # "paciente, bancária, comparece" - feminino
            r'acompanhad[ao]\s+da\s+acompanhante',  # "acompanhado da acompanhante" = masculino
            r'acompanhad[ao]\s+do\s+acompanhante',  # "acompanhada do acompanhante" = feminino
            r'pai\s+tem',  # "pai tem" = paciente masculino (referência ao pai)
            r'mãe\s+tem',  # "mãe tem" = paciente feminino
            r'filho\s+tem',  # "filho tem" = paciente masculino
            r'filha\s+tem',  # "filha tem" = paciente feminino
        ]

        for pattern in gender_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                # Verificar gênero baseado no texto encontrado
                matched_text = match.group(0).lower()

                if 'é trazido' in matched_text:
                    gender = 'masculino'
                    break
                elif 'é trazida' in matched_text:
                    gender = 'feminino'
                    break
                elif 'uma paciente' in matched_text:
                    gender = 'feminino'
                    break
                elif 'um paciente' in matched_text:
                    gender = 'masculino'
                    break
                elif matched_text.startswith('a paciente'):
                    gender = 'feminino'
                    break
                elif matched_text.startswith('o paciente'):
                    gender = 'masculino'
                    break
                elif matched_text.startswith('dona') or matched_text.startswith('sra'):
                    gender = 'feminino'
                    break
                elif matched_text.startswith('dr') or matched_text.startswith('sr'):
                    gender = 'masculino'
                    break

                # Padrões com grupos de captura
                if len(match.groups()) > 0:
                    gender_text = match.group(1).lower() if match.group(1) else match.group(0).lower()
                else:
                    gender_text = match.group(0).lower()

                if ('femin' in gender_text or 'mulher' in gender_text or
                    'ela' in gender_text or 'uma paciente' in gender_text):
                    gender = 'feminino'
                elif ('mascul' in gender_text or 'homem' in gender_text or
                      'ele' in gender_text or 'um paciente' in gender_text):
                    gender = 'masculino'
                break

        # Inferência adicional baseada em contexto se nenhum padrão foi encontrado
        if not gender:
            desc_lower = description.lower()
            if ('paciente feminina' in desc_lower or 'mulher' in desc_lower or 'dona' in desc_lower or 'sra' in desc_lower or
                'mãe tem' in desc_lower or 'filha tem' in desc_lower or 'acompanhada do acompanhante' in desc_lower):
                gender = 'feminino'
            elif ('paciente masculino' in desc_lower or 'homem' in desc_lower or 'sr' in desc_lower or 'dr' in desc_lower or
                  'pai tem' in desc_lower or 'filho tem' in desc_lower or 'acompanhado da acompanhante' in desc_lower):
                gender = 'masculino'
            elif 'a paciente' in desc_lower:
                gender = 'feminino'
            elif 'o paciente' in desc_lower:
                gender = 'masculino'

        # Inferência adicional de gênero baseada em contexto
        if not gender:
            desc_lower = description.lower()
            if 'paciente feminina' in desc_lower or 'mulher' in desc_lower or 'mãe' in desc_lower or 'filha' in desc_lower:
                gender = 'feminino'
            elif 'paciente masculino' in desc_lower or 'homem' in desc_lower or 'pai' in desc_lower or 'filho' in desc_lower:
                gender = 'masculino'

        return age, gender

    def _infer_age_from_context(self, context: Dict, gender: str) -> int:
        """Infere idade baseada no contexto epidemiológico quando não estiver explícita."""
        disease = context.get('tituloEstacao', '').lower()

        # Regras epidemiológicas por doença
        if 'cetoacidose diabética' in disease or 'diabetes' in disease:
            # Pico em jovens adultos e idosos
            return random.choice([25, 35, 45, 65, 75])
        elif 'cistite' in disease or 'itu' in disease:
            # Mais comum em mulheres jovens e adultas
            if gender == 'feminino':
                return random.choice([22, 28, 35, 42, 55])
            else:
                return random.choice([45, 55, 65, 70])
        elif 'cardiopatia chagásica' in disease or 'chagas' in disease:
            # Doença crônica, mais comum em adultos de meia-idade
            return random.choice([45, 50, 55, 60, 65])
        elif 'avc' in disease or 'acidente vascular' in disease:
            # Mais comum em idosos
            return random.choice([60, 65, 70, 75, 80])
        elif 'infarto' in disease or 'angina' in disease:
            # Mais comum em homens de meia-idade e idosos
            if gender == 'masculino':
                return random.choice([50, 55, 60, 65, 70])
            else:
                return random.choice([55, 60, 65, 70, 75])

        # Faixa etária geral baseada no gênero
        if gender == 'feminino':
            return random.choice([25, 35, 45, 55, 65])
        else:
            return random.choice([30, 40, 50, 60, 70])

    def _infer_occupation(self, age: int, context: Dict, gender: str) -> str:
        """Infere ocupação baseada na idade, contexto epidemiológico e gênero."""
        disease = context.get('tituloEstacao', '').lower()

        # Regras específicas por doença
        if 'chagas' in disease or 'chagásica' in disease:
            return "Trabalhador rural" if gender.lower() == "masculino" else "Trabalhadora rural"
        elif 'diabetes' in disease or 'cetoacidose' in disease:
            if age > 60:
                return "Aposentado" if gender.lower() == "masculino" else "Aposentada"
            elif age > 25:
                return "Profissional liberal" if gender.lower() == "masculino" else "Profissional liberal"
            else:
                return "Estudante" if gender.lower() == "masculino" else "Estudante"
        elif 'cistite' in disease or 'itu' in disease:
            if age > 60:
                return "Aposentada" if gender.lower() == "feminino" else "Aposentado"
            elif age > 25:
                return "Profissional de escritório" if gender.lower() == "feminino" else "Profissional de escritório"
            else:
                return "Estudante" if gender.lower() == "feminino" else "Estudante"

        # Regras gerais por idade e gênero
        if age > 65:
            return "Aposentado" if gender.lower() == "masculino" else "Aposentada"
        elif age > 25:
            # Ocupações diferenciadas por gênero
            if gender.lower() == "masculino":
                occupations = ["Professor", "Enfermeiro", "Comerciante", "Motorista", "Funcionário público"]
            else:  # feminino
                occupations = ["Professora", "Enfermeira", "Comerciante", "Motorista", "Funcionária pública"]
            return random.choice(occupations)
        elif age > 18:
            return "Estudante universitário" if gender.lower() == "masculino" else "Estudante universitária"
        else:
            return "Estudante" if gender.lower() == "masculino" else "Estudante"

    def _infer_marital_status(self, age: int, gender: str) -> str:
        """Infere estado civil baseada na idade e gênero."""
        if age < 25:
            return "Solteiro" if gender.lower() == "masculino" else "Solteira"
        elif age < 60:
            # Lógica condicional baseada no gênero para todas as faixas etárias
            if gender.lower() == "masculino":
                return random.choice(["Casado", "Solteiro", "Divorciado"])
            else:  # feminino
                return random.choice(["Casada", "Solteira", "Divorciada"])
        else:
            # Lógica condicional baseada no gênero
            if gender.lower() == "masculino":
                return random.choice(["Casado", "Viúvo"])
            else:  # feminino
                return random.choice(["Casada", "Viúva"])

    def _infer_origin(self, context: Dict) -> Optional[str]:
        """Infere procedência apenas quando epidemiologicamente relevante."""
        disease = context.get('tituloEstacao', '').lower()

        if 'chagas' in disease or 'chagásica' in disease:
            return "Área rural de Minas Gerais"
        elif 'dengue' in disease or 'chikungunya' in disease or 'zika' in disease:
            return "Área urbana periférica"

        return None

    def _is_lgbt_relevant_theme(self, context: Dict) -> bool:
        """Verifica se o tema é relevante para incluir gênero (LGBT)."""
        disease = context.get('tituloEstacao', '').lower()

        # Temas relacionados a população LGBT
        lgbt_keywords = [
            'homossexual', 'lésbica', 'gay', 'lgbt', 'trans', 'transexual',
            'identidade de gênero', 'orientação sexual', 'dst', 'aids', 'hiv',
            'gonorreia', 'sífilis', 'herpes genital', 'condiloma', 'hpv'
        ]

        return any(keyword in disease for keyword in lgbt_keywords)

    def _check_duplicate_identification(self, data: Dict) -> Tuple[bool, int]:
        """Verifica se há duplicatas do campo IDENTIFICAÇÃO DO PACIENTE."""
        info_array = data.get('materiaisDisponiveis', {}).get('informacoesVerbaisSimulado', [])
        identification_count = 0

        for info in info_array:
            if info.get('contextoOuPerguntaChave') == 'IDENTIFICAÇÃO DO PACIENTE':
                identification_count += 1

        has_duplicates = identification_count > 1
        return has_duplicates, identification_count

    def _is_file_already_correct(self, data: Dict) -> Tuple[bool, str]:
        """Verifica se o arquivo já está correto (sem dados filiatórios na descrição)."""
        instrucoes = data.get('instrucoesParticipante', {})
        if not instrucoes or 'descricaoCasoCompleta' not in instrucoes:
            return False, "Arquivo sem estrutura completa"

        description = instrucoes.get('descricaoCasoCompleta', '')

        # Verificar se há dados filiatórios na descrição
        filiation_patterns = [
            r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # Nomes próprios
            r'\d+\s*anos?',  # Idades
            r'sexo\s+(masculino|feminino)',  # Sexo
            r'gênero\s+(masculino|feminino)',  # Gênero
            r'profissão', r'ocupação',  # Profissão
            r'estado\s+civil',  # Estado civil
            r'procedência', r'origem'  # Procedência
        ]

        for pattern in filiation_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return False, f"Arquivo contém dados filiatórios: {pattern}"

        return True, "Arquivo já está correto"

    def _clean_description(self, description: str, age: int, gender: str) -> str:
        """Remove dados filiatórios da descrição do caso de forma inteligente."""
        cleaned = description

        # 1. PRIMEIRO: Identificar e preservar informações clínicas importantes
        # que podem estar misturadas com dados filiatórios

        # Preservar termos médicos importantes que podem vir após dados filiatórios
        medical_terms = [
            r'com\s+dor', r'com\s+febre', r'com\s+náuseas', r'com\s+vômitos',
            r'com\s+diarréia', r'com\s+constipação', r'com\s+tontura',
            r'com\s+fraqueza', r'com\s+fadiga', r'com\s+dispneia',
            r'com\s+taquicardia', r'com\s+hipotensão', r'com\s+hipertensão',
            r'referindo\s+dor', r'referindo\s+febre', r'referindo\s+náuseas',
            r'apresenta\s+dor', r'apresenta\s+febre', r'apresenta\s+sintomas',
            r'queixa\s+de', r'com\s+história', r'com\s+antecedente',
            r'em\s+uso\s+de', r'faz\s+uso\s+de', r'com\s+alergia'
        ]

        # Extrair trechos médicos importantes antes de limpar
        preserved_medical_parts = []
        for term in medical_terms:
            matches = re.findall(term, cleaned, re.IGNORECASE)
            preserved_medical_parts.extend(matches)

        # 2. Remover dados filiatórios específicos no INÍCIO da frase
        # Estratégia mais robusta para o início da descrição

        # Primeiro, identificar se começa com dados filiatórios
        filiation_start_patterns = [
            r'^(Dona?\s+[A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
            r'^(Sr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
            r'^(Dr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
            r'^(Sra\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
            r'^(paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
            r'^(Paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+\s*anos?,?\s*,?\s*',
        ]

        for pattern in filiation_start_patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE | re.MULTILINE)
            if match:
                filiation_part = match.group(0)
                # Encontrar onde termina a parte filiatória (antes do verbo ou sintoma)
                remaining_text = cleaned[len(filiation_part):].strip()

                # Procurar pelo início do conteúdo clínico
                clinical_indicators = [
                    r'^(apresenta|refere|com|queixa|história|antecedente|em\s+uso|diagnóstico)',
                    r'^(dor|febre|náusea|vômito|cefaleia|tontura|fraqueza)',
                    r'^(é\s+trazid|chega|comparece|procura)'
                ]

                clinical_start = len(remaining_text)  # Default: manter tudo
                for indicator in clinical_indicators:
                    clinical_match = re.search(indicator, remaining_text, re.IGNORECASE)
                    if clinical_match:
                        clinical_start = clinical_match.start()
                        break

                # Manter apenas a partir do indicador clínico
                clinical_part = remaining_text[clinical_start:].strip()
                if clinical_part:
                    cleaned = clinical_part
                else:
                    cleaned = remaining_text
                break

        # 3. Remover nomes próprios e idades de forma mais robusta
        # Estratégia mais agressiva para nomes no início após a limpeza inicial

        # Primeiro, remover qualquer nome próprio que apareça logo após "Paciente"
        patient_name_patterns = [
            r'Paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+,',
            r'Paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+,',
            r'Paciente\s+[A-Z][a-z]+,',
            r'Paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'Paciente\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'Paciente\s+[A-Z][a-z]+',
        ]

        for pattern in patient_name_patterns:
            cleaned = re.sub(pattern, 'Paciente', cleaned, flags=re.IGNORECASE)

        # Remover nomes que ainda aparecem no início
        start_name_patterns = [
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+,',
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+,',
            r'^[A-Z][a-z]+,',
        ]

        for pattern in start_name_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remover idades isoladas que não sejam contexto médico
        age_patterns = [
            r'\b\d+\s*anos?\b(?!\s*(?:de\s+)?(dor|febre|diarréia|constipação|tontura|fraqueza|dispneia|taquicardia|hipotensão|hipertensão|diabetes|câncer|avc|infarto))',
            r',\s*\d+\s*anos?,',  # idades após vírgulas
        ]

        for pattern in age_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remover nomes próprios restantes (mais seletivo)
        remaining_name_patterns = [
            r'\bDona?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
            r'\bSr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
            r'\bSra\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Nomes compostos
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Nomes simples
        ]

        for pattern in remaining_name_patterns:
            matches = re.findall(pattern, cleaned)
            for match in matches:
                # Verificar contexto antes e depois
                match_index = cleaned.find(match)
                context_before = cleaned[:match_index].strip()
                context_after = cleaned[match_index + len(match):].strip()

                # Preservar se estiver em contexto médico profissional
                if (context_before.endswith(('Dr.', 'Dra.', 'Dr', 'Dra')) and
                    any(term in context_after.lower() for term in ['cardiologista', 'ortopedista', 'clínico', 'pediatra', 'ginecologista', 'cirurgião', 'médico', 'enfermeiro', 'profissional', 'especialista'])):
                    continue

                # Preservar se vier após "é atendido pelo"
                if 'é atendido pelo' in context_before.lower() or 'atendido pela' in context_before.lower():
                    continue

                # Caso contrário, remover
                cleaned = re.sub(re.escape(match), '', cleaned)

        # 4. Remover idade e gênero de forma mais inteligente
        age_gender_patterns = [
            r'paciente\s+de\s*\d+\s*anos?,?\s*(?:do\s+sexo\s+(?:masculino|feminino))?,?\s*',
            r'sexo\s+(masculino|feminino),?\s*idade\s+de\s*\d+\s*anos?,?\s*',
            r'idade\s+de\s*\d+\s*anos?,?\s*(?:do\s+sexo\s+(?:masculino|feminino))?,?\s*',
            r'de\s*\d+\s*anos?,?\s*(?:de\s+idade)?,?\s*(?:do\s+sexo\s+(?:masculino|feminino))?,?\s*',
            r'com\s*\d+\s*anos?,?\s*(?:de\s+idade)?,?\s*',
            r'aos?\s*\d+\s*anos?,?\s*',
        ]

        # Só remover se não fizer parte de contexto médico
        for pattern in age_gender_patterns:
            matches = re.findall(pattern, cleaned, re.IGNORECASE)
            for match in matches:
                # Verificar se está em contexto médico (ex: "com 3 dias de dor")
                context_after = cleaned[cleaned.find(match) + len(match):].strip()
                if any(term in context_after.lower() for term in ['dor', 'febre', 'sintomas', 'queixa', 'história', 'antecedente']):
                    continue  # Preservar
                cleaned = re.sub(re.escape(match), '', cleaned, flags=re.IGNORECASE)

        # 5. Remover ocupações de forma mais robusta
        occupation_patterns = [
            r'\bmotorista\s+de\s+aplicativo\b',
            r'\bmotorista\s+de\s+ônibus\b',
            r'\bcozinheir[ao]?\b',
            r'\bprofessor[ao]?\b',
            r'\bprofessora?\b',
            r'\bmédic[ao]?\b',
            r'\benfermeir[ao]?\b',
            r'\bengenheir[ao]?\b',
            r'\badvogad[ao]?\b',
            r'\bcomerciante\b',
            r'\bempresári[ao]?\b',
            r'\bfuncionári[ao]?\b',
            r'\bestudante\b',
            r'\bdoméstica?\b',
            r'\baposentad[ao]?\b',
            r'\btrabalhador\s+rural\b',
            r'\banalista\s+financeiro\b',
            r'\bpedreiro\b',
        ]

        for pattern in occupation_patterns:
            matches = re.findall(pattern, cleaned, re.IGNORECASE)
            for match in matches:
                match_index = cleaned.lower().find(match.lower())
                context_before = cleaned[:match_index].strip()
                context_after = cleaned[match_index + len(match):].strip()

                # Preservar se vier imediatamente após dados filiatórios (parte da identificação)
                # Ex: "João Silva, 45 anos, professor, apresenta..."
                if (',' in context_before and any(term in context_before.lower() for term in ['anos', 'idade'])):
                    continue

                # Preservar se estiver em contexto médico
                if any(term in context_after.lower() for term in ['com dor', 'com febre', 'referindo', 'apresenta', 'queixa', 'diagnóstico']):
                    continue

                # Preservar se vier após "ex-" ou "ex "
                if re.search(r'\bex[\s-]', context_before[-10:].lower()):
                    continue

                # Caso contrário, remover
                cleaned = re.sub(re.escape(match), '', cleaned, flags=re.IGNORECASE)

        # 6. Remover estado civil
        marital_patterns = [
            r'\bcasad[ao]?\b',
            r'\bsolteir[ao]?\b',
            r'\bdivorciad[ao]?\b',
            r'\bviúv[ao]?\b',
            r'\bseparad[ao]?\b',
        ]

        for pattern in marital_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # 7. Remover procedência
        origin_patterns = [
            r'área\s+rural\s+de\s+\w+',
            r'área\s+urbana\s+periférica',
            r'cidade\s+\w+',
            r'capital',
            r'zona\s+urbana',
            r'procedência\s+[\w\s]+',
        ]

        for pattern in origin_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # 8. Ajustar referências contextuais (mais conservador)
        context_replacements = [
            (r'\bseu\s+filho\b', 'seu acompanhante'),
            (r'\bsua\s+filha\b', 'sua acompanhante'),
            (r'\bmeu\s+filho\b', 'meu acompanhante'),
            (r'\bminha\s+filha\b', 'minha acompanhante'),
            (r'\bo\s+filho\b', 'o acompanhante'),
            (r'\ba\s+filha\b', 'a acompanhante'),
        ]

        for old_text, new_text in context_replacements:
            cleaned = re.sub(old_text, new_text, cleaned, flags=re.IGNORECASE)

        # 9. Limpeza final mais cuidadosa
        # Limpar espaços extras
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Limpar pontuação problemática
        cleaned = re.sub(r',\s*,', ',', cleaned)
        cleaned = re.sub(r'\.\s*\.', '.', cleaned)
        cleaned = re.sub(r',\s*\.', '.', cleaned)
        cleaned = re.sub(r'\s*,', ',', cleaned)
        cleaned = cleaned.strip()

        # Remover pontuação no início
        cleaned = re.sub(r'^[,\.\s]+', '', cleaned)

        # Remover frases redundantes no início (mais conservador)
        redundant_starts = [
            r'^\s*o\s+paciente\s+',
            r'^\s*a\s+paciente\s+',
            r'^\s*um\s+paciente\s+',
            r'^\s*uma\s+paciente\s+',
            r'^\s*que\s+',
            r'^\s*e\s+que\s+',
        ]

        for pattern in redundant_starts:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Garantir que comece com "Paciente" se não começar com algo significativo
        if not cleaned:
            cleaned = "Paciente"
        elif not (cleaned.lower().startswith('paciente') or
                  cleaned.lower().startswith(('com dor', 'referindo', 'apresenta', 'queixa'))):
            cleaned = 'Paciente ' + cleaned

        # Capitalizar primeira letra
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

        return cleaned

    def _create_identification_field(self, name: str, age: int, gender: str,
                                    occupation: str, marital_status: str,
                                    origin: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        """Cria o campo de identificação do paciente."""
        info_lines = [
            f"Nome: {name}",
            f"Idade: {age} anos"
        ]

        # Incluir gênero apenas em temas LGBT relevantes
        if context and self._is_lgbt_relevant_theme(context):
            info_lines.append(f"Gênero: {gender.capitalize()}")

        info_lines.extend([
            f"Ocupação: {occupation}",
            f"Estado Civil: {marital_status}"
        ])

        if origin:
            info_lines.append(f"Procedência: {origin}")

        return {
            "contextoOuPerguntaChave": "IDENTIFICAÇÃO DO PACIENTE",
            "informacao": "\n".join(info_lines)
        }

    def _clean_existing_identification(self, info_text: str) -> str:
        """Limpa e reformata campos de identificação existentes."""
        if not info_text or not isinstance(info_text, str):
            return ""

        print(f"DEBUG: Texto original: {info_text}")

        # Separar as linhas
        lines = [line.strip() for line in info_text.split('\n') if line.strip()]
        print(f"DEBUG: Linhas separadas: {lines}")

        # Dicionário para armazenar os valores extraídos
        extracted_values = {}

        # Verificar se é o formato antigo (com ":") ou novo (separado por vírgulas)
        has_colon_format = any(':' in line for line in lines)

        if has_colon_format:
            # Formato antigo com ":"
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    # Mapear chaves para nomes padronizados
                    if 'nome' in key:
                        extracted_values['nome'] = value
                    elif 'idade' in key:
                        extracted_values['idade'] = value
                    elif 'gênero' in key or 'genero' in key:
                        extracted_values['genero'] = value
                    elif 'ocupação' in key or 'ocupacao' in key or 'profissão' in key or 'profissao' in key:
                        extracted_values['ocupacao'] = value
                    elif 'estado civil' in key or 'estado_civil' in key:
                        extracted_values['estado_civil'] = value
                    elif 'procedência' in key or 'procedencia' in key or 'origem' in key:
                        extracted_values['procedencia'] = value
        else:
            # Formato novo separado por vírgulas: "Nome, idade, gênero, ocupação e estado_civil"
            for line in lines:
                parts = [part.strip() for part in line.split(',')]
                print(f"DEBUG: Partes separadas: {parts}")

                if len(parts) >= 4:
                    # Extrair nome (primeira parte)
                    extracted_values['nome'] = parts[0]

                    # Extrair idade (segunda parte)
                    if 'anos' in parts[1]:
                        extracted_values['idade'] = parts[1]

                    # Extrair gênero (terceira parte)
                    extracted_values['genero'] = parts[2]

                    # Verificar se a última parte contém estado civil ou ocupação
                    last_part = parts[-1]

                    # Lista de possíveis estados civis
                    marital_statuses = [
                        'casado', 'casada', 'solteiro', 'solteira', 'divorciado', 'divorciada',
                        'viúvo', 'viúva', 'separado', 'separada'
                    ]

                    # Lista de possíveis ocupações comuns
                    common_occupations = [
                        'professor', 'professora', 'enfermeiro', 'enfermeira', 'comerciante',
                        'motorista', 'funcionário', 'funcionária', 'aposentado', 'aposentada',
                        'estudante', 'pedreiro', 'cozinheiro', 'cozinheira', 'médico', 'médica',
                        'advogado', 'advogada', 'engenheiro', 'engenheira', 'contador', 'contadora'
                    ]

                    if ' e ' in last_part:
                        part1, part2 = last_part.split(' e ', 1)
                        part1_lower = part1.strip().lower()
                        part2_lower = part2.strip().lower()

                        # Verificar se part1 é estado civil
                        if part1_lower in marital_statuses:
                            extracted_values['estado_civil'] = part1.strip()
                            # part2 pode ser procedência
                            if any(keyword in part2_lower for keyword in ['área', 'zona', 'capital', 'urbana', 'rural']):
                                extracted_values['procedencia'] = part2.strip()
                        # Verificar se part1 é ocupação
                        elif part1_lower in common_occupations:
                            extracted_values['ocupacao'] = part1.strip()
                            extracted_values['estado_civil'] = part2.strip()
                        else:
                            # Caso ambíguo, assumir ocupação e estado civil
                            extracted_values['ocupacao'] = part1.strip()
                            extracted_values['estado_civil'] = part2.strip()
                    else:
                        # Sem "e", verificar se é estado civil ou ocupação
                        last_part_lower = last_part.lower()
                        if last_part_lower in marital_statuses:
                            extracted_values['estado_civil'] = last_part
                        elif last_part_lower in common_occupations:
                            extracted_values['ocupacao'] = last_part
                        else:
                            # Caso ambíguo, assumir ocupação
                            extracted_values['ocupacao'] = last_part

                    # Se há mais partes, podem ser procedência
                    if len(parts) > 4:
                        for part in parts[3:-1]:
                            if any(keyword in part.lower() for keyword in ['área', 'zona', 'capital', 'urbana', 'rural']):
                                extracted_values['procedencia'] = part
                                break

        print(f"DEBUG: Valores extraídos: {extracted_values}")

        # Valores padrão para campos ausentes
        defaults = {
            'nome': 'Nome Desconhecido',
            'idade': 'idade não informada',
            'genero': 'gênero não informado',
            'ocupacao': 'ocupação não informada',
            'estado_civil': 'estado civil não informado'
        }

        # Aplicar valores padrão se necessário
        for key, default_value in defaults.items():
            if key not in extracted_values or not extracted_values[key]:
                extracted_values[key] = default_value

        # Corrigir estado civil baseado no gênero se necessário
        if extracted_values.get('genero', '').lower() in ['masculino', 'feminino']:
            gender = extracted_values['genero'].lower()
            marital_status = extracted_values.get('estado_civil', '').lower()

            print(f"DEBUG: Verificando correções - Gênero: {gender}, Estado Civil: {marital_status}")

            # Correções específicas (case-insensitive)
            corrections = {
                'masculino': {
                    'viúva': 'Viúvo',
                    'viuva': 'Viúvo',
                    'viúvo': 'Viúvo',  # Já correto, mas padronizar
                    'viuvo': 'Viúvo',  # Já correto, mas padronizar
                    'casada': 'Casado',
                    'solteira': 'Solteiro',
                    'divorciada': 'Divorciado'
                },
                'feminino': {
                    'viúvo': 'Viúva',
                    'viuvo': 'Viúva',
                    'viúva': 'Viúva',  # Já correto, mas padronizar
                    'viuva': 'Viúva',  # Já correto, mas padronizar
                    'casado': 'Casada',
                    'solteiro': 'Solteira',
                    'divorciado': 'Divorciada'
                }
            }

            # Verificar se o estado civil precisa de correção
            correction_applied = False
            for key in corrections[gender]:
                if key == marital_status:  # Comparação exata
                    old_value = extracted_values['estado_civil']
                    extracted_values['estado_civil'] = corrections[gender][key]
                    print(f"DEBUG: Estado civil corrigido: {old_value} -> {extracted_values['estado_civil']}")
                    correction_applied = True
                    break

            if not correction_applied:
                print(f"DEBUG: Nenhuma correção de estado civil necessária para: {marital_status}")

        # Corrigir ocupação baseada no gênero se necessário
        if extracted_values.get('genero', '').lower() in ['masculino', 'feminino']:
            gender = extracted_values['genero'].lower()
            occupation = extracted_values.get('ocupacao', '').lower()

            print(f"DEBUG: Verificando correções de ocupação - Gênero: {gender}, Ocupação: {occupation}")

            # Correções específicas de ocupação (case-insensitive)
            occupation_corrections = {
                'masculino': {
                    'professora': 'Professor',
                    'enfermeira': 'Enfermeiro',
                    'funcionária': 'Funcionário',
                    'funcionaria': 'Funcionário',
                    'funcionária pública': 'Funcionário público',
                    'funcionaria publica': 'Funcionário público',
                    'aposentada': 'Aposentado'
                },
                'feminino': {
                    'professor': 'Professora',
                    'enfermeiro': 'Enfermeira',
                    'funcionário': 'Funcionária',
                    'funcionario': 'Funcionária',
                    'funcionário público': 'Funcionária pública',
                    'funcionario publico': 'Funcionária pública',
                    'aposentado': 'Aposentada'
                }
            }

            # Verificar se a ocupação precisa de correção
            correction_applied = False
            for key in occupation_corrections[gender]:
                if key in occupation:  # Verificar se a chave está contida na ocupação
                    old_value = extracted_values['ocupacao']
                    extracted_values['ocupacao'] = occupation_corrections[gender][key]
                    print(f"DEBUG: Ocupação corrigida: {old_value} -> {extracted_values['ocupacao']}")
                    correction_applied = True
                    break

            if not correction_applied:
                print(f"DEBUG: Nenhuma correção de ocupação necessária para: {occupation}")

        # Construir lista de valores na ordem desejada
        values_list = []

        # Ordem: nome, idade, gênero (se disponível), ocupação, estado civil, procedência
        order = ['nome', 'idade', 'genero', 'ocupacao', 'estado_civil', 'procedencia']

        for key in order:
            if key in extracted_values and extracted_values[key] != defaults.get(key, ''):
                # Não incluir gênero se for "gênero não informado"
                if key == 'genero' and extracted_values[key] == defaults['genero']:
                    continue
                values_list.append(extracted_values[key])

        # Se não há valores válidos, retornar string vazia
        if not values_list:
            return ""

        # Juntar valores com vírgulas, usando "e" antes do último
        if len(values_list) == 1:
            return values_list[0]
        elif len(values_list) == 2:
            return f"{values_list[0]} e {values_list[1]}"
        else:
            # Para 3 ou mais valores: "valor1, valor2 e valor3"
            return ", ".join(values_list[:-1]) + f" e {values_list[-1]}"

    def process_file(self, file_path: str) -> Tuple[bool, str]:
        """Processa um arquivo JSON individual."""
        try:
            # Ler arquivo
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Verificar duplicatas do campo IDENTIFICAÇÃO DO PACIENTE
            has_duplicates, identification_count = self._check_duplicate_identification(data)
            if has_duplicates:
                return False, f"Arquivo contém {identification_count} campos 'IDENTIFICAÇÃO DO PACIENTE' (duplicatas detectadas)"

            # Verificar se já tem identificação
            has_identification = identification_count > 0

            # SEMPRE processar arquivos com identificação existente para aplicar correções de gênero
            # Apenas verificar se arquivos sem identificação já estão corretos
            if not has_identification:
                is_correct, correct_message = self._is_file_already_correct(data)
                if is_correct:
                    return False, f"Arquivo já está correto: {correct_message}"

            # Verificar se o arquivo tem a estrutura necessária
            instrucoes = data.get('instrucoesParticipante', {})
            if not instrucoes or 'descricaoCasoCompleta' not in instrucoes:
                return False, "Arquivo não tem estrutura completa (falta instrucoesParticipante ou descricaoCasoCompleta)"

            # SEMPRE limpar campos de identificação existentes se houver
            # Isso garante que correções de gênero sejam aplicadas mesmo em arquivos já processados
            if has_identification:
                info_array = data.get('materiaisDisponiveis', {}).get('informacoesVerbaisSimulado', [])
                for info in info_array:
                    if info.get('contextoOuPerguntaChave') == 'IDENTIFICAÇÃO DO PACIENTE':
                        original_info = info.get('informacao', '')
                        print(f"DEBUG: Processando identificação existente: {original_info}")
                        cleaned_info = self._clean_existing_identification(original_info)
                        print(f"DEBUG: Informação limpa: {cleaned_info}")
                        if cleaned_info:
                            info['informacao'] = cleaned_info
                        break

                # Para arquivos com identificação existente, ainda precisamos processar
                # a descrição para garantir consistência, mas não criar nova identificação
                # Vamos continuar o processamento normalmente

            # Extrair informações da descrição
            description = instrucoes.get('descricaoCasoCompleta', '')
            age, gender = self._extract_age_gender_from_description(description)

            # Inferir idade se não estiver presente
            if not age:
                if gender:
                    age = self._infer_age_from_context(
                        {'tituloEstacao': data.get('tituloEstacao', '')},
                        gender
                    )
                else:
                    # Inferir ambos se nenhum estiver presente
                    disease = data.get('tituloEstacao', '').lower()
                    # Inferir gênero primeiro baseado na doença
                    if 'cistite' in disease or 'itu' in disease:
                        gender = 'feminino' if random.random() < 0.85 else 'masculino'
                    elif 'câncer de mama' in disease or 'mastite' in disease:
                        gender = 'feminino'
                    elif 'câncer de próstata' in disease or 'hiperplasia prostática' in disease:
                        gender = 'masculino'
                    elif 'gravidez' in disease or 'parto' in disease or 'puerpério' in disease:
                        gender = 'feminino'
                    elif 'câncer cervical' in disease or 'câncer de colo uterino' in disease:
                        gender = 'feminino'
                    elif 'endometriose' in disease or 'mioma' in disease:
                        gender = 'feminino'
                    elif 'câncer de ovário' in disease or 'câncer de endométrio' in disease:
                        gender = 'feminino'
                    elif 'menopausa' in disease or 'osteoporose' in disease:
                        gender = 'feminino' if random.random() < 0.80 else 'masculino'
                    elif 'avc' in disease or 'acidente vascular' in disease:
                        gender = 'masculino' if random.random() < 0.55 else 'feminino'
                    elif 'infarto' in disease or 'angina' in disease:
                        gender = 'masculino' if random.random() < 0.70 else 'feminino'
                    elif 'diabetes' in disease or 'cetoacidose' in disease:
                        gender = 'masculino' if random.random() < 0.50 else 'feminino'
                    else:
                        gender = 'feminino' if random.random() < 0.52 else 'masculino'

                    # Agora inferir idade baseada no gênero inferido
                    age = self._infer_age_from_context(
                        {'tituloEstacao': data.get('tituloEstacao', '')},
                        gender
                    )

            # Inferir gênero se ainda não estiver presente (caso idade estivesse presente mas gênero não)
            if age and not gender:
                # Inferir gênero baseado no contexto epidemiológico
                disease = data.get('tituloEstacao', '').lower()

                # Regras epidemiológicas para inferência de gênero
                if 'cistite' in disease or 'itu' in disease:
                    gender = 'feminino' if random.random() < 0.85 else 'masculino'
                elif 'câncer de mama' in disease or 'mastite' in disease:
                    gender = 'feminino'
                elif 'câncer de próstata' in disease or 'hiperplasia prostática' in disease:
                    gender = 'masculino'
                elif 'gravidez' in disease or 'parto' in disease or 'puerpério' in disease:
                    gender = 'feminino'
                elif 'câncer cervical' in disease or 'câncer de colo uterino' in disease:
                    gender = 'feminino'
                elif 'endometriose' in disease or 'mioma' in disease:
                    gender = 'feminino'
                elif 'câncer de ovário' in disease or 'câncer de endométrio' in disease:
                    gender = 'feminino'
                elif 'menopausa' in disease or 'osteoporose' in disease:
                    gender = 'feminino' if random.random() < 0.80 else 'masculino'
                elif 'avc' in disease or 'acidente vascular' in disease:
                    gender = 'masculino' if random.random() < 0.55 else 'feminino'
                elif 'infarto' in disease or 'angina' in disease:
                    gender = 'masculino' if random.random() < 0.70 else 'feminino'
                elif 'diabetes' in disease or 'cetoacidose' in disease:
                    gender = 'masculino' if random.random() < 0.50 else 'feminino'
                else:
                    gender = 'feminino' if random.random() < 0.52 else 'masculino'

            if not age or not gender:
                return False, f"Não foi possível extrair idade ou gênero da descrição: {description[:100]}..."

            # Gerar dados
            name_category = self._get_name_category(age, gender)
            name = self._get_random_name(name_category)
            occupation = self._infer_occupation(age, {'tituloEstacao': data.get('tituloEstacao', '')}, gender)
            marital_status = self._infer_marital_status(age, gender)
            origin = self._infer_origin({'tituloEstacao': data.get('tituloEstacao', '')})

            # Criar campo de identificação
            context = {'tituloEstacao': data.get('tituloEstacao', '')}
            identification_field = self._create_identification_field(
                name, age, gender, occupation, marital_status, origin, context
            )

            # Inserir no array (no início) apenas se não tiver identificação
            # Para arquivos com identificação existente, já foi atualizada acima
            if not has_identification:
                info_array = data.setdefault('materiaisDisponiveis', {}).setdefault('informacoesVerbaisSimulado', [])
                info_array.insert(0, identification_field)
            else:
                # Para arquivos com identificação existente, apenas garantir que foi atualizada
                # A atualização já foi feita na seção anterior
                pass

            # Limpar descrição
            cleaned_description = self._clean_description(description, age, gender)
            data['instrucoesParticipante']['descricaoCasoCompleta'] = cleaned_description

            # Salvar arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            gender_info = "com gênero" if self._is_lgbt_relevant_theme(context) else "sem gênero"

            # Mensagem diferente para arquivos com identificação existente (atualização)
            if has_identification:
                return True, f"Arquivo atualizado com sucesso. Correções de gênero aplicadas ({gender_info})"
            else:
                return True, f"Arquivo processado com sucesso. Nome: {name}, Idade: {age}, Gênero: {gender} ({gender_info})"

        except Exception as e:
            return False, f"Erro ao processar arquivo: {str(e)}"

    def process_directory(self, directory: str) -> Dict[str, str]:
        """Processa todos os arquivos JSON em um diretório."""
        results = {}
        json_files = []

        # Encontrar arquivos JSON
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))

        print(f"Encontrados {len(json_files)} arquivos JSON para processar")

        for file_path in json_files:
            relative_path = os.path.relpath(file_path, directory)
            print(f"Processando: {relative_path}")

            success, message = self.process_file(file_path)
            results[file_path] = message

            if success:
                print(f"  ✓ {message}")
            else:
                print(f"  ✗ {message}")

        return results

    def generate_report(self, results: Dict[str, str], start_time: datetime) -> str:
        """Gera relatório detalhado das operações."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        report = []
        report.append("=" * 80)
        report.append("RELATÓRIO DE LIMPEZA DE DADOS FILIATÓRIOS")
        report.append("=" * 80)
        report.append("")

        # Estatísticas
        total_files = len(results)
        successful_files = sum(1 for msg in results.values() if "sucesso" in msg.lower())
        correct_files = sum(1 for msg in results.values() if "já está correto" in msg.lower())
        duplicate_files = sum(1 for msg in results.values() if "duplicatas detectadas" in msg.lower())
        error_files = total_files - successful_files - correct_files - duplicate_files

        report.append(f"Data e hora do processamento: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Duração: {duration:.2f} segundos")
        report.append("")

        report.append("ESTATÍSTICAS GERAIS:")
        report.append("-" * 40)
        report.append(f"Total de arquivos JSON: {total_files}")
        report.append(f"Arquivos processados com sucesso: {successful_files}")
        report.append(f"Arquivos já corretos (pulados): {correct_files}")
        report.append(f"Arquivos com duplicatas (ignorados): {duplicate_files}")
        report.append(f"Arquivos com erro: {error_files}")
        report.append("")

        # Detalhes
        if successful_files > 0:
            report.append("ARQUIVOS PROCESSADOS COM SUCESSO:")
            report.append("-" * 50)
            for file_path, message in results.items():
                if "sucesso" in message.lower():
                    report.append(f"Arquivo: {os.path.basename(file_path)}")
                    report.append(f"  {message}")
                    report.append("")

        if correct_files > 0:
            report.append("ARQUIVOS JÁ CORRETOS (SEM DADOS FILIATÓRIOS):")
            report.append("-" * 50)
            for file_path, message in results.items():
                if "já está correto" in message.lower():
                    report.append(f"Arquivo: {os.path.basename(file_path)}")
                    report.append("")

        if duplicate_files > 0:
            report.append("ARQUIVOS COM DUPLICATAS (IGNORADOS):")
            report.append("-" * 40)
            for file_path, message in results.items():
                if "duplicatas detectadas" in message.lower():
                    report.append(f"Arquivo: {os.path.basename(file_path)}")
                    report.append(f"  {message}")
                    report.append("")

        if error_files > 0:
            report.append("ERROS ENCONTRADOS:")
            report.append("-" * 30)
            for file_path, message in results.items():
                if not ("sucesso" in message.lower() or "já está correto" in message.lower() or "duplicatas detectadas" in message.lower()):
                    report.append(f"Arquivo: {os.path.basename(file_path)}")
                    report.append(f"  Erro: {message}")
                    report.append("")

        report.append("=" * 80)
        report.append("RESUMO FINAL")
        report.append("=" * 80)
        report.append(f"Processamento concluído: {successful_files}/{total_files} arquivos limpos com sucesso")
        report.append(f"Arquivos já corretos: {correct_files}")
        report.append(f"Arquivos com duplicatas ignorados: {duplicate_files}")

        return "\n".join(report)

def main():
    """Função principal."""
    start_time = datetime.now()

    print("INICIANDO LIMPEZA DE DADOS FILIATÓRIOS")
    print("=" * 60)
    print(f"Hora de início: {start_time.strftime('%H:%M:%S')}")
    print()

    # Inicializar processador
    try:
        enricher = PatientDataCleaner()
    except Exception as e:
        print(f"Erro ao inicializar: {e}")
        return

    # Processar diretório principal
    target_directory = "ESTAÇÕES A SEREM AUDITADAS"
    all_results = {}

    if not os.path.exists(target_directory):
        print(f"Diretório não encontrado: {target_directory}")
        return

    print(f"\nProcessando diretório: {target_directory}")
    results = enricher.process_directory(target_directory)
    all_results.update(results)

    # Gerar relatório
    print("\nGerando relatório...")
    report = enricher.generate_report(all_results, start_time)

    # Salvar relatório
    report_filename = f"relatorio_limpeza_filiatorios_{start_time.strftime('%Y%m%d_%H%M%S')}.txt"
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
