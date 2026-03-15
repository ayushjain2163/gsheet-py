import pandas as pd

budget = pd.DataFrame([
    {
        "Total Allocated": 1000000,
        "Total Spent": 0,
        "Remaining Budget": 1000000,
    }
])

vendors = pd.DataFrame([
    {
        "Vendor Name": "ABC Pvt Ltd",
        "Vendor Code": "V001",
        "Total Billed": 300000,
        "Total Paid": 0,
        "Balance Due": 300000,
    },
    {
        "Vendor Name": "XYZ Infra",
        "Vendor Code": "V002",
        "Total Billed": 200000,
        "Total Paid": 0,
        "Balance Due": 200000,
    },
])

projects = pd.DataFrame(columns=[
    "Project ID",
    "Project Name",
])

divisions = pd.DataFrame(columns=[
    "Division Name",
])

districts = pd.DataFrame(columns=[
    "District Name",
])

entries = pd.DataFrame(columns=[
    "Entry ID",
    "Date",
    "Vendor Name",
    "Vendor Code",
    "Check No",
    "Gross Amount",
    "Gadget Count",
    "Status",
])

entry_gadgets = pd.DataFrame(columns=[
    "Entry ID",
    "Gadget No",
    "Gadget Name",
    "Project Name",
    "Division",
    "District",
    "Taluka",
    "Project Details",
    "Total Amount",
    "Security Deposit",
    "GST",
    "Tax",
    "Vima",
    "Kamgar Kalyan",
    "Total Deduction",
    "Gross Cost",
])

with pd.ExcelWriter("finance_db.xlsx") as writer:
    budget.to_excel(writer, sheet_name="Budget", index=False)
    vendors.to_excel(writer, sheet_name="Vendors", index=False)
    projects.to_excel(writer, sheet_name="Projects", index=False)
    divisions.to_excel(writer, sheet_name="Divisions", index=False)
    districts.to_excel(writer, sheet_name="Districts", index=False)
    entries.to_excel(writer, sheet_name="Entries", index=False)
    entry_gadgets.to_excel(writer, sheet_name="Entry Gadgets", index=False)

print("finance_db.xlsx created successfully")
