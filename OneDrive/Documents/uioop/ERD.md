# K3 Floating Cottage ERD

This ERD reflects the current runtime schema defined in `k3_rms/database/schema.py`. The older `k3_floating_cottage.sql` file still shows legacy `motorboats`, but the active schema uses `destinations`.

```mermaid
erDiagram
    USERS {
        int id PK
        varchar username UK
        varchar password
        enum password_scheme
        varchar full_name
        varchar contact_number UK
        varchar email UK
        enum status
        varchar recovery_question
        varchar recovery_answer
        timestamp created_at
        timestamp updated_at
    }

    ADMIN_USERS {
        int id PK
        varchar username UK
        varchar password
        varchar full_name
        varchar contact_number
        varchar email
        enum role
        varchar recovery_question
        varchar recovery_answer
        timestamp created_at
        timestamp updated_at
    }

    CUSTOMERS {
        int id PK
        int user_id FK UK
        varchar full_name
        varchar contact_number UK
        varchar email UK
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    COTTAGES {
        int id PK
        varchar asset_code UK
        varchar name
        int capacity
        decimal base_rate
        timestamp created_at
    }

    DESTINATIONS {
        int id PK
        varchar asset_code UK
        varchar name UK
        int capacity
        decimal base_rate
        timestamp created_at
    }

    RESERVATIONS {
        int id PK
        varchar reservation_code UK
        int user_id FK
        int customer_id FK
        int cottage_id FK
        int destination_id FK
        varchar destination
        int party_size
        datetime departure_time
        datetime return_time
        decimal total_price
        enum status
        varchar payment_status
        decimal amount_paid
        varchar payment_method
        datetime paid_at
        text payment_notes
        text notes
        datetime completed_at
        datetime cancelled_at
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    RESERVATION_DESTINATIONS {
        int id PK
        int reservation_id FK
        int destination_id FK
        int sort_order
        boolean is_primary
        timestamp created_at
    }

    PAYMENTS {
        int id PK
        int reservation_id FK
        varchar transaction_type
        varchar payment_status
        decimal payment_amount
        decimal total_amount_paid
        decimal balance_due
        varchar payment_method
        text payment_notes
        varchar recorded_by
        datetime recorded_at
        timestamp created_at
    }

    PAYMENT_LOGS {
        int id PK
        int reservation_id FK
        int payment_id FK
        varchar action
        varchar old_payment_status
        varchar new_payment_status
        decimal old_amount_paid
        decimal new_amount_paid
        varchar payment_method
        text notes
        varchar recorded_by
        timestamp created_at
    }

    AUDIT_LOGS {
        int id PK
        varchar table_name
        int record_id
        enum action
        json old_values
        json new_values
        varchar changed_by
        timestamp created_at
    }

    TRASH_BIN {
        int id PK
        varchar record_type
        int record_id
        varchar record_ref
        json original_data
        timestamp deleted_at
    }

    USERS o|--o| CUSTOMERS : "profile link"
    USERS o|--o{ RESERVATIONS : "places"
    CUSTOMERS ||--o{ RESERVATIONS : "owns"
    COTTAGES ||--o{ RESERVATIONS : "assigned cottage"
    DESTINATIONS ||--o{ RESERVATIONS : "assigned destination"
    RESERVATIONS ||--o{ RESERVATION_DESTINATIONS : "route stops"
    DESTINATIONS ||--o{ RESERVATION_DESTINATIONS : "selected stops"
    RESERVATIONS ||--o{ PAYMENTS : "has payments"
    RESERVATIONS ||--o{ PAYMENT_LOGS : "has payment history"
    PAYMENTS o|--o{ PAYMENT_LOGS : "logged payment"
    RESERVATIONS o|--o{ AUDIT_LOGS : "logical audit trail"
    CUSTOMERS o|--o{ TRASH_BIN : "logical delete archive"
    RESERVATIONS o|--o{ TRASH_BIN : "logical delete archive"
```

## Current Tables

The current runtime schema contains these 11 tables:

1. `admin_users`
2. `users`
3. `customers`
4. `cottages`
5. `destinations`
6. `reservations`
7. `reservation_destinations`
8. `payments`
9. `payment_logs`
10. `audit_logs`
11. `trash_bin`

## Notes

- `customers.user_id` is optional but unique, so guest records can exist without a linked app account.
- `reservations.user_id` is optional, while `reservations.customer_id`, `cottage_id`, and `destination_id` are part of the finalized active schema.
- Multi-stop bookings are normalized through `reservation_destinations`, while `reservations.destination` is retained as a compatibility summary during the migration.
- Payment state is normalized through `payments`, while `reservations.payment_status`, `amount_paid`, `payment_method`, `paid_at`, and `payment_notes` are retained as compatibility snapshots.
- Linked account profile reads now prefer `customers` data, while duplicate `users` profile columns are still mirrored for compatibility during the migration.
- `audit_logs` and `trash_bin` are included as full tables, but their links are logical and not enforced with foreign keys.
- `audit_logs` currently records reservation changes through database triggers.
- `trash_bin` currently stores soft-deleted snapshots for `customers` and `reservations`.
- Derived views built from the base tables are `vw_active_reservations`, `vw_financial_summary`, and `vw_cottage_popularity`.
