# K3's Floating Cottage Reservation Management System

This project is a Python Reservation Management System for K3's Floating Cottage. It follows the MVC pattern and uses MySQL for reservation, asset, and dashboard data.

## Highlights

- MVC project layout with separated models, controllers, and views
- CustomTkinter desktop interface styled like a small website with top navigation
- MySQL connection pooling with environment-based credentials
- Advanced MySQL objects: `INNER JOIN`, `LEFT JOIN`, dashboard view, scalar functions, and stored availability function
- Real-time cottage and motorboat availability validation
- Automatic asset status updates: `Available`, `Reserved`, and `On Going`
- Streamlined reservation flow with known-customer autofill
- Transaction dashboard for active, completed, cancelled, daily, and weekly bookings
- Demo mode fallback so the UI still works even when MySQL is not configured yet

## Setup

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set the MySQL environment variables or create a local `.env` file:

   ```powershell
   $env:K3_DB_HOST="localhost"
   $env:K3_DB_PORT="3306"
   $env:K3_DB_USER="root"
   $env:K3_DB_PASSWORD="your-password"
   $env:K3_DB_NAME="k3_floating_cottage"
   ```

   You can also copy `.env.example` to `.env` and place the same values there.

3. Run the desktop app:

   ```bash
   python main.py
   ```

If `K3_DB_PASSWORD` is not already configured, the app will prompt for the MySQL password when started in a normal terminal. The GUI uses `customtkinter` and loads `inspo_preview.png` or `inspo.avif` for the hero section.

If MySQL is unavailable, the app opens in demo mode with working sample data so you can still test navigation, booking, and trip actions.
