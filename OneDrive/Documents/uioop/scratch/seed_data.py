import sys
import os
import random
from datetime import datetime, timedelta, date
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings, DEFAULT_COTTAGES, DEFAULT_DESTINATION_ASSETS

def populate_database():
    try:
        settings = DatabaseSettings.from_env()
        db = DatabaseManager(settings)
        db.connect()
        
        with db.session() as (_, cursor):
            # 1. Get Assets
            cursor.execute("SELECT id, name, base_rate FROM cottages")
            cottages = cursor.fetchall()
            cursor.execute("SELECT id, name, base_rate FROM destinations")
            destinations = cursor.fetchall()
            
            if not cottages or not destinations:
                print("Error: No assets found in database. Run the app once to initialize schema.")
                return

            # 2. Create Customers
            customer_data = [
                ("Juan Dela Cruz", "09123456789", "juan@example.com"),
                ("Maria Clara", "09987654321", "maria@example.com"),
                ("Jose Rizal", "09182736451", "jose@example.com"),
                ("Andres Bonifacio", "09112233445", "andres@example.com"),
                ("Melchora Aquino", "09223344556", "melchora@example.com"),
                ("Emilio Aguinaldo", "09334455667", "emilio@example.com"),
                ("Gabriela Silang", "09445566778", "gabriela@example.com"),
                ("Antonio Luna", "09556677889", "antonio@example.com"),
                ("Apolinario Mabini", "09667788990", "apolinario@example.com"),
                ("Marcelo H. Del Pilar", "09778899001", "marcelo@example.com"),
            ]
            
            customer_ids = []
            for name, phone, email in customer_data:
                cursor.execute(
                    "INSERT INTO customers (full_name, contact_number, email) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
                    (name, phone, email)
                )
                customer_ids.append(cursor.lastrowid)

            # 3. Create Reservations
            now = datetime.now()
            
            # Past Reservations (Completed/Cancelled)
            for i in range(15):
                days_ago = random.randint(5, 60)
                departure = now - timedelta(days=days_ago)
                departure = departure.replace(hour=8, minute=0, second=0, microsecond=0)
                return_time = departure.replace(hour=16, minute=0)
                
                status = "Completed" if random.random() > 0.2 else "Cancelled"
                cust_id = random.choice(customer_ids)
                cottage = random.choice(cottages)
                dest = random.choice(destinations)
                
                res_code = f"RES-PAST-{i:03d}"
                total_price = float(cottage["base_rate"]) + float(dest["base_rate"])
                
                paid = total_price if status == "Completed" else 0.0
                pay_status = "Paid" if status == "Completed" else "Unpaid"
                
                cursor.execute(
                    """
                    INSERT INTO reservations 
                    (reservation_code, customer_id, cottage_id, destination_id, party_size, 
                     departure_time, return_time, total_price, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (res_code, cust_id, cottage["id"], dest["id"], random.randint(5, 20),
                     departure, return_time, total_price, status, departure - timedelta(days=5))
                )
                res_id = cursor.lastrowid
                
                # Payment record
                if paid > 0:
                    cursor.execute(
                        "INSERT INTO payments (reservation_id, transaction_type, payment_status, payment_amount, payment_method, recorded_by) VALUES (%s, %s, %s, %s, %s, %s)",
                        (res_id, "Payment", "Paid", paid, "GCash", "System Seed")
                    )

            # Present/Future Reservations (Reserved/Pending/On Going)
            for i in range(20):
                days_ahead = random.randint(-1, 90) # Some might be active today
                departure = now + timedelta(days=days_ahead)
                departure = departure.replace(hour=8, minute=0, second=0, microsecond=0)
                return_time = departure.replace(hour=16, minute=0)
                
                if days_ahead < 0:
                    status = "On Going"
                else:
                    status = "Reserved" if random.random() > 0.3 else "Pending"
                
                cust_id = random.choice(customer_ids)
                cottage = random.choice(cottages)
                dest = random.choice(destinations)
                
                res_code = f"RES-FUT-{i:03d}"
                total_price = float(cottage["base_rate"]) + float(dest["base_rate"])
                
                # Payment logic: some paid, some partial, some unpaid
                rand_val = random.random()
                if rand_val > 0.6:
                    paid = total_price
                    pay_status = "Paid"
                elif rand_val > 0.3:
                    paid = total_price / 2
                    pay_status = "Partially Paid"
                else:
                    paid = 0.0
                    pay_status = "Unpaid"

                cursor.execute(
                    """
                    INSERT INTO reservations 
                    (reservation_code, customer_id, cottage_id, destination_id, party_size, 
                     departure_time, return_time, total_price, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (res_code, cust_id, cottage["id"], dest["id"], random.randint(5, 20),
                     departure, return_time, total_price, status, now - timedelta(days=2))
                )
                res_id = cursor.lastrowid
                
                if paid > 0:
                    cursor.execute(
                        "INSERT INTO payments (reservation_id, transaction_type, payment_status, payment_amount, payment_method, recorded_by) VALUES (%s, %s, %s, %s, %s, %s)",
                        (res_id, "Payment", pay_status, paid, "Other", "System Seed")
                    )

            print("Database successfully populated with varied reservation and payment records.")
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    populate_database()
