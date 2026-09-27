import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def verify():
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    db.connect()
    
    with db.session() as (_, cursor):
        print("--- Verifying Reservations Table ---")
        cursor.execute("DESCRIBE reservations")
        columns = [row['Field'] for row in cursor.fetchall()]
        redundant = ["destination", "payment_status", "amount_paid", "payment_method", "paid_at", "payment_notes"]
        for col in redundant:
            if col in columns:
                print(f"FAILED: Column '{col}' still exists in reservations.")
            else:
                print(f"PASSED: Column '{col}' removed from reservations.")
        
        print("\n--- Verifying Payments Table ---")
        cursor.execute("DESCRIBE payments")
        columns = [row['Field'] for row in cursor.fetchall()]
        redundant = ["total_amount_paid", "balance_due"]
        for col in redundant:
            if col in columns:
                print(f"FAILED: Column '{col}' still exists in payments.")
            else:
                print(f"PASSED: Column '{col}' removed from payments.")
                
        print("\n--- Verifying Data Integrity ---")
        cursor.execute("SELECT COUNT(*) as count FROM reservations")
        print(f"Total Reservations: {cursor.fetchone()['count']}")
        
        cursor.execute("SELECT COUNT(*) as count FROM payments")
        print(f"Total Payments: {cursor.fetchone()['count']}")
        
        cursor.execute("""
            SELECT r.reservation_code, SUM(p.payment_amount) as total_paid
            FROM reservations r
            JOIN payments p ON p.reservation_id = r.id
            GROUP BY r.id
            LIMIT 5
        """)
        print("\nSample Calculated Payments:")
        for row in cursor.fetchall():
            print(f"Code: {row['reservation_code']}, Total Paid: {row['total_paid']}")

    db.close()

if __name__ == "__main__":
    verify()
