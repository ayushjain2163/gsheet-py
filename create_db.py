import pandas as pd

budget = pd.DataFrame([{
    "Total Allocated": 1000000,
    "Total Spent": 0,
    "Remaining Budget": 1000000
}])

vendors = pd.DataFrame([
    {"Vendor Name": "ABC Pvt Ltd", "Total Billed": 300000,
        "Total Paid": 0, "Balance Due": 300000},
    {"Vendor Name": "XYZ Infra", "Total Billed": 200000,
        "Total Paid": 0, "Balance Due": 200000}
])

projects = pd.DataFrame([
    {"Project ID": "P1", "Project Name": "Road Work",
        "Vendor Assigned": "ABC Pvt Ltd", "Total Project Cost": 300000},
    {"Project ID": "P2", "Project Name": "Drain Work",
        "Vendor Assigned": "XYZ Infra", "Total Project Cost": 200000}
])

ledger = pd.DataFrame(columns=[
    "Date", "Vendor Name", "Project", "Cheque Amount", "Status"
])

with pd.ExcelWriter("finance_db.xlsx") as writer:
    budget.to_excel(writer, sheet_name="Budget", index=False)
    vendors.to_excel(writer, sheet_name="Vendors", index=False)
    projects.to_excel(writer, sheet_name="Projects", index=False)
    ledger.to_excel(writer, sheet_name="Cheque Distribution", index=False)

print("✅ finance_db.xlsx created successfully")
