import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import openai
import os

# Set up page with improved layout
st.set_page_config(page_title="📊 Financial KPI Dashboard", layout="wide")

with st.container():
    st.markdown("""
        <style>
        .main {background-color: #f8f9fa;}
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        h1, h2, h3, h4 {color: #1f4e79;}
        .stMetric {padding: 1rem; background-color: #ffffff; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);}
        </style>
    """, unsafe_allow_html=True)

    st.title("📊 Financial KPI Dashboard")
    st.caption("Easily analyze financial statements and generate smart insights for small businesses, CFOs, and tax professionals.")

# --- File Upload Section ---
st.subheader("📁 Upload Your Financial Statements")
with st.expander("Upload Instructions", expanded=False):
    st.markdown("""
    - Upload Excel exports from your accounting software (GL, Profit & Loss, Balance Sheet)
    - We support multiple uploads at once
    - Files must include account names and amounts, and optionally dates
    """)

uploaded_files = st.file_uploader("Upload GL, P&L, or Balance Sheet files", type=["xlsx"], accept_multiple_files=True)

gl_data = pd.DataFrame()
pnl_data = pd.DataFrame()
bs_data = pd.DataFrame()

if uploaded_files:
    for file in uploaded_files:
        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()

            if 'Date' in df.columns and 'Account' in df.columns and 'Amount' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.dropna(subset=['Date', 'Account', 'Amount'])
                gl_data = pd.concat([gl_data, df], ignore_index=True)
            elif 'Account' in df.columns and ('Total' in df.columns or 'Amount' in df.columns):
                df['Amount'] = df['Amount'] if 'Amount' in df.columns else df['Total']
                if df['Account'].str.contains("Income|Expense|COGS", case=False).any():
                    pnl_data = pd.concat([pnl_data, df], ignore_index=True)
                elif df['Account'].str.contains("Assets|Liabilities|Equity", case=False).any():
                    bs_data = pd.concat([bs_data, df], ignore_index=True)
            else:
                st.warning(f"⚠️ Unknown format in {file.name}, skipping.")
        except Exception as e:
            st.error(f"❌ Error processing {file.name}: {e}")

# --- KPI Calculations ---
def calculate_kpis(gl_data, pnl_data, bs_data):
    kpis = {}

    if not gl_data.empty:
        total_revenue = gl_data[gl_data['Account'].str.contains("Income", case=False)]['Amount'].sum()
        total_expenses = gl_data[gl_data['Account'].str.contains("Expense|Cost of Goods Sold", case=False)]['Amount'].sum()
        cogs = gl_data[gl_data['Account'].str.contains("Cost of Goods Sold", case=False)]['Amount'].sum()
    elif not pnl_data.empty:
        total_revenue = pnl_data[pnl_data['Account'].str.contains("Income", case=False)]['Amount'].sum()
        total_expenses = pnl_data[pnl_data['Account'].str.contains("Expense|Cost of Goods Sold", case=False)]['Amount'].sum()
        cogs = pnl_data[pnl_data['Account'].str.contains("Cost of Goods Sold", case=False)]['Amount'].sum()
    else:
        total_revenue = total_expenses = cogs = 0

    net_income = total_revenue + total_expenses
    gross_profit = total_revenue + cogs
    gross_margin = gross_profit / total_revenue if total_revenue else 0
    net_margin = net_income / total_revenue if total_revenue else 0

    total_assets = bs_data[bs_data['Account'].str.contains("Assets", case=False)]['Amount'].sum() if not bs_data.empty else 0
    total_equity = bs_data[bs_data['Account'].str.contains("Equity", case=False)]['Amount'].sum() if not bs_data.empty else 0
    total_liabilities = bs_data[bs_data['Account'].str.contains("Liabilities", case=False)]['Amount'].sum() if not bs_data.empty else 0

    current_assets = bs_data[bs_data['Account'].str.contains("Current Assets", case=False)]['Amount'].sum() if not bs_data.empty else 0
    current_liabilities = bs_data[bs_data['Account'].str.contains("Current Liabilities", case=False)]['Amount'].sum() if not bs_data.empty else 0

    kpis = {
        "Total Revenue": total_revenue,
        "Total Expenses": total_expenses,
        "Net Income": net_income,
        "Gross Profit": gross_profit,
        "Gross Margin": gross_margin,
        "Net Margin": net_margin,
        "Total Assets": total_assets,
        "Total Equity": total_equity,
        "Total Liabilities": total_liabilities,
        "Current Ratio": current_assets / current_liabilities if current_liabilities else 0,
        "Debt-to-Equity Ratio": total_liabilities / total_equity if total_equity else 0,
        "Debt Ratio": total_liabilities / total_assets if total_assets else 0,
        "Return on Equity (ROE)": net_income / total_equity if total_equity else 0,
        "Return on Assets (ROA)": net_income / total_assets if total_assets else 0
    }
    return kpis

# --- KPI Display ---
if not gl_data.empty or not pnl_data.empty or not bs_data.empty:
    st.subheader("📈 Key Financial Metrics")
    kpis = calculate_kpis(gl_data, pnl_data, bs_data)
    kpi_cols = st.columns(3)
    for i, (metric, value) in enumerate(kpis.items()):
        with kpi_cols[i % 3]:
            if "Margin" in metric or "Ratio" in metric or "Return" in metric:
                st.metric(metric, f"{value:.2%}")
            else:
                st.metric(metric, f"${value:,.2f}")

    # --- Export KPIs ---
    @st.cache_data
    def export_kpis_to_excel(kpis):
        df = pd.DataFrame(kpis.items(), columns=["Metric", "Value"])
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        return output

    st.divider()
    st.download_button(
        label="📥 Download KPI Report",
        data=export_kpis_to_excel(kpis),
        file_name="financial_kpis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- GPT Q&A ---
    st.divider()
    api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY")

    if api_key:
        openai.api_key = api_key
        st.subheader("🤖 Ask a Financial Analyst (AI)")
        user_question = st.text_input("Type your question:")

        if user_question:
            try:
                prompt = "You are a financial analyst. Based on the following KPI data, answer the user's question:\n"
                for metric, value in kpis.items():
                    prompt += f"{metric}: {value}\n"
                prompt += f"\nQuestion: {user_question}\nAnswer:"

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                answer = response['choices'][0]['message']['content']
                st.success(answer)
            except Exception as e:
                st.error(f"❌ GPT Error: {e}")
    else:
        st.warning("🔑 OpenAI API key not found. Please set it in .streamlit/secrets.toml or environment variable.")
else:
    st.info("📤 Upload GL, P&L, or Balance Sheet Excel files to begin.")
