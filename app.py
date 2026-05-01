"""
Finance Dashboard - Streamlit + Google Sheets
Dashboard financeiro lúdico que lê dados de Google Sheets via n8n/Telegram.
Colunas: Data | Valor_BRL | Valor_USD | Categoria | Descricao | Cotacao(_usada)
"""
from __future__ import annotations
import re
from datetime import datetime

import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="💸 Finance Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

PURPLE = "#7c5cfc"
PINK = "#fc5c9c"
TEAL = "#3dffd0"
AMBER = "#ffb547"
CATEGORY_COLORS = [PURPLE, PINK, TEAL, AMBER, "#5cd6fc", "#c45cfc"]
DEFAULT_CATEGORIES = ["Alimentação", "Transporte", "Lazer", "Saúde", "Educação", "Outros"]
DEFAULT_SHEET_ID = "1h7MRvQ4QZ_dcR5PvO1SUf9f6zMh2gnOwim-J-Cgoxko"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
    [data-testid="stMetricLabel"] p { font-size: 0.85rem; color: #a399c7; }
    [data-testid="stMetric"] {
        background: rgba(124, 92, 252, 0.08);
        border: 1px solid rgba(124, 92, 252, 0.25);
        border-radius: 14px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)


def parse_money(val):
    """Parser robusto: aceita 9.71, 9,71, "R$ 9,71", "1.234,56" (BR), "1,234.56" (US), etc."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in ("-", ".", ","):
        return None
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Credenciais ausentes em st.secrets['gcp_service_account'].")
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


def descale_money(v, threshold, divisor):
    """Se v for inteiro grande (>= threshold), divide por divisor.
    Usado para corrigir valores que perderam decimais por locale (n8n → Sheets PT-BR)."""
    if v is None or pd.isna(v):
        return v
    if v == int(v) and abs(v) >= threshold:
        return v / divisor
    return v


@st.cache_data(ttl=300, show_spinner="Buscando dados na planilha...")
def load_data(sheet_id, worksheet_name, fix_scale=True):
    client = get_gsheet_client()
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.get_worksheet(0)
    # UNFORMATTED_VALUE = pega valor cru armazenado, sem formatação de locale
    rows = ws.get_all_records(value_render_option="UNFORMATTED_VALUE")
    df_raw = pd.DataFrame(rows)
    if df_raw.empty:
        return df_raw, df_raw
    df = df_raw.copy()
    df.columns = [c.strip() for c in df.columns]
    if "Cotacao" in df.columns and "Cotacao_usada" not in df.columns:
        df = df.rename(columns={"Cotacao": "Cotacao_usada"})
    expected = ["Data", "Valor_BRL", "Valor_USD", "Categoria", "Descricao", "Cotacao_usada"]
    for col in expected:
        if col not in df.columns:
            df[col] = None
    df["Data"] = pd.to_datetime(df["Data"].astype(str), errors="coerce", dayfirst=True, format="mixed")
    for col in ["Valor_BRL", "Valor_USD", "Cotacao_usada"]:
        df[col] = df[col].apply(parse_money)

    # Auto-correção: valores que vieram escalados da planilha (locale n8n→Sheets PT-BR)
    if fix_scale:
        # BRL/USD: integer >= 1000 → /100  (perdeu 2 casas decimais; típico R$ 49,91 → 4991)
        df["Valor_BRL"] = df["Valor_BRL"].apply(lambda v: descale_money(v, 1000, 100))
        df["Valor_USD"] = df["Valor_USD"].apply(lambda v: descale_money(v, 1000, 100))
        # Cotação: >= 100 → /10000  (típica BRL/USD é 1-10; perdeu 4 casas)
        df["Cotacao_usada"] = df["Cotacao_usada"].apply(lambda v: descale_money(v, 100, 10000))

    df["Categoria"] = df["Categoria"].fillna("Outros").astype(str).str.strip()
    df["Descricao"] = df["Descricao"].fillna("").astype(str)
    df = df.dropna(subset=["Data"]).sort_values("Data", ascending=False).reset_index(drop=True)
    return df, df_raw


def line_chart_weekly(df):
    if df.empty:
        return _empty_fig("Sem dados")
    weekly = (df.set_index("Data")["Valor_USD"]
              .resample("W-MON", label="left", closed="left").sum().reset_index())
    fig = go.Figure(go.Scatter(
        x=weekly["Data"], y=weekly["Valor_USD"], mode="lines+markers",
        line=dict(color=PURPLE, width=3, shape="spline"),
        marker=dict(size=10, color=PINK, line=dict(width=2, color="#0e0a1f")),
        fill="tozeroy", fillcolor="rgba(124, 92, 252, 0.15)",
        hovertemplate="<b>Semana de %{x|%d/%m}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=320,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#a399c7"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#a399c7", tickprefix="$"),
        showlegend=False,
        hoverlabel=dict(bgcolor="#1a1335", bordercolor=PURPLE, font_color="white"),
    )
    return fig


def donut_by_category(df):
    if df.empty:
        return _empty_fig("Sem dados")
    by_cat = df.groupby("Categoria")["Valor_USD"].sum().sort_values(ascending=False)
    fig = go.Figure(go.Pie(
        labels=by_cat.index, values=by_cat.values, hole=0.62,
        marker=dict(colors=CATEGORY_COLORS[:len(by_cat)], line=dict(color="#0e0a1f", width=3)),
        textinfo="percent", textfont=dict(color="white", size=13),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=320,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
                    font=dict(color="#f5f3ff", size=12)),
        annotations=[dict(
            text=f"<b>${by_cat.sum():,.0f}</b><br><span style='font-size:11px;color:#a399c7'>total</span>",
            showarrow=False, font=dict(size=18, color="#f5f3ff"),
        )],
    )
    return fig


def _empty_fig(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(color="#a399c7", size=14),
                       xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def build_sidebar():
    st.sidebar.title("⚙️ Configurações")
    sheet_id = st.sidebar.text_input("ID da planilha",
        value=st.secrets.get("sheet_id", DEFAULT_SHEET_ID))
    worksheet_name = st.sidebar.text_input("Nome da aba",
        value=st.secrets.get("worksheet_name", "Página1"))
    st.sidebar.divider()
    st.sidebar.subheader("💰 Orçamento (USD)")
    # Lê valor da URL (?budget=...) ou cai pro secrets, ou default 1000
    try:
        default_budget = float(st.query_params.get("budget", st.secrets.get("budget_total", 1000.0)))
    except (ValueError, TypeError):
        default_budget = float(st.secrets.get("budget_total", 1000.0))
    budget_total = st.sidebar.number_input("Total mensal", min_value=0.0,
        value=default_budget, step=50.0, key="budget_total_input")
    # Salva na URL para persistir entre reloads
    if str(budget_total) != st.query_params.get("budget", ""):
        st.query_params["budget"] = str(budget_total)
    with st.sidebar.expander("🏷️ Por categoria"):
        default_by_cat = dict(st.secrets.get("budget_by_category", {}))
        cat_budgets = {}
        for cat in DEFAULT_CATEGORIES:
            cat_budgets[cat] = st.number_input(cat, min_value=0.0,
                value=float(default_by_cat.get(cat, budget_total / len(DEFAULT_CATEGORIES))),
                step=10.0, key=f"budget_{cat}")
    st.sidebar.divider()
    fix_scale = st.sidebar.checkbox(
        "🔧 Auto-corrigir valores escalados",
        value=True,
        help="Divide BRL/USD por 100 (se inteiro ≥ 1000) e Cotação por 10000 (se ≥ 100). Use enquanto o n8n não estiver gravando decimais corretamente.",
    )
    if st.sidebar.button("🔄 Recarregar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.caption("Cache: 5 min")
    return {"sheet_id": sheet_id, "worksheet_name": worksheet_name,
            "budget_total": budget_total, "budget_by_category": cat_budgets,
            "fix_scale": fix_scale}


# === MAIN ===
st.title("💸 Finance Dashboard")
st.caption("Seus gastos em USD, em tempo real, vindos do bot do Telegram → n8n → Google Sheets ✨")

cfg = build_sidebar()

try:
    df, df_raw = load_data(cfg["sheet_id"], cfg["worksheet_name"], cfg.get("fix_scale", True))
except RuntimeError as e:
    st.error(f"❌ {e}"); st.stop()
except gspread.exceptions.APIError as e:
    st.error("❌ Erro Google Sheets API. Verifique ID, compartilhamento e APIs habilitadas.")
    st.code(str(e)); st.stop()
except Exception as e:
    st.error(f"❌ Erro inesperado: {type(e).__name__}: {e}")
    import traceback
    st.code(traceback.format_exc()); st.stop()

if df.empty:
    st.warning("📭 Planilha vazia."); st.stop()

with st.expander("🔍 Diagnóstico — comparar valores crus vs parseados", expanded=False):
    st.write("Esta tabela mostra o que **chega da planilha** (cru) vs o que o app **interpretou** (parseado). "
             "Se valores divergirem, é problema na origem (Sheets/n8n).")
    if not df_raw.empty:
        cols_diag = [c for c in ["Data", "Valor_BRL", "Valor_USD", "Cotacao", "Cotacao_usada"]
                     if c in df_raw.columns]
        diag_raw = df_raw[cols_diag].copy()
        diag_raw.columns = [f"{c} (cru)" for c in cols_diag]
        diag_parsed = pd.DataFrame({
            "Valor_BRL (parseado)": df["Valor_BRL"],
            "Valor_USD (parseado)": df["Valor_USD"],
            "Cotacao (parseado)": df["Cotacao_usada"],
        })
        st.write("**Como vieram do Google Sheets:**")
        st.dataframe(diag_raw.head(10), use_container_width=True, hide_index=True)
        st.write("**Após parse do app:**")
        st.dataframe(diag_parsed.head(10), use_container_width=True, hide_index=True)
        st.caption("💡 Se 9,71 vira **971** no cru: problema na planilha/n8n. "
                   "Se cru OK mas parseado errado: me avisa!")

df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)
months = sorted(df["AnoMes"].unique(), reverse=True)
current_month = datetime.now().strftime("%Y-%m")
default_idx = months.index(current_month) + 1 if current_month in months else 0

cf1, cf2 = st.columns([1, 3])
with cf1:
    sel_month = st.selectbox("📅 Mês", ["Todos"] + months, index=default_idx)
with cf2:
    cats_avail = sorted(df["Categoria"].unique())
    sel_cats = st.multiselect("🏷️ Categorias", cats_avail, default=cats_avail)

df_view = df.copy()
if sel_month != "Todos":
    df_view = df_view[df_view["AnoMes"] == sel_month]
if sel_cats:
    df_view = df_view[df_view["Categoria"].isin(sel_cats)]

total_usd = float(df_view["Valor_USD"].sum())
n_tx = len(df_view)
available = cfg["budget_total"] - total_usd
pct_used = (total_usd / cfg["budget_total"] * 100) if cfg["budget_total"] > 0 else 0
avg_tx = total_usd / n_tx if n_tx > 0 else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("💸 Gasto Total", f"${total_usd:,.2f}",
              f"{pct_used:.0f}% do orçamento", delta_color="inverse")
with k2:
    st.metric("🎯 Orçamento", f"${cfg['budget_total']:,.2f}",
              sel_month if sel_month != "Todos" else "período total", delta_color="off")
with k3:
    st.metric("💰 Disponível", f"${available:,.2f}",
              "✨ no verde" if available >= 0 else "⚠️ estourou",
              delta_color="normal" if available >= 0 else "inverse")
with k4:
    st.metric("🛒 Transações", n_tx, f"ticket médio ${avg_tx:,.2f}", delta_color="off")

st.divider()

g1, g2 = st.columns([1.3, 1])
with g1:
    st.subheader("📈 Evolução semanal")
    st.plotly_chart(line_chart_weekly(df_view), use_container_width=True,
                    config={"displayModeBar": False})
with g2:
    st.subheader("🍩 Por categoria")
    st.plotly_chart(donut_by_category(df_view), use_container_width=True,
                    config={"displayModeBar": False})

st.divider()

st.subheader("🎯 Progresso por categoria")
spent_by_cat = df_view.groupby("Categoria")["Valor_USD"].sum().to_dict()
for cat in DEFAULT_CATEGORIES:
    spent = float(spent_by_cat.get(cat, 0))
    budget = float(cfg["budget_by_category"].get(cat, 0))
    if budget == 0 and spent == 0:
        continue
    pct = min(spent / budget, 1.0) if budget > 0 else 0
    over = budget > 0 and spent > budget
    pct_label = (spent / budget * 100) if budget > 0 else 0
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.write(f"**{cat}**"); st.progress(pct)
    with col_b:
        emoji = "⚠️" if over else "✅"
        st.write(f"{emoji} ${spent:,.2f} / ${budget:,.2f} ({pct_label:.0f}%)")

st.divider()
st.subheader("📋 Últimas transações")
table = df_view.head(50)[["Data", "Categoria", "Descricao", "Valor_USD", "Valor_BRL", "Cotacao_usada"]].copy()
table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")
table = table.rename(columns={"Valor_USD": "USD", "Valor_BRL": "BRL",
                               "Cotacao_usada": "Cotação", "Descricao": "Descrição"})
st.dataframe(table, use_container_width=True, hide_index=True,
             column_config={
                 "USD": st.column_config.NumberColumn(format="$ %.2f"),
                 "BRL": st.column_config.NumberColumn(format="R$ %.2f"),
                 "Cotação": st.column_config.NumberColumn(format="%.4f"),
             })

st.caption(f"Mostrando {len(table)} de {n_tx} transações · "
           f"última atualização {datetime.now().strftime('%d/%m/%Y %H:%M')}")
