-- =============================================================================
-- VoiceRoute - database/triggers.sql
-- Real MySQL 8 triggers (NOT simulated in Python).
-- Re-runnable: each trigger is DROPped IF EXISTS and re-created. No table data is touched.
-- The file uses the mysql-client DELIMITER command; the project's Python initializer
-- (backend/app/database/sqlsplit.py) understands it too.
--
-- Trigger chain
--   INSERT booking  -> trg_bookings_before_insert  (must start CONFIRMED)
--                   -> trg_bookings_after_insert   (seats--, audit log)
--                          -> trg_schedules_after_update (low-seat alert open/refresh/resolve)
--   UPDATE booking  -> trg_bookings_before_update  (status is final once left CONFIRMED,
--                                                   immutable columns)
--                   -> trg_bookings_after_update   (CONFIRMED->CANCELLED: seats++ once,
--                                                   release seat rows, audit log)
--   INSERT booking_seats -> trg_booking_seats_before_insert (seat must exist on the bus)
-- =============================================================================

DROP TRIGGER IF EXISTS trg_bookings_before_insert;
DROP TRIGGER IF EXISTS trg_bookings_after_insert;
DROP TRIGGER IF EXISTS trg_bookings_before_update;
DROP TRIGGER IF EXISTS trg_bookings_after_update;
DROP TRIGGER IF EXISTS trg_schedules_after_update;
DROP TRIGGER IF EXISTS trg_booking_seats_before_insert;

DELIMITER $$

-- A booking can only be created as CONFIRMED (so "never confirmed" bookings cannot exist).
CREATE TRIGGER trg_bookings_before_insert
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
  IF NEW.booking_status <> 'CONFIRMED' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'New bookings must have status CONFIRMED';
  END IF;
END$$

-- TRIGGER 1: AFTER INSERT ON bookings
--   * decrease schedules.available_seats by seat_count (only if enough seats remain)
--   * write an audit log row
--   * low-seat alert is produced by trg_schedules_after_update (fires on the UPDATE below)
CREATE TRIGGER trg_bookings_after_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
  UPDATE schedules
     SET available_seats = available_seats - NEW.seat_count
   WHERE id = NEW.schedule_id
     AND status = 'ACTIVE'
     AND available_seats >= NEW.seat_count;

  IF ROW_COUNT() = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Not enough available seats on this schedule (or schedule inactive)';
  END IF;

  INSERT INTO audit_logs (booking_id, user_id, action, details)
  VALUES (NEW.id, NEW.user_id, 'BOOKING_CREATED',
          CONCAT('Reference ', NEW.booking_reference, ': ', NEW.seat_count,
                 ' seat(s), total fare ', NEW.total_fare, ' BDT'));
END$$

-- Guard: a booking's status is final once it leaves CONFIRMED (blocks double
-- cancellation / resurrecting cancelled bookings) and its key columns never change.
CREATE TRIGGER trg_bookings_before_update
BEFORE UPDATE ON bookings
FOR EACH ROW
BEGIN
  IF NEW.schedule_id <> OLD.schedule_id
     OR NEW.user_id <> OLD.user_id
     OR NEW.seat_count <> OLD.seat_count
     OR NEW.total_fare <> OLD.total_fare
     OR NEW.booking_reference <> OLD.booking_reference THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking core columns are immutable';
  END IF;

  IF OLD.booking_status <> 'CONFIRMED' AND NEW.booking_status <> OLD.booking_status THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking status is final and cannot be changed';
  END IF;
END$$

-- TRIGGER 2: AFTER UPDATE ON bookings
--   CONFIRMED -> CANCELLED : restore seats exactly once, release seat rows, audit it.
--   CONFIRMED -> COMPLETED : audit only (seats are NOT restored).
--   Any update that leaves booking_status unchanged does nothing.
CREATE TRIGGER trg_bookings_after_update
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
  IF OLD.booking_status = 'CONFIRMED' AND NEW.booking_status = 'CANCELLED' THEN
    UPDATE schedules
       SET available_seats = LEAST(total_seats, available_seats + OLD.seat_count)
     WHERE id = NEW.schedule_id;

    UPDATE booking_seats
       SET seat_status = 'CANCELLED'
     WHERE booking_id = NEW.id;

    INSERT INTO audit_logs (booking_id, user_id, action, details)
    VALUES (NEW.id, NEW.user_id, 'BOOKING_CANCELLED',
            CONCAT('Reference ', NEW.booking_reference, ': ', OLD.seat_count,
                   ' seat(s) released'));
  ELSEIF OLD.booking_status = 'CONFIRMED' AND NEW.booking_status = 'COMPLETED' THEN
    INSERT INTO audit_logs (booking_id, user_id, action, details)
    VALUES (NEW.id, NEW.user_id, 'BOOKING_COMPLETED',
            CONCAT('Reference ', NEW.booking_reference, ' marked completed'));
  END IF;
END$$

-- TRIGGER 3: LOW SEAT ALERT (AFTER UPDATE ON schedules)
--   * crossing DOWN to <= threshold  -> open one alert (never a duplicate while one is open)
--   * still <= threshold, count moved -> refresh the open alert's seat figure
--   * recovering ABOVE threshold      -> resolve open alerts
CREATE TRIGGER trg_schedules_after_update
AFTER UPDATE ON schedules
FOR EACH ROW
BEGIN
  DECLARE v_threshold INT DEFAULT 5;

  IF NEW.available_seats <> OLD.available_seats THEN
    SELECT COALESCE(
             (SELECT CAST(setting_value AS UNSIGNED)
                FROM app_settings WHERE setting_key = 'low_seat_threshold'), 5)
      INTO v_threshold;

    IF NEW.available_seats <= v_threshold THEN
      IF EXISTS (SELECT 1 FROM low_seat_alerts
                  WHERE schedule_id = NEW.id AND resolved_at IS NULL) THEN
        UPDATE low_seat_alerts
           SET available_seats = NEW.available_seats,
               alert_message = CONCAT('Only ', NEW.available_seats, ' seat(s) left on schedule #', NEW.id)
         WHERE schedule_id = NEW.id AND resolved_at IS NULL;
      ELSEIF OLD.available_seats > v_threshold THEN
        INSERT INTO low_seat_alerts (schedule_id, available_seats, threshold, alert_message)
        VALUES (NEW.id, NEW.available_seats, v_threshold,
                CONCAT('Only ', NEW.available_seats, ' seat(s) left on schedule #', NEW.id));
      END IF;
    ELSE
      UPDATE low_seat_alerts
         SET resolved_at = UTC_TIMESTAMP()
       WHERE schedule_id = NEW.id AND resolved_at IS NULL;
    END IF;
  END IF;
END$$

-- Seat integrity: a seat number must exist on the schedule's bus layout.
CREATE TRIGGER trg_booking_seats_before_insert
BEFORE INSERT ON booking_seats
FOR EACH ROW
BEGIN
  DECLARE v_total INT;
  SELECT total_seats INTO v_total FROM schedules WHERE id = NEW.schedule_id;
  IF v_total IS NULL OR NEW.seat_number < 1 OR NEW.seat_number > v_total THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Seat number does not exist on this schedule';
  END IF;
END$$

DELIMITER ;
