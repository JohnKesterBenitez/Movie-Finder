from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def update_rates():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    updates = [
        ("Snorkeling Area", 300.00),
        ("Starfish Area", 300.00),
        ("Little Boracay", 500.00),
        ("Wave Runner", 500.00)
    ]
    with db.session() as (conn, cursor):
        for name, rate in updates:
            cursor.execute("UPDATE destinations SET base_rate = %s WHERE name = %s", (rate, name))
        conn.commit()
    print("Successfully updated destination rates in the database.")

if __name__ == "__main__":
    update_rates()
