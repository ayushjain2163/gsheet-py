import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st

DB_FILE = "finance_db.xlsx"

BUDGET_COLUMNS = ["Total Allocated", "Total Spent", "Remaining Budget"]
VENDOR_COLUMNS = ["Vendor Name", "Vendor Code", "Total Billed", "Total Paid", "Balance Due"]
PROJECT_COLUMNS = ["Project ID", "Project Name"]
DIVISION_COLUMNS = ["Division Name"]
DISTRICT_COLUMNS = ["District Name"]
ENTRY_COLUMNS = [
    "Entry ID",
    "Date",
    "Vendor Name",
    "Vendor Code",
    "Check No",
    "Gross Amount",
    "Gadget Count",
    "Status",
]
ENTRY_GADGET_COLUMNS = [
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
]


def load_sheet(name, expected_columns):
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=expected_columns)

    try:
        df = pd.read_excel(DB_FILE, sheet_name=name)
    except ValueError:
        return pd.DataFrame(columns=expected_columns)

    for column in expected_columns:
        if column not in df.columns:
            df[column] = ""

    return df[expected_columns]


def save_workbook(sheets):
    db_dir = os.path.dirname(os.path.abspath(DB_FILE)) or "."
    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir=db_dir) as tmp:
            temp_file = tmp.name

        with pd.ExcelWriter(temp_file, engine="openpyxl", mode="w") as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        os.replace(temp_file, DB_FILE)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def initialize_missing_dataframes(budget, vendors, projects, divisions, districts, entries, entry_gadgets):
    if budget.empty:
        budget = pd.DataFrame([
            {
                "Total Allocated": 0.0,
                "Total Spent": 0.0,
                "Remaining Budget": 0.0,
            }
        ])

    if vendors.empty:
        vendors = pd.DataFrame(columns=VENDOR_COLUMNS)

    if projects.empty:
        projects = pd.DataFrame(columns=PROJECT_COLUMNS)

    if divisions.empty:
        divisions = pd.DataFrame(columns=DIVISION_COLUMNS)

    if districts.empty:
        districts = pd.DataFrame(columns=DISTRICT_COLUMNS)

    if entries.empty:
        entries = pd.DataFrame(columns=ENTRY_COLUMNS)

    if entry_gadgets.empty:
        entry_gadgets = pd.DataFrame(columns=ENTRY_GADGET_COLUMNS)

    if "Vendor Code" not in vendors.columns:
        vendors["Vendor Code"] = ""

    if vendors["Vendor Code"].replace("", pd.NA).isna().any():
        missing_code_idx = vendors[vendors["Vendor Code"].replace("", pd.NA).isna()].index
        for idx, vendor_idx in enumerate(missing_code_idx, start=1):
            vendors.loc[vendor_idx, "Vendor Code"] = f"V{idx:03d}"

    return budget, vendors, projects, divisions, districts, entries, entry_gadgets


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_next_entry_id(entries):
    if entries.empty:
        return "E0001"

    numeric_ids = []
    for value in entries["Entry ID"].astype(str):
        cleaned = value.strip().upper().replace("E", "")
        if cleaned.isdigit():
            numeric_ids.append(int(cleaned))

    next_num = (max(numeric_ids) + 1) if numeric_ids else 1
    return f"E{next_num:04d}"


def get_next_project_id(projects):
    if projects.empty:
        return "P0001"

    numeric_ids = []
    for value in projects["Project ID"].astype(str):
        cleaned = value.strip().upper().replace("P", "")
        if cleaned.isdigit():
            numeric_ids.append(int(cleaned))

    next_num = (max(numeric_ids) + 1) if numeric_ids else 1
    return f"P{next_num:04d}"


def find_vendor_row(vendors, vendor_name):
    normalized_name = str(vendor_name).strip().lower()
    if not normalized_name or vendors.empty:
        return None

    matches = vendors["Vendor Name"].astype(str).str.strip().str.lower() == normalized_name
    if not matches.any():
        return None

    return vendors[matches].iloc[0]


def upsert_vendor(vendors, vendor_name, vendor_code, gross_amount):
    existing_vendor = find_vendor_row(vendors, vendor_name)

    if existing_vendor is None:
        new_vendor = pd.DataFrame([
            {
                "Vendor Name": vendor_name,
                "Vendor Code": vendor_code,
                "Total Billed": float(gross_amount),
                "Total Paid": float(gross_amount),
                "Balance Due": 0.0,
            }
        ])
        return pd.concat([vendors, new_vendor], ignore_index=True)

    vendor_idx = existing_vendor.name
    current_billed = to_float(vendors.loc[vendor_idx, "Total Billed"])
    current_paid = to_float(vendors.loc[vendor_idx, "Total Paid"])
    next_paid = current_paid + float(gross_amount)
    next_billed = max(current_billed, next_paid)

    vendors.loc[vendor_idx, "Vendor Code"] = str(vendor_code).strip() or str(vendors.loc[vendor_idx, "Vendor Code"]).strip()
    vendors.loc[vendor_idx, "Total Billed"] = next_billed
    vendors.loc[vendor_idx, "Total Paid"] = next_paid
    vendors.loc[vendor_idx, "Balance Due"] = max(next_billed - next_paid, 0.0)
    return vendors


def upsert_projects(projects, gadgets_payload):
    if projects.empty:
        projects = pd.DataFrame(columns=PROJECT_COLUMNS)

    normalized_existing = set(
        projects["Project Name"].astype(str).str.strip().str.lower()
    )

    for gadget in gadgets_payload:
        project_name = str(gadget["Project Name"]).strip()
        normalized_name = project_name.lower()
        if not project_name or normalized_name in normalized_existing:
            continue

        new_project = pd.DataFrame([
            {
                "Project ID": get_next_project_id(projects),
                "Project Name": project_name,
            }
        ])
        projects = pd.concat([projects, new_project], ignore_index=True)
        normalized_existing.add(normalized_name)

    return projects


def get_master_options(df, column_name):
    if df.empty:
        return []

    values = (
        df[column_name]
        .astype(str)
        .str.strip()
    )
    values = [value for value in values.tolist() if value]
    return sorted(set(values), key=str.lower)


def upsert_master_value(df, column_name, value):
    cleaned_value = str(value).strip()
    if not cleaned_value:
        return df

    existing_values = set(
        df[column_name].astype(str).str.strip().str.lower()
    ) if not df.empty else set()

    if cleaned_value.lower() in existing_values:
        return df

    new_row = pd.DataFrame([{column_name: cleaned_value}])
    return pd.concat([df, new_row], ignore_index=True)


def format_currency(value):
    return f"INR {to_float(value):,.2f}"


def main():
    st.set_page_config(layout="wide")
    st.title("Finance Entry Management")
    st.caption("Build entries live with gadget-wise calculations, then save everything in one step.")

    budget = load_sheet("Budget", BUDGET_COLUMNS)
    vendors = load_sheet("Vendors", VENDOR_COLUMNS)
    projects = load_sheet("Projects", PROJECT_COLUMNS)
    divisions = load_sheet("Divisions", DIVISION_COLUMNS)
    districts = load_sheet("Districts", DISTRICT_COLUMNS)
    entries = load_sheet("Entries", ENTRY_COLUMNS)
    entry_gadgets = load_sheet("Entry Gadgets", ENTRY_GADGET_COLUMNS)

    budget, vendors, projects, divisions, districts, entries, entry_gadgets = initialize_missing_dataframes(
        budget, vendors, projects, divisions, districts, entries, entry_gadgets
    )

    total_alloc = to_float(budget.iloc[0]["Total Allocated"])
    total_spent = to_float(budget.iloc[0]["Total Spent"])
    remaining = to_float(budget.iloc[0]["Remaining Budget"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Budget", f"INR {total_alloc:,.2f}")
    c2.metric("Total Spent", f"INR {total_spent:,.2f}")
    c3.metric("Remaining Budget", f"INR {remaining:,.2f}")

    st.subheader("Vendor Outstanding")
    st.dataframe(vendors[["Vendor Name", "Vendor Code", "Balance Due"]], use_container_width=True)

    st.divider()

    st.header("Create Entry")
    entry_col, summary_col = st.columns([1.7, 1])

    with entry_col:
        top_left, top_mid, top_right = st.columns(3)
        vendor = top_left.text_input("Vendor Name")
        vendor_code = top_mid.text_input("Vendor Code")
        check_no = top_right.text_input("Check No")

        gadget_count = st.number_input("Number of Gadgets", min_value=1, max_value=25, value=1, step=1)
        division_options = get_master_options(divisions, "Division Name") + ["Other"]
        district_options = get_master_options(districts, "District Name") + ["Other"]

        gadgets_payload = []
        for i in range(int(gadget_count)):
            with st.expander(f"Gadget {i + 1}", expanded=(i == 0)):
                info_col1, info_col2 = st.columns(2)
                gadget_name = info_col1.text_input(f"Gadget Name {i + 1}", key=f"gadget_name_{i}")
                project_name = info_col2.text_input(f"Project Name {i + 1}", key=f"project_name_{i}")

                loc_col1, loc_col2, loc_col3 = st.columns(3)
                division_name = loc_col1.selectbox(
                    f"Division {i + 1}",
                    division_options,
                    key=f"division_{i}",
                )
                if division_name == "Other":
                    division_name = loc_col1.text_input(f"New Division {i + 1}", key=f"new_division_{i}")

                district_name = loc_col2.selectbox(
                    f"District {i + 1}",
                    district_options,
                    key=f"district_{i}",
                )
                if district_name == "Other":
                    district_name = loc_col2.text_input(f"New District {i + 1}", key=f"new_district_{i}")

                taluka = loc_col3.text_input(f"Taluka {i + 1}", key=f"taluka_{i}")
                project_details = st.text_area(f"Project Details {i + 1}", key=f"project_details_{i}")

                amount_col1, amount_col2, amount_col3 = st.columns(3)
                total_amount = amount_col1.number_input(
                    f"Total Amount {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    key=f"total_amount_{i}",
                )
                security_deposit = amount_col2.number_input(
                    f"Security Deposit {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"security_deposit_{i}",
                )
                gst = amount_col3.number_input(
                    f"GST {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"gst_{i}",
                )

                deduct_col1, deduct_col2, deduct_col3 = st.columns(3)
                tax = deduct_col1.number_input(
                    f"Tax {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"tax_{i}",
                )
                vima = deduct_col2.number_input(
                    f"Vima {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"vima_{i}",
                )
                kamgar_kalyan = deduct_col3.number_input(
                    f"Kamgar Kalyan {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"kamgar_kalyan_{i}",
                )

                total_deduction = security_deposit + gst + tax + vima + kamgar_kalyan
                gross_cost = total_amount - total_deduction

                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric(f"Gadget {i + 1} Total Deduction", format_currency(total_deduction))
                metric_col2.metric(f"Gadget {i + 1} Gross Amount", format_currency(gross_cost))

                gadgets_payload.append(
                    {
                        "Gadget No": i + 1,
                        "Gadget Name": gadget_name.strip(),
                        "Project Name": project_name.strip(),
                        "Division": str(division_name).strip(),
                        "District": str(district_name).strip(),
                        "Taluka": taluka.strip(),
                        "Project Details": project_details.strip(),
                        "Total Amount": float(total_amount),
                        "Security Deposit": float(security_deposit),
                        "GST": float(gst),
                        "Tax": float(tax),
                        "Vima": float(vima),
                        "Kamgar Kalyan": float(kamgar_kalyan),
                        "Total Deduction": float(total_deduction),
                        "Gross Cost": float(gross_cost),
                    }
                )

    gross_amount = sum(row["Gross Cost"] for row in gadgets_payload)
    total_deductions = sum(row["Total Deduction"] for row in gadgets_payload)
    total_base_amount = sum(row["Total Amount"] for row in gadgets_payload)

    with summary_col:
        st.subheader("Live Summary")
        st.metric("Budget Remaining", format_currency(remaining))
        st.metric("Entry Total Amount", format_currency(total_base_amount))
        st.metric("Entry Total Deduction", format_currency(total_deductions))
        st.metric("Entry Gross Amount", format_currency(gross_amount))

        summary_rows = pd.DataFrame(
            [
                {
                    "Gadget": row["Gadget Name"] or f"Gadget {row['Gadget No']}",
                    "Project": row["Project Name"],
                    "Gross": row["Gross Cost"],
                }
                for row in gadgets_payload
            ]
        )
        st.dataframe(summary_rows, use_container_width=True, hide_index=True, height=240)

        if gross_amount > remaining:
            st.error("Entry gross amount is above remaining budget.")
        else:
            st.success("Entry is within the remaining budget.")

    submit = st.button("Create Entry", type="primary", use_container_width=True)

    if submit:
        if not vendor.strip():
            st.error("Vendor name is required.")
        elif not vendor_code.strip():
            st.error("Vendor code is required.")
        elif not check_no.strip():
            st.error("Check No is required.")
        elif gross_amount <= 0:
            st.error("Gross amount must be greater than 0.")
        elif gross_amount > remaining:
            st.error("Sum of gadget gross costs exceeds remaining budget.")
        elif any(not item["Gadget Name"] for item in gadgets_payload):
            st.error("Each gadget must have a name.")
        elif any(not item["Project Name"].strip() for item in gadgets_payload):
            st.error("Each gadget must have a project name.")
        elif any(not item["Division"] for item in gadgets_payload):
            st.error("Each gadget must have a division.")
        elif any(not item["District"] for item in gadgets_payload):
            st.error("Each gadget must have a district.")
        elif any(not item["Taluka"] for item in gadgets_payload):
            st.error("Each gadget must have a taluka.")
        elif any(item["Gross Cost"] < 0 for item in gadgets_payload):
            st.error("Gross amount for a gadget cannot be negative.")
        else:
            entry_id = get_next_entry_id(entries)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            new_entry = pd.DataFrame([
                {
                    "Entry ID": entry_id,
                    "Date": now,
                    "Vendor Name": str(vendor).strip(),
                    "Vendor Code": str(vendor_code).strip(),
                    "Check No": check_no.strip(),
                    "Gross Amount": float(gross_amount),
                    "Gadget Count": int(gadget_count),
                    "Status": "Created",
                }
            ])

            new_gadgets = pd.DataFrame(
                [
                    {
                        "Entry ID": entry_id,
                        "Gadget No": row["Gadget No"],
                        "Gadget Name": row["Gadget Name"],
                        "Project Name": row["Project Name"],
                        "Division": row["Division"],
                        "District": row["District"],
                        "Taluka": row["Taluka"],
                        "Project Details": row["Project Details"],
                        "Total Amount": row["Total Amount"],
                        "Security Deposit": row["Security Deposit"],
                        "GST": row["GST"],
                        "Tax": row["Tax"],
                        "Vima": row["Vima"],
                        "Kamgar Kalyan": row["Kamgar Kalyan"],
                        "Total Deduction": row["Total Deduction"],
                        "Gross Cost": row["Gross Cost"],
                    }
                    for row in gadgets_payload
                ]
            )

            entries = pd.concat([entries, new_entry], ignore_index=True)
            entry_gadgets = pd.concat([entry_gadgets, new_gadgets], ignore_index=True)
            vendors = upsert_vendor(vendors, str(vendor).strip(), str(vendor_code).strip(), gross_amount)
            projects = upsert_projects(projects, gadgets_payload)
            for row in gadgets_payload:
                divisions = upsert_master_value(divisions, "Division Name", row["Division"])
                districts = upsert_master_value(districts, "District Name", row["District"])

            budget.loc[0, "Total Spent"] = to_float(budget.loc[0, "Total Spent"]) + float(gross_amount)
            budget.loc[0, "Remaining Budget"] = to_float(budget.loc[0, "Remaining Budget"]) - float(gross_amount)

            try:
                save_workbook(
                    {
                        "Budget": budget,
                        "Vendors": vendors,
                        "Projects": projects,
                        "Divisions": divisions,
                        "Districts": districts,
                        "Entries": entries,
                        "Entry Gadgets": entry_gadgets,
                    }
                )
            except PermissionError:
                st.error("Could not save finance_db.xlsx. Please close the Excel file if it is open, then try again.")
            else:
                st.success(f"Entry {entry_id} created successfully.")
                st.rerun()

    st.divider()

    st.header("Entry History")
    if entries.empty:
        st.info("No entries created yet.")
        return

    entries_view = entries.sort_values("Date", ascending=False)
    total_gross = entries_view["Gross Amount"].apply(to_float).sum()

    st.metric("Total Gross Amount", f"INR {total_gross:,.2f}")
    st.dataframe(entries_view, use_container_width=True, height=320)

    selected_entry = st.selectbox(
        "View Gadgets for Entry",
        entries_view["Entry ID"].astype(str).tolist(),
    )

    selected_gadgets = entry_gadgets[entry_gadgets["Entry ID"].astype(str) == str(selected_entry)]
    st.dataframe(selected_gadgets, use_container_width=True, height=260)


if __name__ == "__main__":
    main()
