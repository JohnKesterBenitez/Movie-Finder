from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def check_raw():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    with db.session() as (_, cursor):
        cursor.execute("SELECT * FROM vw_active_reservations WHERE reservation_code = 'K3-P04ZD'")
        rows = cursor.fetchall()
        print(f"Rows for K3-P04ZD: {len(rows)}")
        for row in rows:
            print(row)

if __name__ == "__main__":
    check_raw()
