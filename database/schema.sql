-- =============================================================================
-- VoiceRoute - database/schema.sql
-- MySQL 8.0+ / InnoDB.  Safe to re-run: every statement is CREATE ... IF NOT EXISTS
-- and nothing here deletes or overwrites existing data.
-- All sample transport data (operators, buses, fares, schedules) is DEMONSTRATION
-- DATA ONLY. It is not live operator data.
-- =============================================================================

SET NAMES utf8mb4;

-- 1. users ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  full_name      VARCHAR(100) NOT NULL,
  phone_number   VARCHAR(20)  NOT NULL,
  password_hash  VARCHAR(255) NOT NULL,
  role           ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  created_at     DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_phone (phone_number),
  KEY idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. districts (exactly 30 rows are seeded) ----------------------------------
CREATE TABLE IF NOT EXISTS districts (
  id             SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  district_name  VARCHAR(60) NOT NULL,
  slug           VARCHAR(60) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_districts_name (district_name),
  UNIQUE KEY uq_districts_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. stations (one sample terminal per district) -----------------------------
CREATE TABLE IF NOT EXISTS stations (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  station_name   VARCHAR(120) NOT NULL,
  district_id    SMALLINT UNSIGNED NOT NULL,
  address        VARCHAR(200) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_station_name_district (district_id, station_name),
  CONSTRAINT fk_stations_district FOREIGN KEY (district_id)
    REFERENCES districts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. transport_operators (fictional demonstration companies) -----------------
CREATE TABLE IF NOT EXISTS transport_operators (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  operator_name    VARCHAR(100) NOT NULL,
  contact_phone    VARCHAR(30) NULL,
  contact_email    VARCHAR(120) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_operator_name (operator_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. buses -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS buses (
  id                   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  operator_id          INT UNSIGNED NOT NULL,
  bus_name             VARCHAR(100) NOT NULL,
  bus_type             ENUM('AC','NON_AC') NOT NULL,
  registration_number  VARCHAR(30) NOT NULL,
  total_seats          TINYINT UNSIGNED NOT NULL,
  is_active            TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_buses_registration (registration_number),
  KEY idx_buses_operator (operator_id),
  CONSTRAINT fk_buses_operator FOREIGN KEY (operator_id)
    REFERENCES transport_operators (id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_buses_seats CHECK (total_seats BETWEEN 8 AND 60)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. routes (directed: A->B and B->A are different rows) ---------------------
CREATE TABLE IF NOT EXISTS routes (
  id                         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_station_id          INT UNSIGNED NOT NULL,
  destination_station_id     INT UNSIGNED NOT NULL,
  distance_km                SMALLINT UNSIGNED NULL,
  estimated_duration_minutes SMALLINT UNSIGNED NULL,
  description                VARCHAR(200) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_routes_pair (source_station_id, destination_station_id),
  KEY idx_routes_destination (destination_station_id, source_station_id),
  -- NOTE: no ON UPDATE CASCADE here: MySQL forbids referential actions on columns
  -- that also appear in a CHECK constraint (chk_routes_distinct below).
  CONSTRAINT fk_routes_source FOREIGN KEY (source_station_id)
    REFERENCES stations (id) ON DELETE RESTRICT,
  CONSTRAINT fk_routes_destination FOREIGN KEY (destination_station_id)
    REFERENCES stations (id) ON DELETE RESTRICT,
  CONSTRAINT chk_routes_distinct CHECK (source_station_id <> destination_station_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. schedules (one departure of one bus on one route on one date) -----------
-- total_seats is a deliberate snapshot of buses.total_seats (so later edits to a bus
-- never alter past/future schedules). available_seats is a trigger-maintained counter.
CREATE TABLE IF NOT EXISTS schedules (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  bus_id           INT UNSIGNED NOT NULL,
  route_id         INT UNSIGNED NOT NULL,
  departure_date   DATE NOT NULL,
  departure_time   TIME NOT NULL,
  arrival_time     TIME NOT NULL,
  fare             DECIMAL(10,2) NOT NULL,
  total_seats      TINYINT UNSIGNED NOT NULL,
  available_seats  TINYINT UNSIGNED NOT NULL,
  status           ENUM('ACTIVE','CANCELLED','COMPLETED') NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (id),
  UNIQUE KEY uq_schedule_departure (bus_id, route_id, departure_date, departure_time),
  KEY idx_schedule_search (route_id, departure_date, status, departure_time),
  KEY idx_schedule_bus (bus_id),
  KEY idx_schedule_date (departure_date),
  CONSTRAINT fk_schedules_bus FOREIGN KEY (bus_id)
    REFERENCES buses (id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_schedules_route FOREIGN KEY (route_id)
    REFERENCES routes (id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_schedules_fare CHECK (fare >= 0),
  CONSTRAINT chk_schedules_seats CHECK (available_seats <= total_seats)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. bookings ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  booking_reference  VARCHAR(20) NOT NULL,
  user_id            INT UNSIGNED NOT NULL,
  schedule_id        INT UNSIGNED NOT NULL,
  seat_count         TINYINT UNSIGNED NOT NULL,
  total_fare         DECIMAL(10,2) NOT NULL,
  booking_status     ENUM('CONFIRMED','CANCELLED','COMPLETED') NOT NULL DEFAULT 'CONFIRMED',
  booked_at          DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  cancelled_at       DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_bookings_reference (booking_reference),
  UNIQUE KEY uq_bookings_id_schedule (id, schedule_id),
  KEY idx_bookings_user (user_id, booked_at),
  KEY idx_bookings_schedule (schedule_id, booking_status),
  KEY idx_bookings_status (booking_status),
  CONSTRAINT fk_bookings_user FOREIGN KEY (user_id)
    REFERENCES users (id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_bookings_schedule FOREIGN KEY (schedule_id)
    REFERENCES schedules (id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_bookings_count CHECK (seat_count > 0),
  CONSTRAINT chk_bookings_fare CHECK (total_fare >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. booking_seats -----------------------------------------------------------
-- active_seat is NULL for cancelled seats and equals seat_number for booked ones.
-- UNIQUE(schedule_id, active_seat) therefore makes double-booking of a seat
-- impossible at the database level, while cancelled seats can be booked again.
-- The composite FK (booking_id, schedule_id) guarantees the stored schedule_id
-- always matches the parent booking's schedule.
CREATE TABLE IF NOT EXISTS booking_seats (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  booking_id    INT UNSIGNED NOT NULL,
  schedule_id   INT UNSIGNED NOT NULL,
  seat_number   TINYINT UNSIGNED NOT NULL,
  seat_status   ENUM('BOOKED','CANCELLED') NOT NULL DEFAULT 'BOOKED',
  active_seat   TINYINT UNSIGNED GENERATED ALWAYS AS
                  (CASE WHEN seat_status = 'BOOKED' THEN seat_number ELSE NULL END) STORED,
  PRIMARY KEY (id),
  UNIQUE KEY uq_booking_seat (booking_id, seat_number),
  UNIQUE KEY uq_schedule_active_seat (schedule_id, active_seat),
  KEY idx_booking_seats_schedule (schedule_id, seat_status),
  CONSTRAINT fk_bseats_booking FOREIGN KEY (booking_id, schedule_id)
    REFERENCES bookings (id, schedule_id) ON DELETE CASCADE,
  CONSTRAINT chk_bseats_number CHECK (seat_number >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. audit_logs -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  booking_id   INT UNSIGNED NULL,
  user_id      INT UNSIGNED NULL,
  action       VARCHAR(40) NOT NULL,
  details      VARCHAR(500) NULL,
  created_at   DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  PRIMARY KEY (id),
  KEY idx_audit_booking (booking_id),
  KEY idx_audit_user (user_id),
  KEY idx_audit_created (created_at),
  CONSTRAINT fk_audit_booking FOREIGN KEY (booking_id)
    REFERENCES bookings (id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id)
    REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. low_seat_alerts --------------------------------------------------------
CREATE TABLE IF NOT EXISTS low_seat_alerts (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  schedule_id      INT UNSIGNED NOT NULL,
  available_seats  TINYINT UNSIGNED NOT NULL,
  threshold        TINYINT UNSIGNED NOT NULL,
  alert_message    VARCHAR(255) NOT NULL,
  created_at       DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
  resolved_at      DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_alerts_schedule (schedule_id, resolved_at),
  CONSTRAINT fk_alerts_schedule FOREIGN KEY (schedule_id)
    REFERENCES schedules (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. app_settings (extra table: configurable low-seat threshold) ------------
CREATE TABLE IF NOT EXISTS app_settings (
  setting_key    VARCHAR(50)  NOT NULL,
  setting_value  VARCHAR(100) NOT NULL,
  PRIMARY KEY (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO app_settings (setting_key, setting_value) VALUES ('low_seat_threshold', '5');
