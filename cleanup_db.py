import os

# Main database jo streamlit_app.py use karega
main_db = "civic_services.db"
extra_dbs = ["db.sqlite", "sqlite.db"]

print("Starting Database Cleanup...")

for db in extra_dbs:
    if os.path.exists(db):
        os.remove(db)
        print(f"Deleted extra database file: {db}")
    else:
        print(f"Already clean (Not found): {db}")

if os.path.exists(main_db):
    print(f"Success: Main database '{main_db}' is safe and ready!")
else:
    print(f"Warning: Main database '{main_db}' is missing! Please make sure it is uploaded.")
