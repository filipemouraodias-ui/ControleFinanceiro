# 💸 Finance Dashboard

Dashboard financeiro lúdico em Streamlit que lê dados de uma planilha do Google Sheets populada por um bot do Telegram via n8n.

## ✨ Features

- KPIs: gasto total, orçamento, disponível e nº de transações
- Gráfico de evolução semanal (linha suave preenchida)
- Donut com distribuição por categoria
- Barras de progresso por categoria com alerta quando ultrapassa o limite
- Tabela com últimas transações
- Filtros por mês e por categoria
- Tema escuro com paleta lúdica (roxo, rosa, verde água, âmbar)

## 📋 Requisitos

- Python 3.10+
- Conta no Google Cloud (gratuita) para criar o Service Account
- Planilha no Google Sheets com as colunas: `Data`, `Valor_BRL`, `Valor_USD`, `Categoria`, `Descricao`, `Cotacao_usada`

## 🚀 Setup local

```bash
# 1. Crie e ative um virtualenv
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure os secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml e cole o JSON do seu Service Account

# 4. Rode
streamlit run app.py
```

Vai abrir em http://localhost:8501.

## 🔑 Service Account no Google Cloud (passo a passo)

1. Acesse https://console.cloud.google.com/ e crie um projeto novo (ex.: `finance-dashboard`).
2. No menu, vá em **APIs & Services → Library** e habilite:
   - **Google Sheets API**
   - **Google Drive API**
3. Vá em **APIs & Services → Credentials → Create Credentials → Service Account**.
4. Dê um nome (ex.: `dashboard-reader`), pule as etapas opcionais e finalize.
5. Clique no Service Account criado → aba **Keys → Add Key → Create New Key → JSON**. Baixa um arquivo `.json`.
6. Abra o JSON em um editor de texto.
7. Abra `.streamlit/secrets.toml` e copie cada campo do JSON para a seção `[gcp_service_account]`.
8. Pegue o `client_email` do JSON (algo como `dashboard-reader@projeto.iam.gserviceaccount.com`).
9. Abra a planilha no Google Sheets → **Compartilhar** → cole o `client_email` com permissão de **Leitor**.

## ☁️ Deploy no Streamlit Community Cloud (gratuito)

1. Crie um repositório no GitHub e suba este projeto **sem o `.streamlit/secrets.toml`** (ele já está no `.gitignore`).
2. Acesse https://share.streamlit.io/ e faça login com GitHub.
3. Clique em **New app**, escolha o repo, branch `main`, arquivo `app.py`.
4. Antes de fazer deploy, vá em **Advanced settings → Secrets** e cole o conteúdo completo do seu `secrets.toml` (incluindo o `[gcp_service_account]`).
5. Deploy. Em ~1 minuto sua URL pública estará no ar.

## 🗂️ Estrutura

```
finance-dashboard/
├── app.py                          # dashboard Streamlit
├── requirements.txt                # dependências
├── README.md                       # este arquivo
├── .gitignore
└── .streamlit/
    ├── config.toml                 # tema escuro
    └── secrets.toml.example        # template de credenciais
```

## 🎨 Paleta

| Cor          | Hex       | Uso                                  |
|--------------|-----------|--------------------------------------|
| Roxo         | `#7c5cfc` | Primária / orçamento                 |
| Rosa         | `#fc5c9c` | Gasto total / destaques              |
| Verde água   | `#3dffd0` | Disponível / sucesso                 |
| Âmbar        | `#ffb547` | Transações / alertas suaves          |

## 📝 Formato esperado da planilha

| Data       | Valor_BRL | Valor_USD | Categoria   | Descricao            | Cotacao_usada |
|------------|-----------|-----------|-------------|----------------------|---------------|
| 28/04/2026 | 50.00     | 9.80      | Alimentação | almoço no restaurante| 5.10          |

A coluna `Data` aceita formatos com `dia/mês/ano`. Valores numéricos podem usar vírgula ou ponto.
