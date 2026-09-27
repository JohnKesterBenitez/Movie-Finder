from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings
import json

def check():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    with db.session() as (conn, cursor):
        cursor.execute("SELECT * FROM vw_active_reservations WHERE reservation_code = 'K3-P04ZD'")
        rows = cursor.fetchall()
        print(f"ROWS FOUND IN VIEW: {len(rows)}")
        for row in rows:
            print(json.dumps(row, default=str))

if __name__ == '__main__':
    check()
