import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------
# 1. CONFIGURAÇÃO INICIAL DA PÁGINA
# ----------------------------------------------------
st.set_page_config(
    page_title="Demandas Atendidas pelos Núcleos de Vigilância Ambiental",
    layout="wide",
)

# ----------------------------------------------------
# 2. CORES FIXAS (LIGHT MODE)
# ----------------------------------------------------
HEX_PRIMARY = "#1F77B4"  # Azul Principal
HEX_SECONDARY = "#2E7D32"  # Verde Escuro
HEX_TEXT = "#2C3E50"  # Cinza Escuro
HEX_BG = "#F4F6F9"  # Cinza Claro
HEX_ACCENT = "#FFFFFF"  # Fundo dos Cards
PLOT_BG = "#FFFFFF"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {HEX_BG};
        color: {HEX_TEXT};
    }}
    .metric-card {{
        background-color: {HEX_ACCENT};
        padding: 20px;
        border-radius: 10px;
        border: 1px solid {HEX_SECONDARY};
        text-align: center;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }}
    .metric-number {{
        font-size: 38px;
        font-weight: bold;
        color: {HEX_PRIMARY};
        margin-bottom: 5px;
    }}
    .metric-label {{
        font-size: 16px;
        font-weight: bold;
        color: {HEX_TEXT};
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# 3. CARREGAMENTO DOS DADOS (BASEADO EM CARIMBO DATA/HORA)
# ----------------------------------------------------
DIRETORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CAMINHO_CSV = os.path.join(DIRETORIO_SCRIPT, "Planilha_Tratada_Vigilancia.csv")


def formatar_numero_br(valor):
  """Formata números com separador de milhar por ponto (ex: 24.856)"""
  try:
    val = int(round(valor))
    return f"{val:,}".replace(",", ".")
  except Exception:
    return str(valor)


def padronizar_solicitante(val):
  if pd.isna(val):
    return ""
  txt = str(val).strip()
  txt_lower = txt.lower()

  if (
      not txt
      or txt_lower
      in ["nan", "none", "", "null", "0", "(vazio)", "xxxx", "test", "teste"]
  ):
    return ""

  if txt_lower in ["outros", "outro", "diversos"]:
    return "Outros"

  # 1. Categorias específicas da lista oficial
  if any(k in txt_lower for k in ["bombeiro", "cbmdf"]):
    return "Bombeiros"
  if any(k in txt_lower for k in ["denúncia", "denuncia", "anônimo", "anonimo"]):
    return "Denúncia / Anônimo"
  if any(
      k in txt_lower
      for k in [
          "escola",
          "colégio",
          "colegio",
          "universidade",
          "unb",
          "faculdade",
          "ensino",
          "creche",
      ]
  ):
    return "Instituição de Ensino"
  if "ofício" in txt_lower or "oficio" in txt_lower:
    return "Ofício"
  if any(
      k in txt_lower for k in ["ouvidoria", "participa df", "e-ouv", "e-ouvidoria"]
  ):
    return "Ouvidorias"
  if any(
      k in txt_lower for k in ["polícia", "policia", "pmdf", "pcdf", "delegacia"]
  ):
    return "Polícia"
  if any(k in txt_lower for k in ["sei", "processo"]):
    return "Processos SEI"
  if any(
      k in txt_lower
      for k in [
          "gdf",
          "órgão público",
          "orgao publico",
          "secretaria",
          "administração",
          "administracao",
          "caesb",
          "neoenergia",
          "slu",
          "novacap",
      ]
  ):
    return "Órgão Público / GDF"

  # 2. Se tiver nome de pessoa -> "Pessoa física"
  partes = [p for p in txt.split() if p.isalpha()]
  if len(partes) >= 1 and not any(char.isdigit() for char in txt):
    return "Pessoa física"

  # 3. Caso contrário -> "Outros"
  return "Outros"


@st.cache_data(ttl="5m")
def carregar_dados():
  if not os.path.exists(CAMINHO_CSV):
    st.error(f"❌ Arquivo CSV não encontrado no caminho:\n`{CAMINHO_CSV}`")
    st.info(
        "Certifique-se de que o arquivo 'Planilha_Tratada_Vigilancia.csv' está"
        " salvo na mesma pasta deste script Python."
    )
    st.stop()

  df = pd.read_csv(CAMINHO_CSV, sep=";", encoding="utf-8-sig", low_memory=False)

  # Busca ou identifica a coluna de Carimbo de data/hora
  col_carimbo = None
  for c in [
      "Carimbo de data/hora",
      "Carimbo de data / hora",
      "Carimbo de data/hora ",
      "Timestamp",
  ]:
    if c in df.columns:
      col_carimbo = c
      break

  if not col_carimbo:
    col_carimbo = df.columns[0]

  df["COLUNA_CONTAGEM_REF"] = df[col_carimbo]

  # Parsing de datas a partir do Carimbo de data/hora
  df["dt_carimbo_parsed"] = pd.to_datetime(
      df["COLUNA_CONTAGEM_REF"], errors="coerce", dayfirst=True
  )

  # Extração de Ano e Mês diretamente do Carimbo de data/hora
  df["Ano_Inspecao"] = df["dt_carimbo_parsed"].dt.year
  df["Num_Mes_Inspecao"] = df["dt_carimbo_parsed"].dt.month

  mapa_meses = {
      1: "Janeiro",
      2: "Fevereiro",
      3: "Março",
      4: "Abril",
      5: "Maio",
      6: "Junho",
      7: "Julho",
      8: "Agosto",
      9: "Setembro",
      10: "Outubro",
      11: "Novembro",
      12: "Dezembro",
  }
  df["Mes_Inspecao"] = df["Num_Mes_Inspecao"].map(mapa_meses)

  # Tratamento das Regiões Administrativas
  def formatar_ra_segura(val):
    if pd.isna(val):
      return ""
    txt = str(val).strip()
    if txt.upper() in ["RIACHO FUNDO II", "RIACHO FUNDO 2"]:
      return "Riacho Fundo II"
    elif txt.upper() == "RIACHO FUNDO":
      return "Riacho Fundo"
    else:
      return txt.title().replace(" Ii", " II")

  if "Região Administrativa" in df.columns:
    df["Região Administrativa"] = df["Região Administrativa"].apply(
        formatar_ra_segura
    )

  # Tratamento do Solicitante
  if "Solicitante" in df.columns:
    df["Solicitante"] = df["Solicitante"].apply(padronizar_solicitante)

  # Mapeamento do Núcleo de Vigilância
  col_nurv_origem = None
  for c in [
      "Núcleo de Vigilância",
      "Núcleo de vigilância",
      "NURV",
      "Núcleo",
      "Nucleo",
      "Nucleo de vigilancia",
  ]:
    if c in df.columns:
      col_nurv_origem = c
      break

  if col_nurv_origem and col_nurv_origem != "Núcleo de Vigilância":
    df["Núcleo de Vigilância"] = df[col_nurv_origem]

  return df


df_raw = carregar_dados()
df = df_raw.copy()

# Lista de colunas de Motivos da Inspeção
COLUNAS_MOTIVOS = [
    "Motivo_Mosquito/Dengue/Fumacê",
    "Motivo_Água Parada",
    "Motivo_Escorpião",
    "Motivo_Roedor",
    "Motivo_Lixo/Entulho",
    "Motivo_Pombo",
    "Motivo_Caramujo",
    "Motivo_Morcego",
    "Motivo_Carrapato",
    "Motivo_Aranha",
    "Motivo_Lagarta",
    "Motivo_Barbeiro",
    "Motivo_Lacraia",
    "Motivo_Pulga/Bicho-de-pé",
    "Motivo_Acumulador",
    "Motivo_Vacinação Antirrábica",
]

# ----------------------------------------------------
# 4. PAINEL DE FILTROS (SIDEBAR)
# ----------------------------------------------------
st.sidebar.header("🔍 Filtros")


def recarregar_dados_completos():
  st.cache_data.clear()


st.sidebar.button(
    "🔄 Atualizar Dados",
    on_click=recarregar_dados_completos,
    use_container_width=True,
)


def limpar_filtros():
  st.session_state["f_ano"] = "Todos"
  st.session_state["f_mes"] = "Todos"
  st.session_state["f_nurv"] = "Todos"
  st.session_state["f_ra"] = []
  st.session_state["f_motivo"] = "Todos"
  st.session_state["f_coleta"] = "Todas"


st.sidebar.button(
    "🧹 Limpar Todos os Filtros",
    on_click=limpar_filtros,
    use_container_width=True,
)

if "f_ano" not in st.session_state:
  st.session_state["f_ano"] = "Todos"
if "f_mes" not in st.session_state:
  st.session_state["f_mes"] = "Todos"
if "f_nurv" not in st.session_state:
  st.session_state["f_nurv"] = "Todos"
if "f_ra" not in st.session_state:
  st.session_state["f_ra"] = []
if "f_motivo" not in st.session_state:
  st.session_state["f_motivo"] = "Todos"
if "f_coleta" not in st.session_state:
  st.session_state["f_coleta"] = "Todas"

# Filtro 1: Ano
if "Ano_Inspecao" in df_raw.columns:
  anos_validos = sorted([
      str(int(x))
      for x in df_raw["Ano_Inspecao"].dropna().unique()
      if float(x) > 0
  ])
  anos = ["Todos"] + anos_validos
  ano_sel = st.sidebar.selectbox("Ano da inspeção", anos, key="f_ano")
  if ano_sel != "Todos":
    df = df[df["Ano_Inspecao"].fillna(0).astype(int).astype(str) == str(ano_sel)]

# Filtro 2: Mês
if "Mes_Inspecao" in df_raw.columns and "Num_Mes_Inspecao" in df_raw.columns:
  df_meses_ord = (
      df_raw[["Num_Mes_Inspecao", "Mes_Inspecao"]]
      .dropna()
      .drop_duplicates()
      .sort_values("Num_Mes_Inspecao")
  )
  meses = ["Todos"] + df_meses_ord["Mes_Inspecao"].tolist()
  mes_sel = st.sidebar.selectbox("Mês da inspeção", meses, key="f_mes")
  if mes_sel != "Todos":
    df = df[df["Mes_Inspecao"] == mes_sel]

# Filtro 3: Núcleo
if "Núcleo de Vigilância" in df_raw.columns:
  nucleos_unicos = sorted([
      str(x).strip()
      for x in df_raw["Núcleo de Vigilância"].dropna().unique()
      if str(x).strip() not in ["nan", "none", "", "null", "0"]
  ])
  nucleos = ["Todos"] + nucleos_unicos
  nucleo_sel = st.sidebar.selectbox(
      "Núcleo de Vigilância", nucleos, key="f_nurv"
  )
  if nucleo_sel != "Todos":
    df = df[df["Núcleo de Vigilância"] == nucleo_sel]

# Filtro 4: Região Administrativa (Multi-Seleção)
if "Região Administrativa" in df_raw.columns:
  ras_unicas = [
      ra
      for ra in df_raw["Região Administrativa"].dropna().unique()
      if str(ra).lower() not in ["nan", "none", "", "null", "0"]
  ]
  ras_ordenadas = sorted(list(set(ras_unicas)))

  ra_sel = st.sidebar.multiselect(
      "Região Administrativa (Multi-Seleção)",
      ras_ordenadas,
      key="f_ra",
      placeholder="Selecione uma ou mais RAs...",
  )

  if ra_sel:
    df = df[df["Região Administrativa"].isin(ra_sel)]

# Filtro 5: Motivo da inspeção
motivos_existentes = [c for c in COLUNAS_MOTIVOS if c in df_raw.columns]
if motivos_existentes:
  lista_motivos_limpos = sorted(
      [c.replace("Motivo_", "") for c in motivos_existentes]
  )
  opcoes_motivo = ["Todos"] + lista_motivos_limpos
  motivo_sel = st.sidebar.selectbox(
      "Motivo da inspeção", opcoes_motivo, key="f_motivo"
  )

  if motivo_sel != "Todos":
    col_alvo = f"Motivo_{motivo_sel}"
    if col_alvo in df.columns:
      df = df[df[col_alvo].astype(str).str.upper() == "SIM"]

# Filtro 6: Coleta de espécimes
if "Coleta de espécimes: SIM / NÃO" in df_raw.columns:
  coletas = ["Todas"] + sorted(
      [
          x
          for x in df_raw["Coleta de espécimes: SIM / NÃO"].dropna().unique()
          if str(x).strip() != ""
      ]
  )
  coleta_sel = st.sidebar.selectbox(
      "Coleta de espécimes", coletas, key="f_coleta"
  )
  if coleta_sel != "Todas":
    df = df[df["Coleta de espécimes: SIM / NÃO"] == coleta_sel]

# ----------------------------------------------------
# 5. TÍTULO E EXPORTAÇÃO
# ----------------------------------------------------
st.title("Demandas Atendidas pelos Núcleos de Vigilância Ambiental")

col_tit_1, col_tit_2 = st.columns([3, 1])
with col_tit_2:
  csv_filtrado = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
  st.download_button(
      label="📥 Exportar Dados (CSV)",
      data=csv_filtrado,
      file_name="Dados_Filtrados_Vigilancia.csv",
      mime="text/csv",
      use_container_width=True,
  )

# ----------------------------------------------------
# 6. CARTÕES DE NÚMERO
# ----------------------------------------------------
col_card1, col_card2 = st.columns(2)

total_visitas = df["COLUNA_CONTAGEM_REF"].count()
total_visitas_str = formatar_numero_br(total_visitas)

with col_card1:
  st.markdown(
      f"""
        <div class="metric-card">
            <div class="metric-number">{total_visitas_str}</div>
            <div class="metric-label">Visitas realizadas</div>
        </div>
    """,
      unsafe_allow_html=True,
  )

media_dias = (
    pd.to_numeric(df["Dias_Uteis_Atendimento"], errors="coerce").mean()
    if "Dias_Uteis_Atendimento" in df.columns
    else 0
)
valor_media_str = (
    f"{media_dias:.1f}".replace(".", ",") if pd.notna(media_dias) else "N/A"
)

with col_card2:
  st.markdown(
      f"""
        <div class="metric-card">
            <div class="metric-number">{valor_media_str}</div>
            <div class="metric-label">Média de dias úteis até o atendimento</div>
        </div>
    """,
      unsafe_allow_html=True,
  )

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------
# 7. GRÁFICOS INICIAIS (RA E NÚCLEO)
# ----------------------------------------------------
col_g1, col_g2 = st.columns(2)

with col_g1:
  if "Região Administrativa" in df.columns and len(df) > 0:
    st.subheader("Região Administrativa")
    df_ra_chart = (
        df.groupby("Região Administrativa")["COLUNA_CONTAGEM_REF"]
        .count()
        .reset_index(name="Total")
        .sort_values(by="Total", ascending=False)
    )
    df_ra_chart["Total_Texto"] = df_ra_chart["Total"].apply(formatar_numero_br)

    fig_ra = px.bar(
        df_ra_chart,
        x="Total",
        y="Região Administrativa",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_PRIMARY],
    )
    fig_ra.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_ra, use_container_width=True)

with col_g2:
  if "Núcleo de Vigilância" in df.columns and len(df) > 0:
    st.subheader("Núcleo de Vigilância")
    df_nurv_chart = (
        df.groupby("Núcleo de Vigilância")["COLUNA_CONTAGEM_REF"]
        .count()
        .reset_index(name="Total")
        .sort_values(by="Total", ascending=False)
    )
    df_nurv_chart["Total_Texto"] = df_nurv_chart["Total"].apply(
        formatar_numero_br
    )

    fig_nurv = px.bar(
        df_nurv_chart,
        x="Total",
        y="Núcleo de Vigilância",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_SECONDARY],
    )
    fig_nurv.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_nurv, use_container_width=True)

# ----------------------------------------------------
# 8. NOVO GRÁFICO UNIFICADO: MOTIVO DA INSPEÇÃO (LOGO APÓS RA E NÚCLEO)
# ----------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
if len(df) > 0:
  st.subheader("Motivo da Inspeção")
  motivos_contagem = []

  # Calcula a contagem de linhas onde cada motivo foi igual a 'SIM'
  for col_motivo in COLUNAS_MOTIVOS:
    if col_motivo in df.columns:
      nome_motivo_limpo = col_motivo.replace("Motivo_", "")
      qtd_sim = (df[col_motivo].astype(str).str.upper() == "SIM").sum()
      if qtd_sim > 0:
        motivos_contagem.append(
            {"Motivo": nome_motivo_limpo, "Total": qtd_sim}
        )

  if motivos_contagem:
    df_motivos_chart = pd.DataFrame(motivos_contagem).sort_values(
        by="Total", ascending=False
    )
    df_motivos_chart["Total_Texto"] = df_motivos_chart["Total"].apply(
        formatar_numero_br
    )

    fig_motivos = px.bar(
        df_motivos_chart,
        x="Total",
        y="Motivo",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_PRIMARY],
    )
    fig_motivos.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_motivos, use_container_width=True)

# ----------------------------------------------------
# 9. DEMAIS GRÁFICOS DA DASHBOARD
# ----------------------------------------------------
col_g3, col_g4 = st.columns(2)

with col_g3:
  if "Solicitante" in df.columns and len(df) > 0:
    st.subheader("Solicitante")
    df_solic = (
        df.groupby("Solicitante")["COLUNA_CONTAGEM_REF"]
        .count()
        .reset_index(name="Total")
        .sort_values(by="Total", ascending=False)
    )
    df_solic.columns = ["Solicitante", "Total"]
    df_solic["Total_Texto"] = df_solic["Total"].apply(formatar_numero_br)

    fig_solic = px.bar(
        df_solic,
        x="Total",
        y="Solicitante",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_PRIMARY],
    )
    fig_solic.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_solic, use_container_width=True)

with col_g4:
  if "Uso de notificação (sim ou não?" in df.columns and len(df) > 0:
    st.subheader("Status da solicitação")
    df_status = (
        df.groupby("Uso de notificação (sim ou não?")["COLUNA_CONTAGEM_REF"]
        .count()
        .reset_index(name="Total")
        .sort_values(by="Total", ascending=False)
    )
    df_status.columns = ["Status", "Total"]
    df_status["Total_Texto"] = df_status["Total"].apply(formatar_numero_br)

    fig_status = px.bar(
        df_status,
        x="Total",
        y="Status",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_SECONDARY],
    )
    fig_status.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_status, use_container_width=True)

col_g5, col_g6 = st.columns(2)

with col_g5:
  if "Tipo de imóvel" in df.columns and len(df) > 0:
    st.subheader("Tipo de imóvel")
    df_imovel = (
        df.groupby("Tipo de imóvel")["COLUNA_CONTAGEM_REF"]
        .count()
        .reset_index(name="Total")
        .sort_values(by="Total", ascending=False)
    )
    df_imovel.columns = ["Tipo de imóvel", "Total"]
    df_imovel["Total_Texto"] = df_imovel["Total"].apply(formatar_numero_br)

    fig_imovel = px.bar(
        df_imovel,
        x="Total",
        y="Tipo de imóvel",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_PRIMARY],
    )
    fig_imovel.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_imovel, use_container_width=True)

with col_g6:
  if "Prazo_Atendimento_Categoria" in df.columns and len(df) > 0:
    st.subheader("Dias úteis até o atendimento do Núcleo")
    df_prazo = (
        df.groupby("Prazo_Atendimento_Categoria")["COLUNA_CONTAGEM_REF"]
        .count()
        .reset_index(name="Total")
        .sort_values(by="Total", ascending=False)
    )
    df_prazo.columns = ["Prazo", "Total"]
    df_prazo["Total_Texto"] = df_prazo["Total"].apply(formatar_numero_br)

    fig_prazo = px.bar(
        df_prazo,
        x="Total",
        y="Prazo",
        orientation="h",
        text="Total_Texto",
        color_discrete_sequence=[HEX_SECONDARY],
    )
    fig_prazo.update_layout(
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=HEX_TEXT, weight="bold"),
    )
    st.plotly_chart(fig_prazo, use_container_width=True)

# ----------------------------------------------------
# 10. GRÁFICO DE LINHAS
# ----------------------------------------------------
st.subheader("📈 Monitoramento de Espécimes e Caixas")

colunas_linhas = [
    "Quantidade de espécimes encontrados (insetos ou animais peçonhentos)",
    "Quantidade de Caixas Inspecionadas (escorpiões)",
    "Quantidade de Caixas Positivas (escorpiões)",
    "Quantidade de Caixas Inspecionadas (Roedores)",
    "Quantidade de Caixas Positivas (Roedores)",
    "N° Tocas/ninheiras (Roedores)",
]

colunas_existentes = [c for c in colunas_linhas if c in df.columns]

if colunas_existentes and len(df) > 0:
  if "dt_carimbo_parsed" in df.columns and df["dt_carimbo_parsed"].notna().any():
    df_linhas = (
        df.groupby(df["dt_carimbo_parsed"].dt.to_period("M"))[colunas_existentes]
        .sum()
        .reset_index()
    )
    df_linhas["dt_carimbo_parsed"] = df_linhas["dt_carimbo_parsed"].astype(str)
    eixo_x = "dt_carimbo_parsed"
  else:
    df_linhas = df[colunas_existentes].sum().reset_index()
    df_linhas.columns = ["Métrica", "Total"]
    df_linhas = df_linhas.sort_values(by="Total", ascending=False)
    eixo_x = "Métrica"

  fig_linhas = px.line(
      df_linhas, x=eixo_x, y=colunas_existentes, markers=True
  )
  fig_linhas.update_layout(
      paper_bgcolor=PLOT_BG,
      plot_bgcolor=PLOT_BG,
      font=dict(color=HEX_TEXT, weight="bold"),
  )
  st.plotly_chart(fig_linhas, use_container_width=True)