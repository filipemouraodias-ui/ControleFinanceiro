"""Teste mínimo para confirmar se o Streamlit está funcionando."""
import streamlit as st

st.set_page_config(page_title="Debug", layout="wide")

st.title("✅ Streamlit funcionando!")
st.write("Se você vê isso, o Streamlit está OK.")
st.write("Versão do Streamlit:", st.__version__)

st.success("Tudo certo até aqui.")

import sys
st.write("Python:", sys.version)

try:
    import pandas as pd
    st.write("Pandas:", pd.__version__)
except Exception as e:
    st.error(f"Erro com pandas: {e}")

try:
    import plotly
    st.write("Plotly:", plotly.__version__)
except Exception as e:
    st.error(f"Erro com plotly: {e}")

try:
    import gspread
    st.write("Gspread:", gspread.__version__)
except Exception as e:
    st.error(f"Erro com gspread: {e}")

# Testa a leitura do secrets
st.divider()
st.subheader("Secrets")
if "gcp_service_account" in st.secrets:
    sa = st.secrets["gcp_service_account"]
    st.success(f"✅ Service account encontrado: {sa.get('client_email', '?')}")
else:
    st.error("❌ Secrets não encontrado")

# Testa conexão real com a planilha
st.divider()
st.subheader("Teste de conexão com Google Sheets")
if st.button("🔌 Testar agora"):
    try:
        from google.oauth2.service_account import Credentials
        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet_id = st.secrets.get("sheet_id", "1h7MRvQ4QZ_dcR5PvO1SUf9f6zMh2gnOwim-J-Cgoxko")
        sh = client.open_by_key(sheet_id)
        st.success(f"✅ Planilha aberta: {sh.title}")
        ws = sh.get_worksheet(0)
        st.write(f"Nome da primeira aba: **{ws.title}**")
        rows = ws.get_all_records()
        st.write(f"Total de linhas: **{len(rows)}**")
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows)
            st.write("Colunas:", list(df.columns))
            st.dataframe(df.head(5))
    except Exception as e:
        st.error(f"❌ Erro: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc())
