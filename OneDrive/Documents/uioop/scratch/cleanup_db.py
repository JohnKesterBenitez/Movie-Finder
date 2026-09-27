from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def cleanup():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    with db.session() as (conn, cursor):
        # 1. Update reservations that point to invalid destinations
        # We'll point them to SandBar Area (usually ID 1)
        cursor.execute("SELECT id FROM destinations WHERE name = 'SandBar Area' LIMIT 1")
        sandbar = cursor.fetchone()
        sandbar_id = sandbar['id'] if sandbar else 1
        
        cursor.execute("""
            UPDATE reservations 
            SET destination_id = %s 
            WHERE destination_id IN (SELECT id FROM destinations WHERE name LIKE '%%,%%')
        """, (sandbar_id,))
        
        # 2. Delete the invalid destinations
        cursor.execute("DELETE FROM destinations WHERE name LIKE '%%,%%'")
        
        conn.commit()
    print("Cleanup complete. Invalid destinations removed.")

if __name__ == "__main__":
    cleanup()
