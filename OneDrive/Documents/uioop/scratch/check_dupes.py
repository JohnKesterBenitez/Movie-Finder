from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def check():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    with db.session() as (conn, cursor):
        cursor.execute("SELECT name, COUNT(*) FROM destinations GROUP BY name HAVING COUNT(*) > 1")
        dupes = cursor.fetchall()
        print(f"DUPLICATE DESTINATION NAMES: {dupes}")
        
        cursor.execute("SELECT reservation_code, COUNT(*) FROM reservations GROUP BY reservation_code HAVING COUNT(*) > 1")
        res_dupes = cursor.fetchall()
        print(f"DUPLICATE RESERVATION CODES: {res_dupes}")

if __name__ == '__main__':
    check()
