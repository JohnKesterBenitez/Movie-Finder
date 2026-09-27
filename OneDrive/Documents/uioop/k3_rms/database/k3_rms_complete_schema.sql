-- ============================================================================
-- K3's Floating Cottage Reservation Management System (RMS)
-- Complete MySQL Database Schema
-- Location: Calatagan, Batangas
-- ============================================================================
-- PRE-REQUISITES:
-- Ensure MySQL Event Scheduler is enabled:
-- SET GLOBAL event_scheduler = ON;
-- ============================================================================

-- Drop existing database (optional - for fresh installation)
-- DROP DATABASE IF EXISTS k3_rms;

-- Create database
CREATE DATABASE IF NOT EXISTS k3_rms
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE k3_rms;

-- ============================================================================
-- TABLE 1: CUSTOMERS (Guest Information)
-- ============================================================================
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    phone_number VARCHAR(20) NOT NULL,
    address VARCHAR(255),
    barangay VARCHAR(100),
    city VARCHAR(100),
    province VARCHAR(100),
    zip_code VARCHAR(10),
    id_type ENUM('National ID', 'Passport', 'Driver License', 'TIN', 'Other') DEFAULT 'National ID',
    id_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_phone (phone_number)
);

-- ============================================================================
-- TABLE 2: COTTAGES (Asset Management)
-- ============================================================================
CREATE TABLE cottages (
    cottage_id INT PRIMARY KEY AUTO_INCREMENT,
    cottage_name VARCHAR(100) NOT NULL UNIQUE,
    capacity INT NOT NULL DEFAULT 20,
    description TEXT,
    amenities TEXT,
    rate_per_pax DECIMAL(10, 2) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLE 3: ADD-ONS (Boddle Fight & Transient Houses)
-- ============================================================================
CREATE TABLE addons (
    addon_id INT PRIMARY KEY AUTO_INCREMENT,
    addon_name VARCHAR(100) NOT NULL,
    addon_type ENUM('Boddle Fight', 'Transient House', 'Food Package', 'Activity', 'Other') NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    pax_required INT COMMENT 'Minimum pax for Boddle Fight (10 or 15)',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_addon_type (addon_type)
);

-- ============================================================================
-- TABLE 4: RESERVATIONS (Core Booking System)
-- ============================================================================
CREATE TABLE reservations (
    reservation_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    cottage_id INT NOT NULL,
    reservation_date DATE NOT NULL,
    arrival_time TIME DEFAULT '06:00:00',
    departure_time TIME DEFAULT '16:00:00',
    pax_count INT NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL COMMENT 'Total base price (rate_per_pax × pax_count)',
    reservation_status ENUM('Pending', 'Confirmed', 'Checked-In', 'Completed', 'Cancelled') DEFAULT 'Pending',
    special_requests TEXT,
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (cottage_id) REFERENCES cottages(cottage_id) ON DELETE RESTRICT,
    INDEX idx_reservation_date (reservation_date),
    INDEX idx_customer_id (customer_id),
    INDEX idx_cottage_id (cottage_id),
    INDEX idx_status (reservation_status),
    CONSTRAINT unique_reservation_slot UNIQUE (cottage_id, reservation_date)
);

-- ============================================================================
-- TABLE 5: RESERVATION ADD-ONS (Junction Table)
-- ============================================================================
CREATE TABLE reservation_addons (
    reservation_addon_id INT PRIMARY KEY AUTO_INCREMENT,
    reservation_id INT NOT NULL,
    addon_id INT NOT NULL,
    quantity INT DEFAULT 1,
    addon_price DECIMAL(10, 2) NOT NULL COMMENT 'Price at time of booking',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id) ON DELETE CASCADE,
    FOREIGN KEY (addon_id) REFERENCES addons(addon_id) ON DELETE RESTRICT,
    UNIQUE KEY unique_reservation_addon (reservation_id, addon_id)
);

-- ============================================================================
-- TABLE 6: PAYMENTS (Payment Tracking & Financial Records)
-- ============================================================================
CREATE TABLE payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    reservation_id INT NOT NULL,
    payment_type ENUM('Downpayment', 'Full Payment', 'Partial', 'Adjustment') DEFAULT 'Downpayment',
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('Cash', 'Check', 'GCash', 'PayMaya', 'Credit Card', 'Other') NOT NULL,
    payment_status ENUM('Pending', 'Completed', 'Failed', 'Refunded') DEFAULT 'Completed',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reference_number VARCHAR(100),
    notes TEXT,
    recorded_by VARCHAR(100),
    FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id) ON DELETE CASCADE,
    INDEX idx_payment_date (payment_date),
    INDEX idx_reservation_id (reservation_id),
    INDEX idx_payment_status (payment_status)
);

-- ============================================================================
-- TABLE 7: LOGS (Audit Trail)
-- ============================================================================
CREATE TABLE audit_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    action VARCHAR(255) NOT NULL,
    table_name VARCHAR(100),
    record_id INT,
    changed_by VARCHAR(100),
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_values JSON,
    new_values JSON,
    INDEX idx_timestamp (change_timestamp),
    INDEX idx_table_name (table_name)
);

-- ============================================================================
-- INSERT DEFAULT DATA
-- ============================================================================

-- Insert sample cottages
INSERT INTO cottages (cottage_name, capacity, description, rate_per_pax) VALUES
('Cottage A', 20, 'Beach-front cottage with sea view', 800.00),
('Cottage B', 20, 'Garden-view cottage near amenities', 750.00),
('Cottage C', 20, 'Premium cottage with full amenities', 900.00);

-- Insert sample add-ons
INSERT INTO addons (addon_name, addon_type, description, price, pax_required) VALUES
('Boddle Fight - 10 Pax Package', 'Boddle Fight', 'Sabong activity for 10 participants', 5000.00, 10),
('Boddle Fight - 15 Pax Package', 'Boddle Fight', 'Sabong activity for 15 participants', 7000.00, 15),
('Small Transient House', 'Transient House', 'Single room for overnight stay (1-4 pax)', 3000.00, NULL),
('Large Transient House', 'Transient House', 'Multi-room for overnight stay (5-10 pax)', 6000.00, NULL),
('BBQ Package', 'Food Package', 'Complete BBQ setup with utensils', 4000.00, NULL),
('Floating Bar', 'Activity', 'Water bar activity access', 2000.00, NULL);

-- ============================================================================
-- VIEW 1: DAILY ARRIVALS
-- ============================================================================
CREATE OR REPLACE VIEW v_DailyArrivals AS
SELECT
    r.reservation_id,
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.phone_number,
    c.email,
    co.cottage_name,
    r.reservation_date,
    r.arrival_time,
    r.departure_time,
    r.pax_count,
    r.base_price,
    r.reservation_status,
    COUNT(DISTINCT ra.addon_id) AS addon_count
FROM reservations r
INNER JOIN customers c ON r.customer_id = c.customer_id
INNER JOIN cottages co ON r.cottage_id = co.cottage_id
LEFT JOIN reservation_addons ra ON r.reservation_id = ra.reservation_id
WHERE DATE(r.reservation_date) = CURDATE()
GROUP BY r.reservation_id
ORDER BY r.arrival_time ASC;

-- ============================================================================
-- VIEW 2: FINANCIAL SUMMARY
-- ============================================================================
CREATE OR REPLACE VIEW v_FinancialSummary AS
SELECT
    r.reservation_id,
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    r.reservation_date,
    co.cottage_name,
    r.pax_count,
    r.base_price,
    COALESCE(SUM(ra.addon_price * ra.quantity), 0) AS total_addons,
    (r.base_price + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) AS total_revenue,
    COALESCE(SUM(p.amount), 0) AS total_paid,
    ((r.base_price + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) - COALESCE(SUM(p.amount), 0)) AS balance_due,
    r.reservation_status
FROM reservations r
INNER JOIN customers c ON r.customer_id = c.customer_id
INNER JOIN cottages co ON r.cottage_id = co.cottage_id
LEFT JOIN reservation_addons ra ON r.reservation_id = ra.reservation_id
LEFT JOIN payments p ON r.reservation_id = p.reservation_id AND p.payment_status = 'Completed'
GROUP BY r.reservation_id
ORDER BY r.reservation_date DESC;

-- ============================================================================
-- STORED PROCEDURE 1: BOOK RESERVATION
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_BookReservation(
    IN p_first_name VARCHAR(100),
    IN p_last_name VARCHAR(100),
    IN p_email VARCHAR(150),
    IN p_phone VARCHAR(20),
    IN p_address VARCHAR(255),
    IN p_city VARCHAR(100),
    IN p_cottage_id INT,
    IN p_reservation_date DATE,
    IN p_arrival_time TIME,
    IN p_departure_time TIME,
    IN p_pax_count INT,
    IN p_special_requests TEXT,
    OUT p_reservation_id INT,
    OUT p_success BOOLEAN,
    OUT p_message VARCHAR(255)
)
READS SQL DATA
MODIFIES SQL DATA
BEGIN
    DECLARE v_customer_id INT;
    DECLARE v_base_price DECIMAL(10, 2);
    DECLARE v_rate_per_pax DECIMAL(10, 2);
    DECLARE v_existing_reservation INT;

    -- Start validation
    SET p_success = FALSE;
    SET p_message = '';

    -- Validate pax count (max 20)
    IF p_pax_count > 20 THEN
        SET p_message = 'ERROR: Pax count exceeds maximum of 20.';
        LEAVE sp_BookReservation;
    END IF;

    IF p_pax_count <= 0 THEN
        SET p_message = 'ERROR: Pax count must be greater than 0.';
        LEAVE sp_BookReservation;
    END IF;

    -- Check if cottage exists
    IF NOT EXISTS (SELECT 1 FROM cottages WHERE cottage_id = p_cottage_id) THEN
        SET p_message = 'ERROR: Cottage does not exist.';
        LEAVE sp_BookReservation;
    END IF;

    -- Check if slot is already booked
    IF EXISTS (SELECT 1 FROM reservations 
               WHERE cottage_id = p_cottage_id 
               AND reservation_date = p_reservation_date 
               AND reservation_status IN ('Pending', 'Confirmed', 'Checked-In')) THEN
        SET p_message = 'ERROR: Cottage is already booked for this date.';
        LEAVE sp_BookReservation;
    END IF;

    -- Check if reservation date is in the future
    IF p_reservation_date < CURDATE() THEN
        SET p_message = 'ERROR: Reservation date cannot be in the past.';
        LEAVE sp_BookReservation;
    END IF;

    -- Get or create customer
    SELECT customer_id INTO v_customer_id
    FROM customers
    WHERE phone_number = p_phone
    LIMIT 1;

    IF v_customer_id IS NULL THEN
        INSERT INTO customers (first_name, last_name, email, phone_number, address, city)
        VALUES (p_first_name, p_last_name, p_email, p_phone, p_address, p_city);
        SET v_customer_id = LAST_INSERT_ID();
    ELSE
        -- Update customer info if changed
        UPDATE customers
        SET first_name = p_first_name,
            last_name = p_last_name,
            email = COALESCE(p_email, email),
            address = COALESCE(p_address, address),
            city = COALESCE(p_city, city)
        WHERE customer_id = v_customer_id;
    END IF;

    -- Get rate per pax from cottage
    SELECT rate_per_pax INTO v_rate_per_pax
    FROM cottages
    WHERE cottage_id = p_cottage_id;

    -- Calculate base price
    SET v_base_price = v_rate_per_pax * p_pax_count;

    -- Create reservation
    INSERT INTO reservations (
        customer_id, cottage_id, reservation_date, arrival_time, 
        departure_time, pax_count, base_price, special_requests
    ) VALUES (
        v_customer_id, p_cottage_id, p_reservation_date, 
        COALESCE(p_arrival_time, '06:00:00'),
        COALESCE(p_departure_time, '16:00:00'),
        p_pax_count, v_base_price, p_special_requests
    );

    SET p_reservation_id = LAST_INSERT_ID();
    SET p_success = TRUE;
    SET p_message = 'Reservation created successfully.';

END$$

DELIMITER ;

-- ============================================================================
-- STORED PROCEDURE 2: PROCESS PAYMENT
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_ProcessPayment(
    IN p_reservation_id INT,
    IN p_payment_type VARCHAR(50),
    IN p_amount DECIMAL(10, 2),
    IN p_payment_method VARCHAR(50),
    IN p_reference_number VARCHAR(100),
    IN p_recorded_by VARCHAR(100),
    OUT p_success BOOLEAN,
    OUT p_message VARCHAR(255),
    OUT p_remaining_balance DECIMAL(10, 2)
)
READS SQL DATA
MODIFIES SQL DATA
BEGIN
    DECLARE v_total_revenue DECIMAL(10, 2);
    DECLARE v_total_paid DECIMAL(10, 2);
    DECLARE v_reservation_status VARCHAR(50);

    SET p_success = FALSE;
    SET p_message = '';

    -- Check if reservation exists
    IF NOT EXISTS (SELECT 1 FROM reservations WHERE reservation_id = p_reservation_id) THEN
        SET p_message = 'ERROR: Reservation does not exist.';
        LEAVE sp_ProcessPayment;
    END IF;

    -- Get total revenue (base + addons)
    SELECT (r.base_price + COALESCE(SUM(ra.addon_price * ra.quantity), 0))
    INTO v_total_revenue
    FROM reservations r
    LEFT JOIN reservation_addons ra ON r.reservation_id = ra.reservation_id
    WHERE r.reservation_id = p_reservation_id
    GROUP BY r.reservation_id;

    -- Validate payment amount
    IF p_amount <= 0 THEN
        SET p_message = 'ERROR: Payment amount must be greater than 0.';
        LEAVE sp_ProcessPayment;
    END IF;

    -- Insert payment record
    INSERT INTO payments (
        reservation_id, payment_type, amount, payment_method,
        reference_number, recorded_by
    ) VALUES (
        p_reservation_id, p_payment_type, p_amount,
        p_payment_method, p_reference_number, p_recorded_by
    );

    -- Get total paid so far
    SELECT COALESCE(SUM(amount), 0)
    INTO v_total_paid
    FROM payments
    WHERE reservation_id = p_reservation_id
    AND payment_status = 'Completed';

    -- Calculate remaining balance
    SET p_remaining_balance = v_total_revenue - v_total_paid;

    -- Update reservation status to Confirmed if downpayment is recorded
    IF p_payment_type = 'Downpayment' THEN
        UPDATE reservations
        SET reservation_status = 'Confirmed'
        WHERE reservation_id = p_reservation_id;
    END IF;

    SET p_success = TRUE;
    SET p_message = CONCAT('Payment processed successfully. Balance: ', FORMAT(p_remaining_balance, 2));

END$$

DELIMITER ;

-- ============================================================================
-- TRIGGER 1: PAX GUARD (Prevent bookings > 20 pax)
-- ============================================================================
DELIMITER $$

CREATE TRIGGER trg_PaxGuard
BEFORE INSERT ON reservations
FOR EACH ROW
BEGIN
    IF NEW.pax_count > 20 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Pax count cannot exceed 20 for a single reservation.';
    END IF;

    IF NEW.pax_count <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Pax count must be greater than 0.';
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- TRIGGER 2: UPDATE STATUS - AUTO CONFIRM ON DOWNPAYMENT
-- ============================================================================
DELIMITER $$

CREATE TRIGGER trg_UpdateStatus
AFTER INSERT ON payments
FOR EACH ROW
BEGIN
    DECLARE v_downpay_count INT;

    -- Check if this is a downpayment
    IF NEW.payment_type = 'Downpayment' AND NEW.payment_status = 'Completed' THEN
        -- Update reservation status to Confirmed
        UPDATE reservations
        SET reservation_status = 'Confirmed'
        WHERE reservation_id = NEW.reservation_id;

        -- Log the action
        INSERT INTO audit_logs (action, table_name, record_id, changed_by)
        VALUES ('Downpayment received - Reservation Confirmed', 'reservations', NEW.reservation_id, 'SYSTEM');
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- STORED PROCEDURE 3: GET MONTHLY REPORT
-- ============================================================================
DELIMITER $$

CREATE PROCEDURE sp_GenerateMonthlyReport(
    IN p_year INT,
    IN p_month INT
)
READS SQL DATA
BEGIN
    SELECT
        DATE_FORMAT(r.reservation_date, '%Y-%m') AS month,
        COUNT(DISTINCT r.reservation_id) AS total_bookings,
        SUM(r.pax_count) AS total_pax_hosted,
        COUNT(DISTINCT r.cottage_id) AS cottages_used,
        SUM(r.base_price) AS base_revenue,
        COALESCE(SUM(ra.addon_price * ra.quantity), 0) AS addon_revenue,
        (SUM(r.base_price) + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) AS total_revenue,
        COALESCE(SUM(p.amount), 0) AS total_collected,
        ((SUM(r.base_price) + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) - COALESCE(SUM(p.amount), 0)) AS outstanding_balance
    FROM reservations r
    LEFT JOIN reservation_addons ra ON r.reservation_id = ra.reservation_id
    LEFT JOIN payments p ON r.reservation_id = p.reservation_id AND p.payment_status = 'Completed'
    WHERE YEAR(r.reservation_date) = p_year
    AND MONTH(r.reservation_date) = p_month
    GROUP BY DATE_FORMAT(r.reservation_date, '%Y-%m');
END$$

DELIMITER ;

-- ============================================================================
-- SCHEDULED EVENT: DAILY CLEANUP (Update completed reservations at 4:05 PM)
-- ============================================================================
DELIMITER $$

CREATE EVENT evt_DailyCleanup
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    UPDATE reservations
    SET reservation_status = 'Completed'
    WHERE DATE(reservation_date) = CURDATE()
    AND reservation_status = 'Confirmed'
    AND departure_time <= CURTIME();

    -- Log the cleanup action
    INSERT INTO audit_logs (action, table_name, changed_by)
    VALUES ('Daily cleanup event executed', 'reservations', 'EVENT_SCHEDULER');
END$$

DELIMITER ;

-- ============================================================================
-- HELPER VIEWS & FUNCTIONS
-- ============================================================================

-- View: Availability Calendar
CREATE OR REPLACE VIEW v_CottageAvailability AS
SELECT
    c.cottage_id,
    c.cottage_name,
    DATE_ADD(CURDATE(), INTERVAL 1 DAY) AS available_date,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM reservations r
            WHERE r.cottage_id = c.cottage_id
            AND r.reservation_date = DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            AND r.reservation_status NOT IN ('Cancelled')
        ) THEN 'Booked'
        ELSE 'Available'
    END AS status
FROM cottages c
ORDER BY c.cottage_id;

-- View: Outstanding Payments
CREATE OR REPLACE VIEW v_OutstandingPayments AS
SELECT
    r.reservation_id,
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    r.reservation_date,
    co.cottage_name,
    (r.base_price + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) AS total_amount,
    COALESCE(SUM(p.amount), 0) AS amount_paid,
    ((r.base_price + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) - COALESCE(SUM(p.amount), 0)) AS balance_due,
    DATEDIFF(CURDATE(), r.booking_date) AS days_since_booking
FROM reservations r
INNER JOIN customers c ON r.customer_id = c.customer_id
INNER JOIN cottages co ON r.cottage_id = co.cottage_id
LEFT JOIN reservation_addons ra ON r.reservation_id = ra.reservation_id
LEFT JOIN payments p ON r.reservation_id = p.reservation_id AND p.payment_status = 'Completed'
WHERE ((r.base_price + COALESCE(SUM(ra.addon_price * ra.quantity), 0)) - COALESCE(SUM(p.amount), 0)) > 0
AND r.reservation_status NOT IN ('Cancelled')
GROUP BY r.reservation_id
ORDER BY balance_due DESC;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX idx_reservations_date_status ON reservations(reservation_date, reservation_status);
CREATE INDEX idx_reservations_customer ON reservations(customer_id);
CREATE INDEX idx_payments_reservation ON payments(reservation_id);
CREATE INDEX idx_payments_status ON payments(payment_status);
CREATE INDEX idx_addons_type ON addons(addon_type);

-- ============================================================================
-- FINAL NOTE: ENABLE EVENT SCHEDULER
-- ============================================================================
-- After running this script, execute the following command to enable events:
-- SET GLOBAL event_scheduler = ON;
--
-- To verify event scheduler status:
-- SHOW VARIABLES LIKE 'event_scheduler';
-- ============================================================================

-- Sample query to test the system
SELECT '=== K3 FLOATING COTTAGE RMS DATABASE SETUP COMPLETE ===' AS status;
