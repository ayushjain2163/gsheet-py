import os
from datetime import datetime

import pandas as pd
import streamlit as st
from pymongo import MongoClient


def normalize_key(value):
    return str(value).strip().lower()


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_currency(value):
    return f"INR {to_float(value):,.2f}"


@st.cache_resource
def get_database():
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "finance_app")
    client = MongoClient(mongo_uri)
    return client[db_name]


def get_budget(db):
    budget = db.budget.find_one({}, {"_id": 0})
    if budget:
        return budget
    budget = {
        "total_allocated": 0.0,
        "total_spent": 0.0,
        "remaining_budget": 0.0,
    }
    db.budget.insert_one(budget)
    return budget


def get_collection_frame(collection, projection=None):
    documents = list(collection.find({}, projection or {"_id": 0}))
    return pd.DataFrame(documents)


def get_next_entry_id(db):
    latest = db.entries.find_one(sort=[("entry_id", -1)])
    if not latest:
        return "E0001"
    current = str(latest["entry_id"]).replace("E", "")
    next_num = int(current) + 1 if current.isdigit() else 1
    return f"E{next_num:04d}"


def get_next_project_id(db):
    latest = db.projects.find_one(sort=[("project_id", -1)])
    if not latest:
        return "P0001"
    current = str(latest["project_id"]).replace("P", "")
    next_num = int(current) + 1 if current.isdigit() else 1
    return f"P{next_num:04d}"


def get_master_options(collection, label_key):
    values = []
    for item in collection.find({}, {"_id": 0, label_key: 1}):
        label = str(item.get(label_key, "")).strip()
        if label:
            values.append(label)
    return sorted(set(values), key=str.lower)


def upsert_vendor(db, vendor_name, vendor_code, gross_amount):
    vendor_key = normalize_key(vendor_name)
    existing_vendor = db.vendors.find_one({"vendor_name_key": vendor_key})

    if existing_vendor is None:
        db.vendors.insert_one(
            {
                "vendor_name": vendor_name,
                "vendor_name_key": vendor_key,
                "vendor_code": vendor_code,
                "total_billed": float(gross_amount),
                "total_paid": float(gross_amount),
                "balance_due": 0.0,
            }
        )
        return

    total_billed = to_float(existing_vendor.get("total_billed"))
    total_paid = to_float(existing_vendor.get("total_paid")) + float(gross_amount)
    total_billed = max(total_billed, total_paid)

    db.vendors.update_one(
        {"_id": existing_vendor["_id"]},
        {
            "$set": {
                "vendor_name": vendor_name,
                "vendor_code": vendor_code or existing_vendor.get("vendor_code", ""),
                "total_billed": total_billed,
                "total_paid": total_paid,
                "balance_due": max(total_billed - total_paid, 0.0),
            }
        },
    )


def upsert_project(db, project_name):
    project_key = normalize_key(project_name)
    if not project_key:
        return

    existing = db.projects.find_one({"project_name_key": project_key})
    if existing:
        return

    db.projects.insert_one(
        {
            "project_id": get_next_project_id(db),
            "project_name": project_name,
            "project_name_key": project_key,
        }
    )


def upsert_master_value(collection, value_key, label_key, value):
    cleaned_value = str(value).strip()
    if not cleaned_value:
        return

    normalized = normalize_key(cleaned_value)
    existing = collection.find_one({value_key: normalized})
    if existing:
        return

    collection.insert_one({label_key: cleaned_value, value_key: normalized})


def build_gadget_payload(index, division_options, district_options):
    with st.expander(f"Gadget {index + 1}", expanded=(index == 0)):
        info_col1, info_col2 = st.columns(2)
        gadget_name = info_col1.text_input(f"Gadget Name {index + 1}", key=f"gadget_name_{index}")
        project_name = info_col2.text_input(f"Project Name {index + 1}", key=f"project_name_{index}")

        loc_col1, loc_col2, loc_col3 = st.columns(3)
        division_name = loc_col1.selectbox(f"Division {index + 1}", division_options, key=f"division_{index}")
        if division_name == "Other":
            division_name = loc_col1.text_input(f"New Division {index + 1}", key=f"new_division_{index}")

        district_name = loc_col2.selectbox(f"District {index + 1}", district_options, key=f"district_{index}")
        if district_name == "Other":
            district_name = loc_col2.text_input(f"New District {index + 1}", key=f"new_district_{index}")

        taluka = loc_col3.text_input(f"Taluka {index + 1}", key=f"taluka_{index}")
        project_details = st.text_area(f"Project Details {index + 1}", key=f"project_details_{index}")

        amount_col1, amount_col2, amount_col3 = st.columns(3)
        total_amount = amount_col1.number_input(
            f"Total Amount {index + 1}",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            key=f"total_amount_{index}",
        )
        security_deposit = amount_col2.number_input(
            f"Security Deposit {index + 1}",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"security_deposit_{index}",
        )
        gst = amount_col3.number_input(
            f"GST {index + 1}",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"gst_{index}",
        )

        deduct_col1, deduct_col2, deduct_col3 = st.columns(3)
        tax = deduct_col1.number_input(
            f"Tax {index + 1}",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"tax_{index}",
        )
        vima = deduct_col2.number_input(
            f"Vima {index + 1}",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"vima_{index}",
        )
        kamgar_kalyan = deduct_col3.number_input(
            f"Kamgar Kalyan {index + 1}",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"kamgar_kalyan_{index}",
        )

        total_deduction = security_deposit + gst + tax + vima + kamgar_kalyan
        gross_cost = total_amount - total_deduction

        metric_col1, metric_col2 = st.columns(2)
        metric_col1.metric(f"Gadget {index + 1} Total Deduction", format_currency(total_deduction))
        metric_col2.metric(f"Gadget {index + 1} Gross Amount", format_currency(gross_cost))

        return {
            "gadget_no": index + 1,
            "gadget_name": gadget_name.strip(),
            "project_name": project_name.strip(),
            "division": str(division_name).strip(),
            "district": str(district_name).strip(),
            "taluka": taluka.strip(),
            "project_details": project_details.strip(),
            "total_amount": float(total_amount),
            "security_deposit": float(security_deposit),
            "gst": float(gst),
            "tax": float(tax),
            "vima": float(vima),
            "kamgar_kalyan": float(kamgar_kalyan),
            "total_deduction": float(total_deduction),
            "gross_cost": float(gross_cost),
        }


def main():
    st.set_page_config(layout="wide")
    st.title("Finance Entry Management")
    st.caption("MongoDB-backed version of the finance entry app.")

    db = get_database()
    budget = get_budget(db)

    vendors = get_collection_frame(
        db.vendors,
        {"_id": 0, "vendor_name": 1, "vendor_code": 1, "balance_due": 1},
    )
    entries = get_collection_frame(db.entries, {"_id": 0})
    entry_gadgets = get_collection_frame(db.entry_gadgets, {"_id": 0})

    total_alloc = to_float(budget["total_allocated"])
    total_spent = to_float(budget["total_spent"])
    remaining = to_float(budget["remaining_budget"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Budget", format_currency(total_alloc))
    c2.metric("Total Spent", format_currency(total_spent))
    c3.metric("Remaining Budget", format_currency(remaining))

    st.subheader("Vendor Outstanding")
    if vendors.empty:
        st.info("No vendors yet.")
    else:
        vendor_view = vendors.rename(
            columns={
                "vendor_name": "Vendor Name",
                "vendor_code": "Vendor Code",
                "balance_due": "Balance Due",
            }
        )
        st.dataframe(vendor_view, use_container_width=True)

    st.divider()
    st.header("Create Entry")

    entry_col, summary_col = st.columns([1.7, 1])

    with entry_col:
        top_left, top_mid, top_right = st.columns(3)
        vendor = top_left.text_input("Vendor Name")
        vendor_code = top_mid.text_input("Vendor Code")
        check_no = top_right.text_input("Check No")

        gadget_count = st.number_input("Number of Gadgets", min_value=1, max_value=25, value=1, step=1)
        division_options = get_master_options(db.divisions, "division_name") + ["Other"]
        district_options = get_master_options(db.districts, "district_name") + ["Other"]

        gadgets_payload = []
        for index in range(int(gadget_count)):
            gadgets_payload.append(build_gadget_payload(index, division_options, district_options))

    gross_amount = sum(row["gross_cost"] for row in gadgets_payload)
    total_deductions = sum(row["total_deduction"] for row in gadgets_payload)
    total_base_amount = sum(row["total_amount"] for row in gadgets_payload)

    with summary_col:
        st.subheader("Live Summary")
        st.metric("Budget Remaining", format_currency(remaining))
        st.metric("Entry Total Amount", format_currency(total_base_amount))
        st.metric("Entry Total Deduction", format_currency(total_deductions))
        st.metric("Entry Gross Amount", format_currency(gross_amount))

        summary_rows = pd.DataFrame(
            [
                {
                    "Gadget": row["gadget_name"] or f"Gadget {row['gadget_no']}",
                    "Project": row["project_name"],
                    "Gross": row["gross_cost"],
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
        elif any(not item["gadget_name"] for item in gadgets_payload):
            st.error("Each gadget must have a name.")
        elif any(not item["project_name"] for item in gadgets_payload):
            st.error("Each gadget must have a project name.")
        elif any(not item["division"] for item in gadgets_payload):
            st.error("Each gadget must have a division.")
        elif any(not item["district"] for item in gadgets_payload):
            st.error("Each gadget must have a district.")
        elif any(not item["taluka"] for item in gadgets_payload):
            st.error("Each gadget must have a taluka.")
        elif any(item["gross_cost"] < 0 for item in gadgets_payload):
            st.error("Gross amount for a gadget cannot be negative.")
        else:
            entry_id = get_next_entry_id(db)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            db.entries.insert_one(
                {
                    "entry_id": entry_id,
                    "date": now,
                    "vendor_name": vendor.strip(),
                    "vendor_code": vendor_code.strip(),
                    "check_no": check_no.strip(),
                    "gross_amount": float(gross_amount),
                    "gadget_count": int(gadget_count),
                    "status": "Created",
                }
            )

            gadget_docs = []
            for row in gadgets_payload:
                gadget_doc = {"entry_id": entry_id}
                gadget_doc.update(row)
                gadget_docs.append(gadget_doc)

            if gadget_docs:
                db.entry_gadgets.insert_many(gadget_docs)

            upsert_vendor(db, vendor.strip(), vendor_code.strip(), gross_amount)
            for row in gadgets_payload:
                upsert_project(db, row["project_name"])
                upsert_master_value(db.divisions, "division_name_key", "division_name", row["division"])
                upsert_master_value(db.districts, "district_name_key", "district_name", row["district"])

            db.budget.update_one(
                {},
                {
                    "$set": {
                        "total_allocated": total_alloc,
                        "total_spent": total_spent + float(gross_amount),
                        "remaining_budget": remaining - float(gross_amount),
                    }
                },
                upsert=True,
            )

            st.success(f"Entry {entry_id} created successfully.")
            st.rerun()

    st.divider()
    st.header("Entry History")

    if entries.empty:
        st.info("No entries created yet.")
        return

    entry_view = entries.rename(
        columns={
            "entry_id": "Entry ID",
            "date": "Date",
            "vendor_name": "Vendor Name",
            "vendor_code": "Vendor Code",
            "check_no": "Check No",
            "gross_amount": "Gross Amount",
            "gadget_count": "Gadget Count",
            "status": "Status",
        }
    ).sort_values("Date", ascending=False)

    st.metric("Total Gross Amount", format_currency(entry_view["Gross Amount"].apply(to_float).sum()))
    st.dataframe(entry_view, use_container_width=True, height=320)

    selected_entry = st.selectbox("View Gadgets for Entry", entry_view["Entry ID"].astype(str).tolist())
    selected_gadgets = entry_gadgets[entry_gadgets["entry_id"].astype(str) == str(selected_entry)].copy()

    if not selected_gadgets.empty:
        selected_gadgets = selected_gadgets.rename(
            columns={
                "entry_id": "Entry ID",
                "gadget_no": "Gadget No",
                "gadget_name": "Gadget Name",
                "project_name": "Project Name",
                "division": "Division",
                "district": "District",
                "taluka": "Taluka",
                "project_details": "Project Details",
                "total_amount": "Total Amount",
                "security_deposit": "Security Deposit",
                "gst": "GST",
                "tax": "Tax",
                "vima": "Vima",
                "kamgar_kalyan": "Kamgar Kalyan",
                "total_deduction": "Total Deduction",
                "gross_cost": "Gross Cost",
            }
        )
    st.dataframe(selected_gadgets, use_container_width=True, height=260)


if __name__ == "__main__":
    main()
