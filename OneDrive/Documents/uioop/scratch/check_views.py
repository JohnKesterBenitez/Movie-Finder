import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def check_view():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    db.connect()
    
    with db.session() as (_, cursor):
        print("--- Checking vw_active_reservations ---")
        try:
            cursor.execute("SHOW CREATE VIEW vw_active_reservations")
            row = cursor.fetchone()
            print(row['Create View'])
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- Checking vw_financial_summary ---")
        try:
            cursor.execute("SHOW CREATE VIEW vw_financial_summary")
            row = cursor.fetchone()
            print(row['Create View'])
        except Exception as e:
            print(f"Error: {e}")

    db.close()

if __name__ == "__main__":
    check_view()
