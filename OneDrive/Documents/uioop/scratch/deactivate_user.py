import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def deactivate_rieshalyn():
    try:
        settings = DatabaseSettings.from_env()
        db = DatabaseManager(settings)
        db.connect()
        with db.session() as (_, cursor):
            # Find and deactivate
            cursor.execute("SELECT id, username, full_name, status FROM users WHERE full_name LIKE '%Rieshalyn%'")
            users = cursor.fetchall()
            print(f"Found users: {users}")
            
            for user in users:
                cursor.execute("UPDATE users SET status = 'inactive' WHERE id = %s", (user['id'],))
                print(f"Deactivated user: {user['username']}")
                
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    deactivate_rieshalyn()
