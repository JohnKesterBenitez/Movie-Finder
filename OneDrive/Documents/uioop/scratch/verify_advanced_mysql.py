import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from k3_rms.config import DatabaseSettings
from k3_rms.database.connection import DatabaseManager
from k3_rms.database.schema import SchemaManager

def verify():
    try:
        settings = DatabaseSettings.from_env()
        db = DatabaseManager(settings)
        schema = SchemaManager(db)
        
        print("--- Initializing Schema ---")
        warnings = schema.initialize()
        for w in warnings:
            print(f"Warning: {w}")
        
        with db.session() as (conn, cursor):
            print("\n--- Verifying Views ---")
            views = ["vw_active_reservations", "vw_financial_summary", "vw_cottage_popularity"]
            for view in views:
                try:
                    cursor.execute(f"SELECT * FROM {view} LIMIT 1")
                    cursor.fetchall() # Consume results
                    print(f"OK: View '{view}' is accessible.")
                except Exception as e:
                    print(f"FAIL: View '{view}' error: {e}")

            print("\n--- Verifying Stored Procedures ---")
            procs = ["sp_cancel_reservation", "sp_process_payment"]
            for proc in procs:
                cursor.execute(f"SHOW PROCEDURE STATUS WHERE Name = '{proc}'")
                if cursor.fetchone():
                    print(f"OK: Procedure '{proc}' exists.")
                else:
                    print(f"FAIL: Procedure '{proc}' not found.")
                cursor.fetchall() # Consume any remaining results

            print("\n--- Verifying Triggers ---")
            cursor.execute("SHOW TRIGGERS LIKE 'reservations'")
            triggers = [row['Trigger'] for row in cursor.fetchall()]
            expected_triggers = ["trg_reservations_after_update", "trg_reservations_after_delete"]
            for trg in expected_triggers:
                if trg in triggers:
                    print(f"OK: Trigger '{trg}' exists.")
                else:
                    print(f"FAIL: Trigger '{trg}' not found.")

            print("\n--- Verifying Events ---")
            cursor.execute("SHOW EVENTS")
            events = [row['Name'] for row in cursor.fetchall()]
            required_events = ["evt_complete_expired_trips", "evt_expire_unapproved_bookings"]
            for evt in required_events:
                if evt in events:
                    print(f"OK: Event '{evt}' exists.")
                else:
                    print(f"FAIL: Event '{evt}' not found.")

            print("\n--- Verifying Audit Logs Table ---")
            cursor.execute("SHOW TABLES LIKE 'audit_logs'")
            if cursor.fetchone():
                print("OK: Table 'audit_logs' exists.")
                
                # Test trigger by updating a reservation if one exists
                cursor.execute("SELECT id, status FROM reservations LIMIT 1")
                res = cursor.fetchone()
                if res:
                    print(f"Testing Trigger: Updating reservation {res['id']}...")
                    old_status = res['status']
                    new_status = 'On Going' if old_status != 'On Going' else 'Reserved'
                    cursor.execute("UPDATE reservations SET status = %s WHERE id = %s", (new_status, res['id']))
                    conn.commit()
                    
                    cursor.execute("SELECT * FROM audit_logs WHERE record_id = %s ORDER BY created_at DESC LIMIT 1", (res['id'],))
                    audit = cursor.fetchone()
                    if audit:
                        print(f"SUCCESS: Trigger recorded update in audit_logs. Action: {audit['action']}")
                    else:
                        print("FAIL: Trigger did not record update in audit_logs.")
                else:
                    print("Skipping trigger test: No reservations found in database.")

    except Exception as e:
        print(f"An error occurred during verification: {e}")

if __name__ == "__main__":
    verify()
