"""
Versão simplificada do dashboard — sem CSS customizado pesado.
Para testar se o problema é o HTML/CSS injetado.
"""
from datetime import datetime

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Finance Dashboard", page_icon="💸", layout="wide")

# --- DEBUG: confirma que está rodando ---
st.write("🚀 App carregado, iniciando...")

DEFAULT_SHEET_ID = "1h7MRvQ4QZ_dcR5PvO1SUf9f6zMh2gnOwim-J-Cgoxko"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
DEFAULT_CATEGORIES = ["Alimentação", "Transporte", "Lazer", "Saúde", "Educação", "Outros"]


@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300)
def load_data(sheet_id, ws_name):
    client = get_client()
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(ws_name)
    except gspread.WorksheetNotFound:
        ws = sh.get_worksheet(0)
    rows = ws.get_all_records()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df.columns = [c.strip() for c in df.columns]
    if "Cotacao" in df.columns and "Cotacao_usada" not in df.columns:
        df = df.rename(columns={"Cotacao": "Cotacao_usada"})
    df["Data"] = pd.to_datetime(df["Data"].astype(str), errors="coerce", dayfirst=True, format="mixed")
    for col in ["Valor_BRL", "Valor_USD", "Cotacao_usada"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^\d,.\-]", "", regex=True).str.replace(",", "."),
                errors="coerce",
            )
    df["Categoria"] = df.get("Categoria", "Outros").fillna("Outros").astype(str).str.strip()
    df = df.dropna(subset=["Data"]).sort_values("Data", ascending=False).reset_index(drop=True)
    return df


# --- Título ---
st.title("💸 Finance Dashboard")
st.caption("Versão simplificada de teste")

st.write("✅ Cabeçalho renderizado")

# --- Sidebar ---
st.sidebar.header("⚙️ Configurações")
sheet_id = st.sidebar.text_input("ID da planilha", value=st.secrets.get("sheet_id", DEFAULT_SHEET_ID))
ws_name = st.sidebar.text_input("Aba", value=st.secrets.get("worksheet_name", "Página1"))
budget_total = st.sidebar.number_input("Orçamento mensal (USD)", value=1000.0, step=50.0)

st.write("✅ Sidebar renderizada")

# --- Dados ---
try:
    with st.spinner("Carregando dados..."):
        df = load_data(sheet_id, ws_name)
    st.write(f"✅ Dados carregados: {len(df)} linhas")
except Exception as e:
    st.error(f"❌ Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

if df.empty:
    st.warning("Planilha vazia.")
    st.stop()

# --- Filtros ---
df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)
months = sorted(df["AnoMes"].unique(), reverse=True)
sel_month = st.selectbox("Mês", ["Todos"] + months)
df_view = df if sel_month == "Todos" else df[df["AnoMes"] == sel_month]

# --- KPIs ---
total = float(df_view["Valor_USD"].sum())
n = len(df_view)
avail = budget_total - total

c1, c2, c3, c4 = st.columns(4)
c1.metric("💸 Gasto Total", f"${total:,.2f}", f"{total/budget_total*100:.0f}% do orçamento")
c2.metric("🎯 Orçamento", f"${budget_total:,.2f}")
c3.metric("✨ Disponível", f"${avail:,.2f}", "no verde" if avail >= 0 else "estourou")
c4.metric("🛒 Transações", n, f"ticket médio ${total/n if n else 0:,.2f}")

st.divider()

# --- Gráficos ---
col_g1, col_g2 = st.columns([1.3, 1])

with col_g1:
    st.subheader("📈 Evolução semanal")
    weekly = df_view.set_index("Data")["Valor_USD"].resample("W-MON").sum().reset_index()
    fig_line = px.line(
        weekly, x="Data", y="Valor_USD", markers=True,
        color_discrete_sequence=["#7c5cfc"],
    )
    fig_line.update_layout(height=300, yaxis_tickprefix="$")
    st.plotly_chart(fig_line, use_container_width=True)

with col_g2:
    st.subheader("🍩 Por categoria")
    by_cat = df_view.groupby("Categoria")["Valor_USD"].sum().reset_index()
    fig_donut = px.pie(
        by_cat, values="Valor_USD", names="Categoria", hole=0.5,
        color_discrete_sequence=["#7c5cfc", "#fc5c9c", "#3dffd0", "#ffb547", "#5cd6fc", "#c45cfc"],
    )
    fig_donut.update_layout(height=300)
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

# --- Tabela ---
st.subheader("📋 Últimas transações")
table = df_view.head(50)[["Data", "Categoria", "Descricao", "Valor_USD", "Valor_BRL"]].copy()
table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")
st.dataframe(table, use_container_width=True, hide_index=True)

st.caption(f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
