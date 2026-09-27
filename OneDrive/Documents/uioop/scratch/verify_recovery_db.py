import mysql.connector
from k3_rms.config import DatabaseSettings
from k3_rms.database.connection import DatabaseManager
from k3_rms.database.schema import SchemaManager
import dataclasses

def verify():
    try:
        settings = DatabaseSettings.from_env()
        db_manager = DatabaseManager(settings)
        schema_manager = SchemaManager(db_manager)
        
        # This will trigger the migrations
        print("Initializing schema...")
        schema_manager.initialize()
        
        config = dataclasses.asdict(settings)
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        for table in ['users', 'admin_users']:
            cursor.execute(f"DESCRIBE {table}")
            columns = [row[0] for row in cursor.fetchall()]
            print(f"Columns in {table}: {columns}")
            if 'recovery_question' in columns and 'recovery_answer' in columns:
                print(f"OK: {table} has recovery columns.")
            else:
                print(f"FAIL: {table} is missing recovery columns.")
                
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()
