import streamlit as st
st.set_page_config(page_title="NovaFi | Financial Insights Dashboard", layout="wide")

import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from fpdf import FPDF
import os

# --- NovaFi Branding ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Unica+One&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Unica One', sans-serif;
            background-color: #f4e2c2;
            color: #234f43;
        }

        .reportview-container .main .block-container{
            padding-top: 2rem;
            padding-right: 2rem;
            padding-left: 2rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Archivo Black', sans-serif;
            color: #ba4a1e;
        }
    </style>
""", unsafe_allow_html=True)

st.image("NovaFi.png", width=150)
st.title("✨ NovaFi | Financial Insights Dashboard")

# --- File Upload ---
uploaded_files = st.file_uploader("Upload your financial statements (GL, P&L, BS - Excel format)", type=["xlsx"], accept_multiple_files=True)

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

    return {
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

# --- Generate PDF ---
def generate_pdf_summary(kpis):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="NovaFi KPI Summary Report", ln=1, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    for metric, value in kpis.items():
        val = f"{value:.2%}" if "Margin" in metric or "Ratio" in metric or "Return" in metric else f"${value:,.2f}"
        pdf.cell(200, 10, txt=f"{metric}: {val}", ln=1)
    pdf_output = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_output)

# --- Display Results ---
if not gl_data.empty or not pnl_data.empty or not bs_data.empty:
    kpis = calculate_kpis(gl_data, pnl_data, bs_data)

    st.subheader("📊 Key Financial Metrics")
    for metric, value in kpis.items():
        if "Margin" in metric or "Ratio" in metric or "Return" in metric:
            st.metric(metric, f"{value:.2%}")
        else:
            st.metric(metric, f"${value:,.2f}")

    kpi_pdf = generate_pdf_summary(kpis)
    st.download_button("📄 Download KPI Report as PDF", data=kpi_pdf, file_name="kpi_report.pdf", mime="application/pdf")
else:
    st.info("📤 Upload one or more Excel files (GL, P&L, or BS) to begin analysis.")
