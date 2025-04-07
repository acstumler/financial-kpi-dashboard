import streamlit as st
import pandas as pd
import altair as alt
import io
from sklearn.ensemble import IsolationForest

st.set_page_config(page_title="Financial Report Generator", layout="centered")
st.title("📊 Financial Report Generator")

# Upload section
uploaded_file = st.file_uploader("Upload your financial data file (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        # Load file
        if uploaded_file.name.endswith('.csv'):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)

        st.success("✅ File uploaded successfully!")

        # 🛠 Handle QuickBooks-style column mapping
        if 'client_id' not in data.columns and 'Customer:Job' in data.columns:
            data['client_id'] = data['Customer:Job']

        # Clean data
        if 'transaction_date' in data.columns:
            data['transaction_date'] = pd.to_datetime(data['transaction_date'], errors='coerce')
        elif 'Date' in data.columns:
            data['transaction_date'] = pd.to_datetime(data['Date'], errors='coerce')

        if 'transaction_amount' in data.columns:
            data['transaction_amount'] = data['transaction_amount'].fillna(data['transaction_amount'].mean())
        elif 'Amount' in data.columns:
            data['transaction_amount'] = data['Amount'].fillna(data['Amount'].mean())

        data = data.drop_duplicates()

        st.subheader("🧼 Cleaned Data Preview")
        st.dataframe(data.head(10))

        # ---------------------- FILTERING SECTION ----------------------
        st.markdown("---")
        st.subheader("🔍 Filter Options")

        client_ids = data['client_id'].dropna().unique().tolist()
        selected_clients = st.multiselect("Select Client ID(s)", options=client_ids, default=client_ids)

        min_date = data['transaction_date'].min()
        max_date = data['transaction_date'].max()
        date_range = st.date_input("Select Date Range", value=(min_date, max_date))

        min_amount = float(data['transaction_amount'].min())
        max_amount = float(data['transaction_amount'].max())
        amount_range = st.slider("Select Transaction Amount Range", min_value=min_amount, max_value=max_amount, value=(min_amount, max_amount))

        # Apply filters
        filtered_data = data[
            (data['client_id'].isin(selected_clients)) &
            (data['transaction_date'] >= pd.to_datetime(date_range[0])) &
            (data['transaction_date'] <= pd.to_datetime(date_range[1])) &
            (data['transaction_amount'] >= amount_range[0]) &
            (data['transaction_amount'] <= amount_range[1])
        ]

        # ---------------------- ANOMALY DETECTION ----------------------
        st.markdown("---")
        st.subheader("🚨 Anomaly Detection")

        model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
        if len(filtered_data) >= 10:
            filtered_data['anomaly'] = model.fit_predict(filtered_data[['transaction_amount']])
            filtered_data['anomaly'] = filtered_data['anomaly'].apply(lambda x: 'Anomaly' if x == -1 else 'Normal')

            num_anomalies = (filtered_data['anomaly'] == 'Anomaly').sum()
            st.metric("Detected Anomalies", value=f"{num_anomalies}")
        else:
            filtered_data['anomaly'] = 'Not enough data'
            st.warning("⚠️ Not enough data for anomaly detection (need at least 10 records).")

        st.markdown("---")
        st.subheader("📄 Filtered Data with Anomaly Tag")
        st.dataframe(filtered_data.head(10))

        # ---------------------- SUMMARY SECTION ----------------------
        if {'client_id', 'transaction_amount', 'transaction_date'}.issubset(filtered_data.columns):
            summary = filtered_data.groupby('client_id').agg({
                'transaction_amount': 'sum',
                'transaction_date': 'max',
                'anomaly': lambda x: (x == 'Anomaly').sum() if 'Anomaly' in x.values else 0
            }).reset_index()

            st.subheader("📈 Client Summary Table")
            st.dataframe(summary)

            # ---------------------- KPI SECTION ----------------------
            st.markdown("---")
            st.subheader("📌 Key Metrics")
            total_txn = filtered_data['transaction_amount'].sum()
            num_clients = filtered_data['client_id'].nunique()
            start_date = filtered_data['transaction_date'].min().date()
            end_date = filtered_data['transaction_date'].max().date()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Transactions", f"${total_txn:,.2f}")
            col2.metric("Clients", f"{num_clients}")
            col3.metric("Date Range", f"{start_date} → {end_date}")

            # ---------------------- CHART SECTION ----------------------
            st.markdown("---")
            st.subheader("📊 Visual Insights")

            bar_chart = alt.Chart(summary).mark_bar().encode(
                x=alt.X('client_id:N', title='Client ID'),
                y=alt.Y('transaction_amount:Q', title='Total Amount'),
                tooltip=['client_id', 'transaction_amount']
            ).properties(title='Total Transaction Amount per Client')

            time_series = filtered_data.groupby('transaction_date')['transaction_amount'].sum().reset_index()
            line_chart = alt.Chart(time_series).mark_line(point=True).encode(
                x=alt.X('transaction_date:T', title='Date'),
                y=alt.Y('transaction_amount:Q', title='Total Amount'),
                tooltip=['transaction_date', 'transaction_amount']
            ).properties(title='Transaction Amount Over Time')

            st.altair_chart(bar_chart, use_container_width=True)
            st.altair_chart(line_chart, use_container_width=True)

            # ---------------------- ANOMALY VISUALIZATION ----------------------
            st.markdown("---")
            st.subheader("🔴 Anomaly Timeline")

            if 'anomaly' in filtered_data.columns:
                chart_data = filtered_data[['transaction_date', 'transaction_amount', 'anomaly']].copy()

                chart = alt.Chart(chart_data).mark_circle(size=60).encode(
                    x=alt.X('transaction_date:T', title='Transaction Date'),
                    y=alt.Y('transaction_amount:Q', title='Amount'),
                    color=alt.Color('anomaly:N', scale=alt.Scale(domain=['Normal', 'Anomaly'], range=['#1f77b4', '#e74c3c'])),
                    tooltip=['transaction_date', 'transaction_amount', 'anomaly']
                ).properties(
                    title="Detected Anomalies in Transactions Over Time",
                    width='container'
                )

                st.altair_chart(chart, use_container_width=True)

            # Convert to Excel
            @st.cache_data
            def convert_df(df):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Summary')
                processed_data = output.getvalue()
                return processed_data

            excel_file = convert_df(summary)

            # Download button
            st.download_button(
                label="📥 Download Summary Report",
                data=excel_file,
                file_name="client_summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Required columns missing: 'client_id', 'transaction_amount', 'transaction_date'")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
else:
    st.info("👈 Please upload an Excel or CSV file to begin.")