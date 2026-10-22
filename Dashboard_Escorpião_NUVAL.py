import calendar
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------
# 1. CONFIGURAÇÃO INICIAL DA PÁGINA
# ----------------------------------------------------
st.set_page_config(
    page_title="Visitas Realizadas pelos Núcleos de Vigilância Ambiental",
    layout="wide",
)

# ----------------------------------------------------
# 2. LOCALIZAÇÃO AUTOMÁTICA DO ARQUIVO CSV
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


@st.cache_data
def carregar_dados():
  if not os.path.exists(CAMINHO_CSV):
    st.error(f"❌ Arquivo CSV não encontrado no caminho:\n`{CAMINHO_CSV}`")
    st.info(
        "Certifique-se de que o arquivo 'Planilha_Tratada_Vigilancia.csv' está"
        " salvo na mesma pasta deste script Python."
    )
    st.stop()

  df = pd.read_csv(CAMINHO_CSV, sep=";", encoding="utf-8-sig")

  # Tratamento das colunas de data da inspeção para extrair Ano e Mês
  if "Data da inspeção" in df.columns:
    df["dt_insp_parsed"] = pd.to_datetime(
        df["Data da inspeção"], format="%d/%m/%Y", errors="coerce"
    )
    df["Ano_Inspecao"] = df["dt_insp_parsed"].dt.year
    df["Num_Mes_Inspecao"] = df["dt_insp_parsed"].dt.month

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

  return df


df_raw = carregar_dados()
df = df_raw.copy()

# ----------------------------------------------------
# 3. CONFIGURAÇÃO DE TEMAS E CORES (HEX)
# ----------------------------------------------------
st.sidebar.title("⚙️ Configurações do Dashboard")
modo_tema = st.sidebar.radio("Selecione o Tema:", ["Light Mode", "Dark Mode"])

if modo_tema == "Light Mode":
  HEX_PRIMARY = "#1F77B4"  # Azul Principal
  HEX_SECONDARY = "#A1C9DF"  # Azul Claro / Apoio
  HEX_TEXT = "#2C3E50"  # Cinza Escuro
  HEX_BG = "#F4F6F9"  # Cinza Claro
  HEX_ACCENT = "#FF7F0E"  # Destaque / Alerta
  PLOT_BG = "#FFFFFF"
else:
  HEX_PRIMARY = "#00ADB5"  # Ciano / Primária
  HEX_SECONDARY = "#8E44AD"  # Roxo / Secundária
  HEX_TEXT = "#FAFAFA"  # Texto Principal
  HEX_BG = "#0E1117"  # Fundo Principal
  HEX_ACCENT = "#262730"  # Fundo de Cartões / Cards
  PLOT_BG = "#262730"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {HEX_BG};
        color: {HEX_TEXT};
    }}
    .metric-card {{
        background-color: {HEX_ACCENT if modo_tema == 'Dark Mode' else '#FFFFFF'};
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
        font-size: 15px;
        font-weight: 500;
        color: {HEX_TEXT};
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# 4. FILTROS SUSPENSOS E BOTÃO DE LIMPAR FILTROS
# ----------------------------------------------------
st.sidebar.header("🔍 Filtros de Vistoria")


# Função para redefinir todos os filtros para o estado padrão
def limpar_filtros():
  st.session_state["f_ano"] = "Todos"
  st.session_state["f_mes"] = "Todos"
  st.session_state["f_nurv"] = "Todos"
  st.session_state["f_ra"] = "Todas"
  st.session_state["f_motivo"] = "Todos"
  st.session_state["f_coleta"] = "Todas"


# Botão para limpar os filtros
st.sidebar.button(
    "🧹 Limpar Todos os Filtros",
    on_click=limpar_filtros,
    use_container_width=True,
)

# Inicialização das chaves no session_state caso não existam
if "f_ano" not in st.session_state:
  st.session_state["f_ano"] = "Todos"
if "f_mes" not in st.session_state:
  st.session_state["f_mes"] = "Todos"
if "f_nurv" not in st.session_state:
  st.session_state["f_nurv"] = "Todos"
if "f_ra" not in st.session_state:
  st.session_state["f_ra"] = "Todas"
if "f_motivo" not in st.session_state:
  st.session_state["f_motivo"] = "Todos"
if "f_coleta" not in st.session_state:
  st.session_state["f_coleta"] = "Todas"

# Filtro 1: Ano da Inspeção
if "Ano_Inspecao" in df.columns:
  anos = ["Todos"] + sorted(
      [int(x) for x in df["Ano_Inspecao"].dropna().unique()]
  )
  ano_sel = st.sidebar.selectbox("Ano da inspeção", anos, key="f_ano")
  if ano_sel != "Todos":
    df = df[df["Ano_Inspecao"] == ano_sel]

# Filtro 2: Mês da Inspeção em Ordem Cronológica (Janeiro -> Dezembro)
if "Mes_Inspecao" in df.columns and "Num_Mes_Inspecao" in df.columns:
  df_meses_ord = (
      df[["Num_Mes_Inspecao", "Mes_Inspecao"]]
      .dropna()
      .drop_duplicates()
      .sort_values("Num_Mes_Inspecao")
  )
  meses = ["Todos"] + df_meses_ord["Mes_Inspecao"].tolist()
  mes_sel = st.sidebar.selectbox("Mês da inspeção", meses, key="f_mes")
  if mes_sel != "Todos":
    df = df[df["Mes_Inspecao"] == mes_sel]

# Filtro 3: Núcleo de vigilância
col_nurv = (
    "Núcleo de vigilância"
    if "Núcleo de vigilância" in df.columns
    else ("NURV" if "NURV" in df.columns else None)
)
if col_nurv:
  nucleos = ["Todos"] + sorted(
      [x for x in df[col_nurv].dropna().unique() if str(x).strip() != ""]
  )
  nucleo_sel = st.sidebar.selectbox(
      "Núcleo de vigilância", nucleos, key="f_nurv"
  )
  if nucleo_sel != "Todos":
    df = df[df[col_nurv] == nucleo_sel]

# Filtro 4: Região Administrativa (Tratado e protegido contra erros)
if "Região Administrativa" in df.columns:
  df["Região Administrativa"] = (
      df["Região Administrativa"]
      .astype(str)
      .str.strip()
      .str.title()
  )

  ras_unicas = [
      ra
      for ra in df["Região Administrativa"].unique()
      if pd.notna(ra)
      and str(ra).lower() not in ["nan", "none", "", "null", "0"]
  ]

  ras = ["Todas"] + sorted(list(set(ras_unicas)))
  ra_sel = st.sidebar.selectbox("Região Administrativa", ras, key="f_ra")

  if ra_sel != "Todas":
    df = df[df["Região Administrativa"] == ra_sel]

# Filtro 5: Motivo da inspeção (Unificado)
colunas_motivos = [
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

motivos_existentes = [c for c in colunas_motivos if c in df.columns]
if motivos_existentes:
  opcoes_motivo = ["Todos"] + [
      c.replace("Motivo_", "") for c in motivos_existentes
  ]
  motivo_sel = st.sidebar.selectbox(
      "Motivo da inspeção", opcoes_motivo, key="f_motivo"
  )

  if motivo_sel != "Todos":
    col_alvo = f"Motivo_{motivo_sel}"
    if col_alvo in df.columns:
      df = df[df[col_alvo].astype(str).str.upper() == "SIM"]

# Filtro 6: Coleta de espécimes
if "Coleta de espécimes: SIM / NÃO" in df.columns:
  coletas = ["Todas"] + sorted(
      [
          x
          for x in df["Coleta de espécimes: SIM / NÃO"].dropna().unique()
          if str(x).strip() != ""
      ]
  )
  coleta_sel = st.sidebar.selectbox(
      "Coleta de espécimes", coletas, key="f_coleta"
  )
  if coleta_sel != "Todas":
    df = df[df["Coleta de espécimes: SIM / NÃO"] == coleta_sel]

# ----------------------------------------------------
# 5. CARTÕES DE NÚMERO
# ----------------------------------------------------
st.title("Visitas Realizadas pelos Núcleos de Vigilância Ambiental")

col_card1, col_card2 = st.columns(2)

# Cartão 1: Visitas realizadas
col_contagem_referencia = "Motivo_Mosquito/Dengue/Fumacê"
if col_contagem_referencia in df.columns:
  total_visitas = df[col_contagem_referencia].count()
else:
  total_visitas = len(df)

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

# Cartão 2: Média de dias úteis até o atendimento
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
# 6. GRÁFICOS DE BARRAS
# ----------------------------------------------------
col_g1, col_g2 = st.columns(2)

with col_g1:
  if "Solicitante" in df.columns:
    st.subheader("Solicitante")
    df_solic = df["Solicitante"].value_counts().reset_index()
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
        font_color=HEX_TEXT,
    )
    st.plotly_chart(fig_solic, use_container_width=True)

with col_g2:
  if "Uso de notificação (sim ou não?" in df.columns:
    st.subheader("Status da solicitação")
    df_status = df["Uso de notificação (sim ou não?"].value_counts().reset_index()
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
        font_color=HEX_TEXT,
    )
    st.plotly_chart(fig_status, use_container_width=True)

# ----------------------------------------------------
# 7. GRÁFICOS DE COLUNAS
# ----------------------------------------------------
col_g3, col_g4 = st.columns(2)

with col_g3:
  if "Tipo de imóvel" in df.columns:
    st.subheader("Tipo de imóvel")
    df_imovel = df["Tipo de imóvel"].value_counts().reset_index()
    df_imovel.columns = ["Tipo de imóvel", "Total"]
    df_imovel["Total_Texto"] = df_imovel["Total"].apply(formatar_numero_br)

    fig_imovel = px.bar(
        df_imovel,
        x="Tipo de imóvel",
        y="Total",
        text="Total_Texto",
        color_discrete_sequence=[HEX_PRIMARY],
    )
    fig_imovel.update_layout(
        xaxis={"categoryorder": "total descending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font_color=HEX_TEXT,
    )
    st.plotly_chart(fig_imovel, use_container_width=True)

with col_g4:
  if "Prazo_Atendimento_Categoria" in df.columns:
    st.subheader("Dias úteis até o atendimento do Núcleo")
    df_prazo = df["Prazo_Atendimento_Categoria"].value_counts().reset_index()
    df_prazo.columns = ["Prazo", "Total"]
    df_prazo["Total_Texto"] = df_prazo["Total"].apply(formatar_numero_br)

    fig_prazo = px.bar(
        df_prazo,
        x="Prazo",
        y="Total",
        text="Total_Texto",
        color_discrete_sequence=[HEX_SECONDARY],
    )
    fig_prazo.update_layout(
        xaxis={"categoryorder": "total descending"},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font_color=HEX_TEXT,
    )
    st.plotly_chart(fig_prazo, use_container_width=True)

# ----------------------------------------------------
# 8. GRÁFICO DE LINHAS
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

if colunas_existentes:
  if "dt_insp_parsed" in df.columns and df["dt_insp_parsed"].notna().any():
    df_linhas = (
        df.groupby(df["dt_insp_parsed"].dt.to_period("M"))[colunas_existentes]
        .sum()
        .reset_index()
    )
    df_linhas["dt_insp_parsed"] = df_linhas["dt_insp_parsed"].astype(str)
    eixo_x = "dt_insp_parsed"
  else:
    df_linhas = df[colunas_existentes].sum().reset_index()
    df_linhas.columns = ["Métrica", "Total"]
    df_linhas = df_linhas.sort_values(by="Total", ascending=False)
    eixo_x = "Métrica"

  fig_linhas = px.line(
      df_linhas, x=eixo_x, y=colunas_existentes, markers=True
  )
  fig_linhas.update_layout(
      paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, font_color=HEX_TEXT
  )
  st.plotly_chart(fig_linhas, use_container_width=True)