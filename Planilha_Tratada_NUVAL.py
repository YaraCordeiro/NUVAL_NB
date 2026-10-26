import csv
import io
import urllib.parse
import urllib.request

# 1. Pegar planilha do Google Sheets e ler os dados
SPREADSHEET_ID = "1T20cuNtJHi17g0CuPnWwJYVtO7Uzm3aLVdo9U0SQHWw"
SHEET_NAME = "Todas as solicitações"
sheet_name_encoded = urllib.parse.quote(SHEET_NAME)
url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"

# 2. Ler os dados da planilha e armazenar em uma lista de dicionários
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as response:
    csv_text = response.read().decode("utf-8")
reader = csv.DictReader(io.StringIO(csv_text))
dados = list(reader)

# 3. Arrumar datas e horas
import re
from datetime import datetime
from collections import Counter
import pandas as pd

def limpar_data_intervalo(valor, contem_hora=False):
    """
    Limpa e padroniza colunas de data/hora:
    - Corrige erros de digitação no ano (ex: 20244, 20204, 0024 -> 2024)
    - Garante que a data esteja entre 2019 e a data ATUAL exata da execução
    - Modifica datas fora do intervalo, futuras, inválidas ou nulas para "" (campo em branco)
    """
    # Define o limite máximo como o momento exato em que o código é executado
    limite_maximo = datetime.now()
    
    if pd.isna(valor) or str(valor).strip() in ['0', 'NaN', 'nan', 'XXXXX', 'X', '']:
        return ""
    
    txt = str(valor).strip()
    
    # Separa a hora se a coluna contiver horário
    hora_str = ""
    if " " in txt and len(txt.split()) == 2:
        partes_espaco = txt.split()
        data_parte = partes_espaco[0]
        hora_str = " " + partes_espaco[1]
    else:
        data_parte = txt
        
    # 3.1. Trata formato ISO (YYYY-MM-DD)
    if re.match(r'^\d{4}-\d{2}-\d{2}', data_parte):
        partes = data_parte.split('-')
        ano, mes, dia = partes[0], partes[1], partes[2]
        try:
            dt = datetime(int(ano), int(mes), int(dia))
            if 2019 <= dt.year <= limite_maximo.year and dt <= limite_maximo:
                return f"{dia}/{mes}/{ano}" + (hora_str if contem_hora else "")
            else:
                return ""
        except ValueError:
            return ""

    # 3.2. Padroniza separadores (pontos, espaços) para '/' e remove caracteres extras
    txt_limpo = re.sub(r'[.\s]+', '/', data_parte).strip('/.')
    partes = txt_limpo.split('/')
    if len(partes) < 3:
        return ""
        
    dia = partes[0].zfill(2)
    mes = partes[1].zfill(2)
    ano_bruto = partes[2]
    
    # 3.3. Recuperação do ano de 4 dígitos no formato '20XX'
    ano = ""
    if len(ano_bruto) == 5:
        if ano_bruto.startswith('2020'):
            ano = '202' + ano_bruto[-1]
        elif ano_bruto.startswith('200'):
            ano = '20' + ano_bruto[3:]
        else:
            match = re.search(r'202[0-9]', ano_bruto)
            if match:
                ano = match.group(0)
    elif len(ano_bruto) == 4:
        if ano_bruto.startswith('20'):
            ano = ano_bruto
        elif ano_bruto.startswith('00') or ano_bruto.startswith('02'):
            ano = '20' + ano_bruto[2:]
            
    if not ano:
        return ""
        
    # 3.4. Validação final da data no intervalo permitido [2019 até HOJE]
    try:
        dt = datetime(int(ano), int(mes), int(dia))
        if 2019 <= dt.year <= limite_maximo.year and dt <= limite_maximo:
            return f"{dia}/{mes}/{ano}" + (hora_str if contem_hora else "")
        else:
            return ""
    except ValueError:
        return ""

## Regra das datas funciona?
COLUNAS_DATAS = ["Carimbo de data/hora", "Data da solicitação", "Data da inspeção"]

for linha in dados:
    for col in COLUNAS_DATAS:
        if col in linha:
            val_orig = linha[col]
            e_carimbo_hora = "carimbo" in col.lower()
            
            # Aplica a limpeza com o limite dinâmico
            linha[col] = limpar_data_intervalo(val_orig, contem_hora=e_carimbo_hora)

hoje_str = datetime.now().strftime("%d/%m/%Y")
print(f"--- RESUMO DA LIMPEZA DAS DATAS (2019 até HOJE: {hoje_str}) ---")

for col in COLUNAS_DATAS:
    resumo_datas = Counter()
    total_linhas = len(dados)
    
    for linha in dados:
        val = linha.get(col, "")
        resumo_datas[val] += 1
        
    qtd_brancos = resumo_datas.get("", 0)
    qtd_validas = total_linhas - qtd_brancos
    
    print(f"\n📌 Coluna: {col}")
    print(f"  • Datas válidas (2019 até {hoje_str}) : {qtd_validas:>6} registros ({qtd_validas/total_linhas*100:.1f}%)")
    print(f"  • Campos em branco (Fora do período/Erro) : {qtd_brancos:>6} registros ({qtd_brancos/total_linhas*100:.1f}%)")

# 4. Arrumar Núcleos
def limpar_coluna_nurv(texto):
    if not texto:
        return ""
    
    # 4.1. Remove todos os espaços do texto (inclusive no meio das palavras)
    texto_sem_espacos = str(texto).replace(" ", "").strip()

    # 4.2. Verifica se começa com 'NURV' (independente de maiúsculas/minúsculas se usar .upper())
    if texto_sem_espacos.upper().startswith("NURV"):
        return texto_sem_espacos
    else:
        return ""

## Regra dos núcleos funciona?
NOME_COLUNA_NURV = "Núcleo de Vigilância"
print("--- VERIFICAÇÃO DA LIMPEZA DA COLUNA NURV ---")
total_alterados = 0
for i, linha in enumerate(dados, start=1):
    if NOME_COLUNA_NURV in linha:
        valor_original = linha[NOME_COLUNA_NURV]
        valor_limpo = limpar_coluna_nurv(valor_original)
        # Mostra os casos onde houve alteração
        if valor_original != valor_limpo:
            total_alterados += 1
            print(f"Linha {i}:")
            print(f"   Antes : '{valor_original}'")
            print(f"   Depois: '{valor_limpo}'\n")
        # Atualiza a linha com o valor limpo
        linha[NOME_COLUNA_NURV] = valor_limpo
print(f"Total de registros processados/alterados na coluna: {total_alterados}")

# 5. Arrumar RAs
def limpar_ra(texto):
    if not texto:
        return ""
    
    # 5.1. Remove espaços no início e no fim (preserva espaços internos)
    texto_limpo = str(texto).strip()

    # 5.2. Valores que devem virar campo em branco (em minúsculas para comparar)
    valores_invalidos = ["0", "teste", "xxxx"]
    if texto_limpo.lower() in valores_invalidos:
        return ""
    
    # 5.3. Mapeamento de padronização das RAs
    mapeamento_ras = {
        "Asa Norte": "Plano Piloto",
        "ASA SUL": "Plano Piloto",
        "Plano Piloto - Asa Norte": "Plano Piloto",
        "Plano Piloto - Asa Sul": "Plano Piloto",
        "Ceilândia SHSN": "Ceilândia",
        "Estrutural": "SCIA/Estrutural",
        "OCTOGONAL": "Sudoeste/Octogonal",
        "Por do Sol": "Sol Nascente/Por do Sol",
        "Por do Sol/Sol Nascente": "Sol Nascente/Por do Sol",
        "Samambaia Sul": "Samambaia",
        "Sol Nascente": "Sol Nascente/Por do Sol",
        "Por do Sol /Sol Nascente": "Sol Nascente/Por do Sol",
        "SUDOESTE": "Sudoeste/Octogonal"
    }
    # Substitui se o texto exato estiver no dicionário
    return mapeamento_ras.get(texto_limpo, texto_limpo)

## Regra das RAs funciona?
NOME_COLUNA_RA = "Região Administrativa"
print("--- VERIFICAÇÃO DA LIMPEZA DA COLUNA RA ---")
total_alterados = 0
for i, linha in enumerate(dados, start=1):
    if NOME_COLUNA_RA in linha:
        valor_original = linha[NOME_COLUNA_RA]
        valor_limpo = limpar_ra(valor_original)
        # Mostra os casos onde houve alteração
        if valor_original != valor_limpo:
            total_alterados += 1
            print(f"Linha {i}:")
            print(f"   Antes : '{valor_original}'")
            print(f"   Depois: '{valor_limpo}'\n")
        # Atualiza a linha com o valor limpo
        linha[NOME_COLUNA_RA] = valor_limpo
print(f"Total de RAs corrigidas/padronizadas: {total_alterados}")

# 6. Classificar solicitantes
import pandas as pd
def padronizar_solicitante(val):
  if pd.isna(val):
    return ''
  txt = str(val).strip()
  txt_lower = txt.lower()

  if (
      not txt
      or txt_lower
      in ['nan', 'none', '', 'null', '0', '(vazio)', 'xxxx', 'test', 'teste']
  ):
    return ''

  if txt_lower in ['outros', 'outro', 'diversos']:
    return 'Outros'

  # 1. Categorias específicas da lista original
  if any(k in txt_lower for k in ['bombeiro', 'cbmdf']):
    return 'Bombeiros'
  if any(k in txt_lower for k in ['denúncia', 'denuncia', 'anônimo', 'anonimo']):
    return 'Denúncia / Anônimo'
  if any(
      k in txt_lower
      for k in [
          'escola',
          'colégio',
          'colegio',
          'universidade',
          'unb',
          'faculdade',
          'ensino',
          'creche',
      ]
  ):
    return 'Instituição de Ensino'
  if 'ofício' in txt_lower or 'oficio' in txt_lower:
    return 'Ofício'
  if any(
      k in txt_lower for k in ['ouvidoria', 'participa df', 'e-ouv', 'e-ouvidoria']
  ):
    return 'Ouvidorias'
  if any(
      k in txt_lower for k in ['polícia', 'policia', 'pmdf', 'pcdf', 'delegacia']
  ):
    return 'Polícia'
  if any(k in txt_lower for k in ['sei', 'processo']):
    return 'Processos SEI'
  if any(
      k in txt_lower
      for k in [
          'gdf',
          'órgão público',
          'orgao publico',
          'secretaria',
          'administração',
          'administracao',
          'caesb',
          'neoenergia',
          'slu',
          'novacap',
      ]
  ):
    return 'Órgão Público / GDF'

  # 2. Se não for de nenhuma categoria acima, verifica se é Nome de Pessoa -> "Pessoa física"
  partes = [p for p in txt.split() if p.isalpha()]
  if len(partes) >= 1 and not any(char.isdigit() for char in txt):
    return 'Pessoa física'

  # 3. Caso contrário -> "Outros"
  return 'Outros'


# Aplica o tratamento diretamente nos registros que serão exportados
COL_SOLICITANTE = "Solicitante"
if dados and COL_SOLICITANTE in dados[0]:
  for linha in dados:
    linha[COL_SOLICITANTE] = padronizar_solicitante(
        linha.get(COL_SOLICITANTE, "")
    )

  # --- LOOP DE VISUALIZAÇÃO E VERIFICAÇÃO DOS DADOS ---
  print("=" * 60)
  print("CONTAGEM DE SOLICITANTES APÓS A PADRONIZAÇÃO:")
  print("=" * 60)

  resumo_solicitantes = Counter(
      linha.get(COL_SOLICITANTE, "") for linha in dados
  )
  for categoria, qtd in resumo_solicitantes.items():
    cat_nome = categoria if categoria != "" else "(vazio)"
    print(f"• {cat_nome:<25}: {qtd:,} solicitações".replace(",", "."))

  print("=" * 60)

# 7. Classificar tipo do imóvel
import re

# Dicionário completo de padronização baseado no anexo
MAPA_TIPOS_IMOVEL = {
    # Residencial
    "CASA": "Casa",
    "CASA RESIDENCIAL": "Casa",
    "SOBRADO": "Casa",
    "APARTAMENTO": "Apartamento",
    "APTO": "Apartamento",
    "APT": "Apartamento",
    "AP": "Apartamento",
    "CHÁCARA": "Chácara/Sítio",
    "CHACARA": "Chácara/Sítio",
    "SÍTIO": "Chácara/Sítio",
    "SITIO": "Chácara/Sítio",
    "FAZENDA": "Chácara/Sítio",
    
    # Comércio / Serviços
    "COMÉRCIO": "Comércio",
    "COMERCIO": "Comércio",
    "ESTABELECIMENTO COMERCIAL": "Comércio",
    "OFICINA": "Comércio",
    "LOJA": "Comércio",
    "SALA COMERCIAL": "Comércio",
    "GALPÃO": "Comércio",
    "GALPAO": "Comércio",
    
    # Terrenos e Lotes
    "TERRENO BALDIO": "Lote/Terreno",
    "TERRENO BAUDIO": "Lote/Terreno",
    "LOTE VAZIO": "Lote/Terreno",
    "LOTE FECHADO": "Lote/Terreno",
    "TERRENO /EMTULHO": "Lote/Terreno",
    "LIXO/EMTULHO": "Lote/Terreno",
    "TERRENO": "Lote/Terreno",
    "LOTE": "Lote/Terreno",
    
    # Instituições / Saúde / Educação / Espaço Público
    "ESCOLA": "Instituição / Espaço Público",
    "CRECHE": "Instituição / Espaço Público",
    "UNIDADE DE SAÚDE": "Instituição / Espaço Público",
    "UNIDADE DE SAUDE": "Instituição / Espaço Público",
    "VIGILÂNCIA EPIDEMIOLÓGICA": "Instituição / Espaço Público",
    "VIGILANCIA EPIDEMIOLOGICA": "Instituição / Espaço Público",
    "ÓRGÃO PÚBLICO": "Instituição / Espaço Público",
    "ORGAO PUBLICO": "Instituição / Espaço Público",
    "IGREJA": "Instituição / Espaço Público",
    "ASILO": "Instituição / Espaço Público",
    "VIA PÚBLICA": "Instituição / Espaço Público",
    "VIA PUBLICA": "Instituição / Espaço Público"
}

# Valores/textos inválidos que devem virar campo em branco ("")
VALORES_INVALIDOS = [
    "0", "-", "XXXXX", "TESTE", "NÃO INFORMADO", "NAO INFORMADO", 
    "NAÕ INFORMADO", "OUTRO", "OUTROS", "NAN", "NONE"
]

def extrair_tipo_imovel(*valores):
    """
    Analisa os campos (Tipo de imóvel, Telefone, E-mail).
    Limpa espaços, descarta números/e-mails e retorna a categoria padronizada.
    """
    for valor in valores:
        if not valor:
            continue
            
        # 7.1. Remove espaços no início e no fim, mantendo apenas espaços simples entre palavras
        texto = " ".join(str(valor).strip().split())
        
        # 7.2. Ignora se for e-mail ou contiver números (telefones, CPFs, datas, '0')
        if "@" in texto or re.search(r'\d', texto):
            continue
            
        texto_upper = texto.upper()
        
        # 7.3. Descarta valores inválidos/genéricos
        if texto_upper in VALORES_INVALIDOS:
            continue
            
        # 7.4. Busca correspondência exata no dicionário
        if texto_upper in MAPA_TIPOS_IMOVEL:
            return MAPA_TIPOS_IMOVEL[texto_upper]
            
        # 7.5. Busca por palavras-chave contidas no texto
        for chave, padrao in MAPA_TIPOS_IMOVEL.items():
            if chave in texto_upper:
                return padrao

    # Se nenhum tipo válido for encontrado nas 3 colunas, retorna campo em branco
    return ""

## Regra dos tipos de imóvel funciona?
from collections import Counter

COL_TIPO = "Tipo de imóvel"
COL_TEL = "Telefone"
COL_EMAIL = "E-mail"

resumo_tipos = Counter()
alteracoes = []

print("--- PROCESSANDO LIMPEZA DA COLUNA TIPO DE IMÓVEL ---")

for i, linha in enumerate(dados, start=1):
    val_tipo_orig = linha.get(COL_TIPO, "")
    val_tel = linha.get(COL_TEL, "")
    val_email = linha.get(COL_EMAIL, "")
    
    # Executa a limpeza varrendo as três colunas
    val_tipo_limpo = extrair_tipo_imovel(val_tipo_orig, val_tel, val_email)
    
    # Atualiza a linha do dicionário
    linha[COL_TIPO] = val_tipo_limpo
    
    # Guarda contagem e alterações
    resumo_tipos[val_tipo_limpo] += 1
    
    if str(val_tipo_orig).strip() != val_tipo_limpo:
        alteracoes.append((i, val_tipo_orig, val_tipo_limpo))

# 1. Exibe amostra das alterações realizadas
print("\n--- AMOSTRA DAS ALTERAÇÕES (Antes -> Depois) ---")
for num_linha, antes, depois in alteracoes[:10]: # Mostra as 10 primeiras alterações
    depois_txt = depois if depois != "" else "[Campo em Branco / Nulo]"
    print(f"Linha {num_linha:>3}: '{antes}'  -->  '{depois_txt}'")

# 2. Exibe a contagem consolidada das categorias
print("\n--- DISTRIBUIÇÃO DOS TIPOS DE IMÓVEL GERADOS ---")
for tipo, qtd in resumo_tipos.most_common():
    nome_categoria = tipo if tipo != "" else "[Campo em Branco / Nulo]"
    print(f"  • {nome_categoria:<30}: {qtd:>5} registros")

# 8. Classificar o motivo da solicitação
import re
import pandas as pd

    # 8.1. Dicionário de Mapeamento de Variações de Palavras -> Categoria
CATEGORIAS_MOTIVOS = {
    "Mosquito/Dengue/Fumacê": [
        r'\bMOSQUITO\b', r'\bMOSQUITOS\b', r'\bAEDES\b', r'\bDENGUE\b', 
        r'\bARBOVIROSE\b', r'\bARBOVIROSES\b', r'\bFUMACÊ\b', r'\bFUMACE\b', r'\bPERNILONGO\b'
    ],
    "Água Parada": [
        r'ÁGUA PARADA', r'AGUA PARADA', r'\bPNEU\b', r'\bPNEUS\b', 
        r'\bPISCINA\b', r'CAIXA D[\'ÁA]GUA', r'CAIXA DE ÁGUA', r'RECIPIENTE'
    ],
    "Escorpião": [
        r'\bESCORPIÃO\b', r'\bESCORPIAO\b', r'\bESCORPIÕES\b', r'\bESCORPIOES\b'
    ],
    "Roedor": [
        r'\bROEDOR\b', r'\bROEDORES\b', r'\bRATO\b', r'\bRATOS\b', r'\bRATAZANA\b'
    ],
    "Lixo/Entulho": [
        r'\bLIXO\b', r'\bENTULHO\b', r'\bENTULHOS\b', r'\bMATO\b', r'RESTO.*OBRA'
    ],
    "Pombo": [
        r'\bPOMBO\b', r'\bPOMBOS\b', r'PIOLHO DE POMBO'
    ],
    "Caramujo": [
        r'\bCARAMUJO\b', r'\bCARAMUJOS\b'
    ],
    "Morcego": [
        r'\bMORCEGO\b', r'\bMORCEGOS\b'
    ],
    "Carrapato": [
        r'\bCARRAPATO\b', r'\bCARRAPATOS\b'
    ],
    "Aranha": [
        r'\bARANHA\b', r'\bARANHAS\b'
    ],
    "Lagarta": [
        r'\bLAGARTA\b', r'\bLAGARTAS\b'
    ],
    "Barbeiro": [
        r'\bBARBEIRO\b', r'\bBARBEIROS\b', r'\bCHAGAS\b'
    ],
    "Lacraia": [
        r'\bLACRAIA\b', r'\bLACRAIAS\b', r'\bCENTOPÉIA\b', r'\bCENTOPEIA\b'
    ],
    "Pulga/Bicho-de-pé": [
        r'\bPULGA\b', r'\bPULGAS\b', r'BICHO.*PÉ', r'BICHO.*PE'
    ],
    "Acumulador": [
        r'\bACUMULADOR\b', r'\bACUMULADORES\b', r'ACUMULAÇÃO', r'ACUMULACAO'
    ],
    "Vacinação Antirrábica": [
        r'VACINAÇÃO', r'VACINACAO', r'ANTIRRÁBICA', r'ANTIRRABICA', r'\BRAIVA\b'
    ]
}

def extrair_motivos(texto):
    """
    Identifica todas as categorias presentes no texto do motivo.
    Retorna um dicionário com True/False para cada coluna + texto consolidado.
    """
    resultado = {}
    if not texto or str(texto).strip() in ['0', 'NaN', 'nan', '']:
        for cat in CATEGORIAS_MOTIVOS:
            resultado[f"Motivo_{cat}"] = "Não"
        resultado["Motivos_Padronizados"] = ""
        return resultado

    texto_upper = str(texto).upper()
    motivos_encontrados = []

    for categoria, padroes in CATEGORIAS_MOTIVOS.items():
        encontrado = False
        for padrao in padroes:
            if re.search(padrao, texto_upper):
                encontrado = True
                break
        
        resultado[f"Motivo_{categoria}"] = "Sim" if encontrado else "Não"
        if encontrado:
            motivos_encontrados.append(categoria)

    # Texto consolidado organizado por vírgula
    if motivos_encontrados:
        resultado["Motivos_Padronizados"] = ", ".join(motivos_encontrados)
    else:
        resultado["Motivos_Padronizados"] = "Outros"

    return resultado

### Regra dos motivos funciona?
COL_MOTIVO = "Motivo da solicitação"  # Ajuste com o nome da sua coluna

for linha in dados:
    val_motivo = linha.get(COL_MOTIVO, "")
    
    # Processa o motivo e extrai as flags/colunas individuais
    info_motivos = extrair_motivos(val_motivo)
    
    # 1. Atualiza a coluna original/consolidada com os motivos limpos
    linha["Motivos_Padronizados"] = info_motivos["Motivos_Padronizados"]
    
    # 2. Cria uma nova coluna para cada problema específico (ex: Motivo_Escorpião, Motivo_Mosquito...)
    for chave, valor in info_motivos.items():
        if chave != "Motivos_Padronizados":
            linha[chave] = valor

from collections import Counter

contagem_categorias = Counter()

for linha in dados:
    motivos_str = linha.get("Motivos_Padronizados", "")
    if motivos_str:
        for m in motivos_str.split(", "):
            contagem_categorias[m] += 1

print("\n--- DISTRIBUIÇÃO DOS MOTIVOS E VETORES ENCONTRADOS ---")
for motivo, qtd in contagem_categorias.most_common():
    print(f"  • {motivo:<30}: {qtd:>6} solicitações")

# 9. Coleta de espécimes
import pandas as pd

def padronizar_coleta(valor):
    """
    Padroniza a coluna de coleta de espécimes:
    - Variações de Não -> 'Não'
    - Variações de Sim e relatos de animais -> 'Sim'
    - '2024-01-02 00:00:00', '2023-08-21 00:00:00', '2', '3', '0', 'NÃO INFORMADO', 'NAO INFORMADO', 'NÃO RESPONDEU', 'NAO RESPONDEU' -> Campo em branco
    """
    if pd.isna(valor):
        return ""
    
    txt = str(valor).strip().upper()
    
    # 9.1. Valores específicos que devem virar CAMPO EM BRANCO
    valores_em_branco = [
        '2024-01-02 00:00:00', '2023-08-21 00:00:00', '2', '3', '0', 'NÃO INFORMADO', 'NAO INFORMADO', 'NÃO RESPONDEU', 'NAO RESPONDEU',
    ]
    if txt in valores_em_branco:
        return ""
    
    # 9.2. Variações mantidas para "Não"
    variacoes_nao = [
        'NÃO', 'NAO', 'NÂO', 'NAÕ', 'NÁO', 'NÃO0', 'NAO0', 'N0', 'N ÃO', 'NÃ0', 'NÕ', 'NÕA',
        'NÃOI', 'NSO', 'NA0', 'NA\\O', '0N', 'ÑÃO', 'NÃOL', 'NÃP', 'NB',
        'MÃO', 'MAO', 'MÃ', 'X', 'XX', 'XXXXX', ',', 'N', '0', ""
    ]
    if txt in variacoes_nao:
        return "Não"
        
    # 9.3. Variações para "Sim"
    variacoes_sim = ['SIM', 'SIM]', 'SIN', 'SM', '1', 'S']
    if txt in variacoes_sim:
        return "Sim"
        
    # 9.4. Textos com presença de animais ou relatos -> 'Sim'
    palavras_animais = [
        'ESCORPI', 'MOSQUITO', 'RATO', 'ROEDOR', 'LAGARTA', 'CARRAPATO', 
        'ARANHA', 'POMBO', 'MORCEGO', 'CARAMUJO', 'LACRAIA', 'BARBEIRO', 'PULGA', 
        'ANIMAL', 'VÁRIOS', 'VARIOS'
    ]
    if any(p in txt for p in palavras_animais):
        return "Sim"
        
    # 9.5. Qualquer outro valor -> Campo em branco
    return ""

## Regra da coleta de espécimes funciona?
NOME_COL_COLETA = "Coleta de espécimes: SIM / NÃO"

for linha in dados:
    val_orig = linha.get(NOME_COL_COLETA, "")
    
    # Aplica a padronização atualizada
    linha[NOME_COL_COLETA] = padronizar_coleta(val_orig)

from collections import Counter

resumo_coleta = Counter()
total_registros = len(dados)

for linha in dados:
    val_padrao = linha.get(NOME_COL_COLETA, "")
    resumo_coleta[val_padrao] += 1

print("\n--- RESUMO DA PADRONIZAÇÃO DA COLETA DE ESPÉCIMES ---")
print(f"Total de registros analisados: {total_registros}\n")

for categoria, qtd in resumo_coleta.most_common():
    nome_exibicao = categoria if categoria != "" else "[Campo em Branco]"
    porcentagem = (qtd / total_registros) * 100
    print(f"  • {nome_exibicao:<20}: {qtd:>6} registros ({porcentagem:.1f}%)")

# 10. Colunas quantitativas (Números)
import pandas as pd

def padronizar_numero(valor):
    """
    Padroniza campos numéricos:
    - Mantém apenas números inteiros maiores ou iguais a 1 (1, 2, 3...)
    - Modifica 0, decimais, textos (XXXX, X, NÃO, etc.) e nulos para "" (campo em branco)
    """
    if pd.isna(valor):
        return ""
    
    val_str = str(valor).strip()
    
    try:
        num = float(val_str)
        # Verifica se o número é um inteiro válido e maior ou igual a 1
        if num.is_integer() and num >= 1:
            return int(num)
        else:
            return ""
    except ValueError:
        # Se contiver letras ou marcas de erro (XXXX, X, NÃO, etc.) -> Campo em branco
        return ""

### Regra das colunas quantitativas funciona?
# Lista com os nomes das colunas numéricas
COLUNAS_NUMERICAS = [
    "Quantidade de espécimes encontrados (insetos ou animais peçonhentos)",
    "Quantidade de Caixas Inspecionadas (escorpiões)",
    "Quantidade de Caixas Positivas (escorpiões)",
    "Quantidade de Caixas Inspecionadas (Roedores)",
    "Quantidade de Caixas Positivas (Roedores)",
    "N° Tocas/ninheiras (Roedores)",
    "N° Trilhas (Roedores)",
    "Isca (unid.) - Roedores",
    "Raticida Bloco (un.)"
]

# Processa cada linha do seu loop
for linha in dados:
    for col in COLUNAS_NUMERICAS:
        if col in linha:
            linha[col] = padronizar_numero(linha[col])

from collections import Counter

print("--- RESUMO DA LIMPEZA DAS COLUNAS NUMÉRICAS ---")

for col in COLUNAS_NUMERICAS:
    resumo_col = Counter()
    total_linhas = len(dados)
    
    for linha in dados:
        val = linha.get(col, "")
        resumo_col[val] += 1
        
    qtd_brancos = resumo_col.get("", 0)
    qtd_validos = total_linhas - qtd_brancos
    
    print(f"\n📌 Coluna: {col}")
    print(f"  • Valores válidos (≥ 1) : {qtd_validos:>6} registros")
    print(f"  • Campos em branco (0/XX): {qtd_brancos:>6} registros")
    
    # Exibe os 3 números válidos mais frequentes na coluna
    top_numeros = [(k, v) for k, v in resumo_col.most_common() if k != ""][:3]
    if top_numeros:
        top_str = ", ".join([f"{num} (x{qtd})" for num, qtd in top_numeros])
        print(f"  • Valores mais comuns   : {top_str}")

# 11. Coluna quantitativa (Gramas)
import re
import pandas as pd

def padronizar_gramas(valor):
    """
    Padroniza a coluna de quantidade de Raticida em Pó:
    - Converte KG/Quilogramas para Gramas (* 1000)
    - Mantém quantidades em g/gr ou números isolados >= 1
    - Modifica 0, textos (XXXX, X, etc.) e nulos para "" (campo em branco)
    """
    if pd.isna(valor):
        return ""
    
    txt = str(valor).strip().lower()
    
    # Textos zerados, códigos de erro ou marcações inválidas
    if txt in ['0', 'x', 'xx', 'xxx', 'xxxx', 'xxxxx', 'xxxxxx', 'não', 'nao', 'nan', 'none', '']:
        return ""
    
    # Remove espaços extras entre números e unidades (ex: '1 kg' -> '1kg')
    txt = re.sub(r'(\d+)\s+([a-z]+)', r'\1\2', txt)
    
    # 11.1. Trata Quilogramas (kg, kgs, kilo, kilos) -> multiplica por 1000
    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kgs|kilo|kilos|quilograma|quilogramas)', txt)
    if match_kg:
        num_str = match_kg.group(1).replace(',', '.')
        try:
            val_g = float(num_str) * 1000
            if val_g >= 1:
                return int(round(val_g))
        except ValueError:
            pass
            
    # 11.2. Trata Gramas (g, gr, grs) ou número puro isolado
    match_g = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:g|gr|grs|grama|gramas)?$', txt)
    if match_g:
        num_str = match_g.group(1).replace(',', '.')
        try:
            val_g = float(num_str)
            if val_g >= 1:
                return int(round(val_g))
        except ValueError:
            pass
            
    return ""

## Regra da coluna de gramas funciona?
NOME_COL_RATICIDA_PO = "Raticida em Pó (Qtd. em g.)"  # Ajuste para o nome da coluna

for linha in dados:
    val_orig = linha.get(NOME_COL_RATICIDA_PO, "")
    
    # Aplica a padronização e conversão para gramas
    linha[NOME_COL_RATICIDA_PO] = padronizar_gramas(val_orig)

from collections import Counter

resumo_gramas = Counter()
total_registros = len(dados)

for linha in dados:
    val = linha.get(NOME_COL_RATICIDA_PO, "")
    resumo_gramas[val] += 1

qtd_brancos = resumo_gramas.get("", 0)
qtd_validos = total_registros - qtd_brancos

print("\n--- RESUMO DA PADRONIZAÇÃO DE RATICIDA EM PÓ (GRAMAS) ---")
print(f"Total de registros analisados : {total_registros}")
print(f"  • Registros válidos (≥ 1g) : {qtd_validos:>6} ({qtd_validos/total_registros*100:.1f}%)")
print(f"  • Campos em branco (0/XXXX): {qtd_brancos:>6} ({qtd_brancos/total_registros*100:.1f}%)\n")

print("--- QUANTIDADES EM GRAMAS MAIS FREQUENTES ---")
top_gramas = [(k, v) for k, v in resumo_gramas.most_common() if k != ""][:10]

for gramas, qtd in top_gramas:
    print(f"  • {gramas:>5} g : {qtd:>4} registros")

# 12. Status de atividades executadas
import pandas as pd

def padronizar_atividade_vigilancia(valor):
    """
    Categoriza as atividades e status do atendimento da Vigilância Ambiental:
    - Atendida
    - Atendida com Tratamento
    - Atendida com Orientações
    - Atendida com Coleta
    - Não Atendida - Imóvel Fechado
    - Não Atendida - Outros Motivos
    - '' (campo em branco para NÃO/SIM genéricos, 0, XXXXX e nulos)
    """
    if pd.isna(valor):
        return ""
    
    txt = str(valor).strip().upper()
    
    # Respostas genéricas, erros ou marcações sem descrição da atividade
    if txt in ['0', 'X', 'XX', 'XXX', 'XXXX', 'XXXXX', 'XXXXXX', 'NAN', 'NONE', '', 'NÃO', 'NAO', 'NÂO', 'NAÕ', 'NÁO', 'SIM']:
        return ""
    
    # 12.1. Atendimento com Tratamento (Químico/Biológico/BTI/Larvicida)
    if any(p in txt for p in ['TRATAMENTO', 'TRATAMENTTO', 'BTI', 'CONTROLE QUÍMICO', 'CONTROLE QUIMICO', 'LARVICIDA']):
        return "Atendida com Tratamento"
        
    # 12.2. Atendimento com Orientações / Ação Educativa
    if any(p in txt for p in ['ORIENTAÇÃO', 'ORIENTACAO', 'ORIENTAÇÕES', 'ORIENTACOES', 'ORIENTAÇAO']):
        return "Atendida com Orientações"
        
    # 12.3. Atendimento com Coleta de Vetores/Amostras
    if 'COLETA' in txt or 'COLETADO' in txt:
        return "Atendida com Coleta"

    # 12.4. Atendimento Padrão / Vistoria Concluída
    if any(p in txt for p in ['ATENDIDA', 'ATENDIDO', 'SOLICCITAÇÃO', 'SOLICITA AÇÃO', 'VISTORIA REALIZADA', 'INSPEÇÃO REALIZADA', 'INSPECAO REALIZADA']):
        return "Atendida"
        
    # 12.5. Não Atendida - Imóvel Fechado / Ausente
    if any(p in txt for p in ['FECHADO', 'FECHADA', 'FEHCADA', 'AUSENTE', 'FECHADOS']):
        return "Não Atendida - Imóvel Fechado"
        
    # 12.6. Não Atendida - Outros Motivos (Endereço incorreto / Recusa)
    if any(p in txt for p in ['ENDEREÇO', 'ENDERECO', 'INCOMPLETO', 'RECUSADA', 'RECUSA', 'NÃO FOI POSSÍVEL', 'NAO FOI POSSIVEL']):
        return "Não Atendida - Outros Motivos"

    return ""

## Regra da coluna de atividades funciona?
NOME_COL_NOTIFICACAO = "Uso de notificação (sim ou não?"  # Ajuste para o nome exato da coluna

for linha in dados:
    val_orig = linha.get(NOME_COL_NOTIFICACAO, "")
    
    # Aplica a padronização das atividades
    linha[NOME_COL_NOTIFICACAO] = padronizar_atividade_vigilancia(val_orig)

from collections import Counter

resumo_atividades = Counter()
total_registros = len(dados)

for linha in dados:
    val = linha.get(NOME_COL_NOTIFICACAO, "")
    resumo_atividades[val] += 1

print("\n--- RESUMO DAS ATIVIDADES DA VIGILÂNCIA AMBIENTAL ---")
print(f"Total de registros analisados: {total_registros}\n")

for categoria, qtd in resumo_atividades.most_common():
    nome_exibicao = categoria if categoria != "" else "[Sem atividade descrita / Campo em branco]"
    porcentagem = (qtd / total_registros) * 100
    print(f"  • {nome_exibicao:<42}: {qtd:>6} registros ({porcentagem:.1f}%)")

# 13. Uso de relatório circunstanciado
import pandas as pd

def padronizar_relatorio_circunstanciado(valor):
    """
    Padroniza a coluna Uso de Relatório Circunstanciado:
    - 'Sim': Para 'SIM' e relatos/textos descritivos das vistorias.
    - 'Não': Para 'NÃO' e variações de negação.
    - '' (Campo em branco): Para valores numéricos (0, 1, 2, etc.) e campos nulos.
    """
    if pd.isna(valor):
        return ""
    
    txt = str(valor).strip().upper()
    
    # 13.1. Se for um valor numérico (0, 1, 2, etc.) -> Campo em branco
    if txt.isdigit():
        return ""
    
    # 13.2. Variações de negação -> 'Não'
    variacoes_nao = [
        'NÃO', 'NAO', 'NÂO', 'NAÕ', 'NÁO', 'ÑÃO', 'NAI', 'NAN', 'NONE', ''
    ]
    if txt in variacoes_nao:
        return "Não"
        
    # 13.3. Textos descritivos ou 'SIM' -> 'Sim'
    return "Sim"

## Regra da coluna de relatório circunstanciado funciona?
NOME_COL_RELATORIO = "Uso de relatório circunstanciado (sim ou não)?"  # Ajuste para o nome exato da sua coluna

for linha in dados:
    val_orig = linha.get(NOME_COL_RELATORIO, "")
    
    # Aplica a padronização atualizada
    linha[NOME_COL_RELATORIO] = padronizar_relatorio_circunstanciado(val_orig)

from collections import Counter

resumo_relatorio = Counter()
total_registros = len(dados)

for linha in dados:
    val_padrao = linha.get(NOME_COL_RELATORIO, "")
    resumo_relatorio[val_padrao] += 1

print("\n--- RESUMO DA PADRONIZAÇÃO DO RELATÓRIO CIRCUNSTANCIADO ---")
print(f"Total de registros analisados: {total_registros}\n")

for categoria, qtd in resumo_relatorio.most_common():
    nome_exibicao = categoria if categoria != "" else "[Campo em Branco / Numérico]"
    porcentagem = (qtd / total_registros) * 100
    print(f"  • {nome_exibicao:<30}: {qtd:>6} registros ({porcentagem:.2f}%)")

# 14. Arrumar coluna de "Data da inspeção"
import re
import pandas as pd

def limpar_data_inspecao(valor):
    """
    Limpa e padroniza a coluna Data da Inspeção:
    - Corrige anos com dígitos duplicados/extras (ex: 20244, 20204, 22024 -> 2024)
    - Padroniza separadores (pontos, espaços) para '/'
    - Limpa pontos finais e espaços extras
    - Converte datas corrompidas (1899, códigos de 5 dígitos como 45794) para ""
    """
    if pd.isna(valor):
        return ""
    
    txt = str(valor).strip()
    if txt in ['0', 'NaN', 'nan', 'XXXXX', 'X', '']:
        return ""
    
    # 14.1. Se estiver no formato ISO 'YYYY-MM-DD ...'
    if re.match(r'^\d{4}-\d{2}-\d{2}', txt):
        partes = txt.split()[0].split('-')
        ano, mes, dia = partes[0], partes[1], partes[2]
        if ano == '1899' or int(ano) < 2010:
            return ""
        return f"{dia}/{mes}/{ano}"
    
    # 14.2. Padroniza separadores (pontos, espaços) para '/' e limpa pontos no final
    txt_limpo = re.sub(r'[.\s]+', '/', txt).strip('/.')
    
    partes = txt_limpo.split('/')
    if len(partes) < 3:
        return ""
        
    dia = partes[0].zfill(2)
    mes = partes[1].zfill(2)
    ano_bruto = partes[2]
    
    # Valida dia e mês válidos
    try:
        if int(dia) < 1 or int(dia) > 31 or int(mes) < 1 or int(mes) > 12:
            return ""
    except ValueError:
        return ""
    
    # Descarte de códigos corrompidos do Excel e ano 1899
    if ano_bruto == '1899' or ano_bruto in ['45794', '32049']:
        return ""
    
    # 14.3. Resgate do ano correto com 4 dígitos no intervalo de 2010 a 2029
    # Ajusta o erro de digitação duplicada (ex: '20204' -> '2024', '20024' -> '2024', '22024' -> '2024')
    if len(ano_bruto) == 5:
        if ano_bruto.startswith('2020'):
            ano = '202' + ano_bruto[-1]
        elif ano_bruto.startswith('200'):
            ano = '20' + ano_bruto[3:]
        else:
            match_202x = re.search(r'202[0-9]', ano_bruto)
            if match_202x:
                ano = match_202x.group(0)
            else:
                return ""
        return f"{dia}/{mes}/{ano}"

    # 14.4. Ano normal com 4 dígitos válidos
    if len(ano_bruto) == 4 and ano_bruto.startswith('20'):
        return f"{dia}/{mes}/{ano_bruto}"

    return ""

# 15. Contar dias úteis entre solicitação e inspeção
from datetime import datetime
from collections import Counter
import numpy as np
import pandas as pd

def calcular_dias_uteis_com_fallback(data_solic_str, data_insp_str, carimbo_str):
    """
    Calcula dias úteis entre Data da Solicitação e a Data Final:
    - Se houver 'Data da inspeção' válida, utiliza ela.
    - Se 'Data da inspeção' estiver em branco/inválida, utiliza a data do 'Carimbo de data/hora'.
    - Retorna None para datas inválidas, em branco ou valores negativos.
    """
    # Define qual data final utilizar
    data_fim_str = str(data_insp_str).strip()
    if not data_fim_str:
        data_fim_str = str(carimbo_str).strip()
        
    if not str(data_solic_str).strip() or not data_fim_str:
        return None
        
    try:
        # Pega apenas a parte da data (DD/MM/YYYY), descartando horários se houver
        data_solic_limpa = str(data_solic_str).strip().split()[0]
        data_fim_limpa = data_fim_str.strip().split()[0]
        
        dt_solic = datetime.strptime(data_solic_limpa, "%d/%m/%Y").date()
        dt_fim = datetime.strptime(data_fim_limpa, "%d/%m/%Y").date()
        
        # busday_count calcula apenas dias úteis (Segunda a Sexta)
        dias = int(np.busday_count(dt_solic, dt_fim))
        
        # Descarta números negativos
        return dias if dias >= 0 else None
    except Exception:
        return None


def categorizar_tempo_atendimento(dias_uteis, solicitante, linha):
    """
    Categoriza o prazo em dias úteis com base no Solicitante e nos Motivos.
    """
    if dias_uteis is None or dias_uteis < 0:
        return ""
    
    solic_str = str(solicitante).strip().lower()
    
    # ----------------------------------------------------
    # CASO 1: Solicitante == "Ouvidorias"
    # ----------------------------------------------------
    if solic_str == "ouvidorias":
        if 0 <= dias_uteis < 10:
            return "Menos de 10 dias"
        elif 10 <= dias_uteis <= 20:
            return "Entre 10 e 20 dias"
        elif dias_uteis > 20:
            return "Mais de 20 dias"
        return ""
    
    # ----------------------------------------------------
    # CASO 2: Solicitante != "Ouvidorias" (Demais Solicitantes)
    # ----------------------------------------------------
    
    # A) Motivo_Pombo
    if str(linha.get("Motivo_Pombo", "")).strip().lower() == "sim":
        if dias_uteis <= 1:
            return "Em até 1 dia"
        elif dias_uteis > 7:
            return "Mais que 7 dias"

    # B) Motivo_Barbeiro
    if str(linha.get("Motivo_Barbeiro", "")).strip().lower() == "sim":
        if 3 <= dias_uteis <= 7:
            return "De 3 a 7 dias"
        elif dias_uteis > 7:
            return "Mais que 7 dias"

    # C) Vetores com prazo limite de 7 dias
    cols_7d = [
        "Motivo_Mosquito/Dengue/Fumacê", "Motivo_Escorpião", "Motivo_Caramujo",
        "Motivo_Morcego", "Motivo_Carrapato", "Motivo_Aranha", "Motivo_Lagarta",
        "Motivo_Lacraia", "Motivo_Pulga/Bicho-de-pé"
    ]
    if any(str(linha.get(col, "")).strip().lower() == "sim" for col in cols_7d):
        if dias_uteis < 7:
            return "Menos que 7 dias"
        elif dias_uteis == 7:
            return "7 dias"
        elif dias_uteis > 7:
            return "Mais que 7 dias"

    # D) Vetores/Situações com prazo de 10 a 20 dias
    cols_10_20d = [
        "Motivo_Água Parada", "Motivo_Roedor", "Motivo_Lixo/Entulho",
        "Motivo_Acumulador", "Motivo_Vacinação Antirrábica"
    ]
    if any(str(linha.get(col, "")).strip().lower() == "sim" for col in cols_10_20d):
        if dias_uteis < 10:
            return "Menos de 10 dias"
        elif 10 <= dias_uteis <= 20:
            return "Entre 10 e 20 dias"
        elif dias_uteis > 20:
            return "Mais de 20 dias"

    return ""

## Regra do cálculo de dias úteis funciona?
NOME_COL_SOLICITACAO = "Data da solicitação"
NOME_COL_INSPECAO = "Data da inspeção"
NOME_COL_CARIMBO = "Carimbo de data/hora"
NOME_COL_SOLICITANTE = "Solicitante"

for linha in dados:
    dt_solic = linha.get(NOME_COL_SOLICITACAO, "")
    dt_insp = linha.get(NOME_COL_INSPECAO, "")
    carimbo = linha.get(NOME_COL_CARIMBO, "")
    solic = linha.get(NOME_COL_SOLICITANTE, "")
    
    # 1. Calcula os dias úteis aplicando a regra de fallback
    dias_uteis = calcular_dias_uteis_com_fallback(dt_solic, dt_insp, carimbo)
    linha["Dias_Uteis_Atendimento"] = dias_uteis if dias_uteis is not None else ""
    
    # 2. Categoriza o prazo conforme as regras do Solicitante e Motivos
    linha["Prazo_Atendimento_Categoria"] = categorizar_tempo_atendimento(dias_uteis, solic, linha)

resumo_prazos = Counter()
total_registros = len(dados)

for linha in dados:
    cat = linha.get("Prazo_Atendimento_Categoria", "")
    resumo_prazos[cat] += 1

print("\n--- RESUMO DA CLASSIFICAÇÃO DOS PRAZOS DE ATENDIMENTO ---")
print(f"Total de registros analisados: {total_registros}\n")

for categoria, qtd in resumo_prazos.most_common():
    nome_exibicao = categoria if categoria != "" else "[Sem prazo calculado / Negativo / Fora da Regra]"
    porcentagem = (qtd / total_registros) * 100
    print(f"  • {nome_exibicao:<45}: {qtd:>6} registros ({porcentagem:.1f}%)")

# 16. Salvar os dados limpos em um novo arquivo CSV
import csv
# 16.1. Defina o nome do novo arquivo de saída
NOME_ARQUIVO_SAIDA = "Planilha_Tratada_Vigilancia.csv"

if dados:
    # Captura automaticamente os nomes de todas as colunas existentes no primeiro registro
    colunas = list(dados[0].keys())

    # 16.2. Salva os dados limpos no novo arquivo CSV
    # Usamos 'utf-8-sig' para que acentos e caracteres especiais abram perfeitamente no Excel
    with open(NOME_ARQUIVO_SAIDA, mode="w", newline="", encoding="utf-8-sig") as arquivo_csv:
        writer = csv.DictWriter(arquivo_csv, fieldnames=colunas, delimiter=";") # delimiter=";" é o padrão preferido pelo Excel no Brasil
        
        # Escreve o cabeçalho e todas as linhas limpas
        writer.writeheader()
        writer.writerows(dados)

    print(f"\n✅ SUCESSO! Base de dados limpa salva em: {NOME_ARQUIVO_SAIDA}")
    print(f"Total de registros exportados: {len(dados)}")
else:
    print("⚠️ A lista de dados está vazia. Nenhum arquivo foi gerado.")

import os
caminho_completo = os.path.abspath("Planilha_Tratada_Vigilancia.csv")
print(f"📍 O seu arquivo foi salvo exatamente em:\n{caminho_completo}")