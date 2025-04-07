import pandas as pd

# Sample financial data
data = pd.DataFrame({
    'client_id': [101, 102, 103, 101, 104, 102, 105],
    'transaction_amount': [1000, 2000, 1500, None, 3000, 2000, 5000],
    'transaction_date': ['2025-03-01', '2025-03-02', '2025-03-01', '2025-03-03', '2025-03-02', '2025-03-04', '2025-03-05']
})

# Clean data
data['transaction_date'] = pd.to_datetime(data['transaction_date'])
data['transaction_amount'].fillna(data['transaction_amount'].mean(), inplace=True)
data = data.drop_duplicates()

# Aggregate data
summary = data.groupby('client_id').agg({
    'transaction_amount': 'sum',
    'transaction_date': 'max'
}).reset_index()

# Save to Excel
summary.to_excel('client_summary.xlsx', index=False)

print("✅ Financial summary report generated successfully!")