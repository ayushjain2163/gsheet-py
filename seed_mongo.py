import os

from pymongo import MongoClient


def get_database():
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "finance_app")
    client = MongoClient(mongo_uri)
    return client[db_name]


def main():
    db = get_database()

    db.budget.delete_many({})
    db.vendors.delete_many({})
    db.projects.delete_many({})
    db.divisions.delete_many({})
    db.districts.delete_many({})
    db.entries.delete_many({})
    db.entry_gadgets.delete_many({})

    db.budget.insert_one(
        {
            "total_allocated": 1000000.0,
            "total_spent": 0.0,
            "remaining_budget": 1000000.0,
        }
    )

    db.vendors.insert_many(
        [
            {
                "vendor_name": "ABC Pvt Ltd",
                "vendor_name_key": "abc pvt ltd",
                "vendor_code": "V001",
                "total_billed": 300000.0,
                "total_paid": 0.0,
                "balance_due": 300000.0,
            },
            {
                "vendor_name": "XYZ Infra",
                "vendor_name_key": "xyz infra",
                "vendor_code": "V002",
                "total_billed": 200000.0,
                "total_paid": 0.0,
                "balance_due": 200000.0,
            },
        ]
    )

    db.vendors.create_index("vendor_name_key", unique=True)
    db.projects.create_index("project_name_key", unique=True)
    db.divisions.create_index("division_name_key", unique=True)
    db.districts.create_index("district_name_key", unique=True)
    db.entries.create_index("entry_id", unique=True)

    print("MongoDB seeded successfully")


if __name__ == "__main__":
    main()
