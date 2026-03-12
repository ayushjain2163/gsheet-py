import streamlit as st
import pandas as pd
from datetime import datetime

DB_FILE = "finance_db.xlsx"


# ---------- LOAD FUNCTIONS ----------
def load_sheet(name):
    return pd.read_excel(DB_FILE, sheet_name=name)


def save_sheet(df, name):
    with pd.ExcelWriter(
        DB_FILE,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace"
    ) as writer:
        df.to_excel(writer, sheet_name=name, index=False)


# ---------- MAIN APP ----------
def main():
    st.set_page_config(layout="wide")
    st.title("💰 Finance Cheque Management (Excel Backend)")

    budget = load_sheet("Budget")
    vendors = load_sheet("Vendors")
    projects = load_sheet("Projects")
    ledger = load_sheet("Cheque Distribution")

    total_alloc = float(budget.iloc[0]["Total Allocated"])
    total_spent = float(budget.iloc[0]["Total Spent"])
    remaining = float(budget.iloc[0]["Remaining Budget"])

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Budget", total_alloc)
    c2.metric("Total Spent", total_spent)
    c3.metric("Remaining Budget", remaining)

    st.subheader("Vendor Outstanding")
    st.dataframe(vendors[["Vendor Name", "Balance Due"]])

    st.divider()

    # ---------------- ISSUE CHEQUE ----------------
    st.header("✍️ Issue Cheque")

    with st.form("cheque_form"):

        vendor = st.selectbox("Vendor", vendors["Vendor Name"])
        project = st.selectbox("Project", projects["Project Name"])

        vendor_row = vendors[vendors["Vendor Name"] == vendor].iloc[0]
        balance = float(vendor_row["Balance Due"])

        max_amt = min(balance, remaining)

        st.info(f"Maximum Allowed Amount: ₹ {max_amt}")

        amount = st.number_input("Cheque Amount", 0.0, max_amt)

        submit = st.form_submit_button("Issue Cheque")

        if submit and amount > 0:

            # ----- Update Ledger -----
            new_entry = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Vendor Name": vendor,
                "Project": project,
                "Cheque Amount": amount,
                "Status": "Issued"
            }])

            ledger = pd.concat([ledger, new_entry], ignore_index=True)
            save_sheet(ledger, "Cheque Distribution")

            # ----- Update Vendor -----
            idx = vendors[vendors["Vendor Name"] == vendor].index[0]

            vendors.loc[idx, "Total Paid"] += amount
            vendors.loc[idx, "Balance Due"] -= amount

            save_sheet(vendors, "Vendors")

            # ----- Update Budget -----
            budget.loc[0, "Total Spent"] += amount
            budget.loc[0, "Remaining Budget"] -= amount

            save_sheet(budget, "Budget")

            st.success("✅ Cheque Issued Successfully")
            st.rerun()

    st.divider()

    # ---------------- CHEQUE HISTORY (AT END) ----------------
    st.header("📜 Cheque History")

    if ledger.empty:
        st.info("No cheques issued yet")
    else:
        ledger_view = ledger.sort_values("Date", ascending=False)

        total_issued = ledger_view["Cheque Amount"].sum()

        st.metric("Total Amount Issued", f"₹ {total_issued}")

        st.dataframe(
            ledger_view,
            use_container_width=True,
            height=400
        )


if __name__ == "__main__":
    main()
