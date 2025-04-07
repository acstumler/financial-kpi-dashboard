import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import openai
import os
from fpdf import FPDF

st.set_page_config(page_title="📊 Financial KPI Dashboard", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <style>
        .main-title {
            font-size: 3em;
            font-weight: bold;
            color: #4CAF50;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 1.2em;
            color: #666;
            text-align: center;
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 1.5em;
            font-weight: 600;
            margin-top: 30px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 Financial KPI Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Easily analyze financial statements and generate smart insights for small businesses, CFOs, and tax professionals.</div>', unsafe_allow_html=True)

# --- File Upload ---
st.markdown('<div class="section-title">📁 Upload Your Financial Statements</div>', unsafe_allow_html=True)

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

# --- PDF Summary Export ---
def generate_pdf_summary(kpis):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="Financial KPI Summary Report", ln=1, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)

    for metric, value in kpis.items():
        val = f"{value:.2%}" if "Margin" in metric or "Ratio" in metric or "Return" in metric else f"${value:,.2f}"
        pdf.cell(200, 10, txt=f"{metric}: {val}", ln=1)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

if not gl_data.empty or not pnl_data.empty or not bs_data.empty:
    kpis = calculate_kpis(gl_data, pnl_data, bs_data)

    st.markdown('<div class="section-title">📈 Key Financial Metrics</div>', unsafe_allow_html=True)
    for metric, value in kpis.items():
        if "Margin" in metric or "Ratio" in metric or "Return" in metric:
            st.metric(metric, f"{value:.2%}")
        else:
            st.metric(metric, f"${value:,.2f}")

    @st.cache_data
    def export_kpis_to_excel(kpis):
        df = pd.DataFrame(kpis.items(), columns=["Metric", "Value"])
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        return output

    kpi_excel = export_kpis_to_excel(kpis)
    st.download_button(
        label="📥 Download KPI Excel Report",
        data=kpi_excel,
        file_name="financial_kpis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    kpi_pdf = generate_pdf_summary(kpis)
    st.download_button(
        label="📄 Download KPI PDF Report",
        data=kpi_pdf,
        file_name="financial_kpis_summary.pdf",
        mime="application/pdf"
    )

    api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY")

    if api_key:
        openai.api_key = api_key
        st.markdown('<div class="section-title">💬 Ask a Question About Your Financial KPIs</div>', unsafe_allow_html=True)
        user_question = st.text_input("Enter your question:")

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
    st.info("📤 Upload one or more Excel files (GL, P&L, or BS) to begin analysis.")
