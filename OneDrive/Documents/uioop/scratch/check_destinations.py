from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def check():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    with db.session() as (_, cursor):
        cursor.execute("SELECT * FROM destinations")
        rows = cursor.fetchall()
        for row in rows:
            print(row)

if __name__ == "__main__":
    check()
