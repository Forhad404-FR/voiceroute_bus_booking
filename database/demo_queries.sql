-- =============================================================================
-- VoiceRoute - database/demo_queries.sql
-- SQL demonstration for the DBMS course. Run in any MySQL 8 client after the schema,
-- triggers and seed data have been loaded. Queries 1-15 are read-only. The booking
-- and cancellation demos (16, 17) end in ROLLBACK so they leave data unchanged
-- (change ROLLBACK to COMMIT to keep the effect).
-- All transport data is sample/demonstration data.
-- =============================================================================

-- 1. SELECT: all districts (exactly 30)
SELECT id, district_name, slug FROM districts ORDER BY district_name;

-- 2. WHERE + ORDER BY: AC buses with many seats, largest first
SELECT bus_name, bus_type, total_seats
  FROM buses
 WHERE bus_type = 'AC' AND total_seats >= 36
 ORDER BY total_seats DESC, bus_name;

-- 3. COUNT / GROUP BY: how many buses per operator
SELECT o.operator_name, COUNT(b.id) AS bus_count
  FROM transport_operators o
  LEFT JOIN buses b ON b.operator_id = o.id
 GROUP BY o.id, o.operator_name
 ORDER BY bus_count DESC, o.operator_name;

-- 4. GROUP BY + HAVING: operators that run more than 2 AC buses
SELECT o.operator_name, COUNT(*) AS ac_buses
  FROM transport_operators o
  JOIN buses b ON b.operator_id = o.id
 WHERE b.bus_type = 'AC'
 GROUP BY o.id, o.operator_name
HAVING COUNT(*) > 2;

-- 5. INNER JOIN: every route with its origin and destination district
SELECT r.id AS route_id, sd.district_name AS origin, dd.district_name AS destination,
       r.distance_km, r.estimated_duration_minutes
  FROM routes r
  JOIN stations ss   ON ss.id = r.source_station_id
  JOIN districts sd  ON sd.id = ss.district_id
  JOIN stations ds   ON ds.id = r.destination_station_id
  JOIN districts dd  ON dd.id = ds.district_id
 ORDER BY sd.district_name, dd.district_name;

-- 6. LEFT JOIN: districts that are NOT the origin of any route (non-hub districts have
--    exactly one outgoing route to each hub, so "no route to Dhaka" shows gaps if any)
SELECT d.district_name, COUNT(r.id) AS outgoing_routes
  FROM districts d
  JOIN stations s ON s.district_id = d.id
  LEFT JOIN routes r ON r.source_station_id = s.id
 GROUP BY d.id, d.district_name
 ORDER BY outgoing_routes DESC, d.district_name;

-- 7. Multi-table JOIN (districts, stations, routes, schedules, buses, operators):
--    buses from Dhaka to Sylhet on the earliest date that has departures
SELECT o.operator_name, b.bus_name, b.bus_type,
       sch.departure_date, sch.departure_time, sch.arrival_time,
       sch.fare, sch.available_seats, sch.total_seats
  FROM schedules sch
  JOIN buses b                 ON b.id = sch.bus_id
  JOIN transport_operators o   ON o.id = b.operator_id
  JOIN routes r                ON r.id = sch.route_id
  JOIN stations ss             ON ss.id = r.source_station_id
  JOIN districts sd            ON sd.id = ss.district_id
  JOIN stations ds             ON ds.id = r.destination_station_id
  JOIN districts dd            ON dd.id = ds.district_id
 WHERE sd.district_name = 'Dhaka'
   AND dd.district_name = 'Sylhet'
   AND sch.status = 'ACTIVE'
   AND sch.departure_date = (SELECT MIN(departure_date) FROM schedules WHERE status = 'ACTIVE')
 ORDER BY sch.departure_time;

-- 8. Subquery (scalar): schedules cheaper than the average fare
SELECT id, route_id, fare
  FROM schedules
 WHERE fare < (SELECT AVG(fare) FROM schedules)
 ORDER BY fare
 LIMIT 20;

-- 9. Subquery (IN): users who have at least one confirmed booking
SELECT id, full_name, phone_number
  FROM users
 WHERE id IN (SELECT user_id FROM bookings WHERE booking_status = 'CONFIRMED');

-- 10. Subquery (correlated, NOT EXISTS): schedules nobody has booked yet (first 20)
SELECT s.id, s.departure_date, s.departure_time
  FROM schedules s
 WHERE NOT EXISTS (SELECT 1 FROM bookings bk WHERE bk.schedule_id = s.id)
 ORDER BY s.departure_date, s.departure_time
 LIMIT 20;

-- 11. Booking report: each booking with passenger, route, bus and seats
SELECT bk.booking_reference, u.full_name AS passenger,
       sd.district_name AS origin, dd.district_name AS destination,
       o.operator_name, b.bus_name,
       sch.departure_date, sch.departure_time,
       GROUP_CONCAT(bs.seat_number ORDER BY bs.seat_number) AS seats,
       bk.seat_count, bk.total_fare, bk.booking_status, bk.booked_at
  FROM bookings bk
  JOIN users u                 ON u.id = bk.user_id
  JOIN schedules sch           ON sch.id = bk.schedule_id
  JOIN buses b                 ON b.id = sch.bus_id
  JOIN transport_operators o   ON o.id = b.operator_id
  JOIN routes r                ON r.id = sch.route_id
  JOIN stations ss             ON ss.id = r.source_station_id
  JOIN districts sd            ON sd.id = ss.district_id
  JOIN stations ds             ON ds.id = r.destination_station_id
  JOIN districts dd            ON dd.id = ds.district_id
  LEFT JOIN booking_seats bs   ON bs.booking_id = bk.id
 GROUP BY bk.id, u.full_name, sd.district_name, dd.district_name, o.operator_name,
          b.bus_name, sch.departure_date, sch.departure_time
 ORDER BY bk.booked_at DESC;

-- 12. Popular routes report (confirmed + completed bookings only)
SELECT sd.district_name AS origin, dd.district_name AS destination,
       COUNT(bk.id) AS bookings, SUM(bk.seat_count) AS seats_sold, SUM(bk.total_fare) AS revenue
  FROM bookings bk
  JOIN schedules sch ON sch.id = bk.schedule_id
  JOIN routes r      ON r.id = sch.route_id
  JOIN stations ss   ON ss.id = r.source_station_id
  JOIN districts sd  ON sd.id = ss.district_id
  JOIN stations ds   ON ds.id = r.destination_station_id
  JOIN districts dd  ON dd.id = ds.district_id
 WHERE bk.booking_status IN ('CONFIRMED','COMPLETED')
 GROUP BY r.id, sd.district_name, dd.district_name
 ORDER BY bookings DESC, seats_sold DESC
 LIMIT 10;

-- 13. Total revenue (SUM) and status breakdown (GROUP BY)
SELECT booking_status, COUNT(*) AS bookings, COALESCE(SUM(total_fare), 0) AS fare_total
  FROM bookings
 GROUP BY booking_status;

SELECT COALESCE(SUM(total_fare), 0) AS total_revenue
  FROM bookings
 WHERE booking_status IN ('CONFIRMED','COMPLETED');

-- 14. Low-seat alerts (open alerts with route and bus context)
SELECT a.id, a.alert_message, a.available_seats, a.threshold, a.created_at,
       sd.district_name AS origin, dd.district_name AS destination, b.bus_name
  FROM low_seat_alerts a
  JOIN schedules sch ON sch.id = a.schedule_id
  JOIN buses b       ON b.id = sch.bus_id
  JOIN routes r      ON r.id = sch.route_id
  JOIN stations ss   ON ss.id = r.source_station_id
  JOIN districts sd  ON sd.id = ss.district_id
  JOIN stations ds   ON ds.id = r.destination_station_id
  JOIN districts dd  ON dd.id = ds.district_id
 WHERE a.resolved_at IS NULL
 ORDER BY a.available_seats, a.created_at DESC;

-- 15. Audit trail written by the triggers
SELECT al.created_at, al.action, al.details, bk.booking_reference
  FROM audit_logs al
  LEFT JOIN bookings bk ON bk.id = al.booking_id
 ORDER BY al.id DESC
 LIMIT 30;

-- 16. TRANSACTION EXAMPLE: booking 2 seats safely (rolls back; use COMMIT to keep)
--     Needs at least one registered user and one active schedule with >= 2 free seats.
SET @uid   := (SELECT MIN(id) FROM users);
SET @sid   := (SELECT MIN(id) FROM schedules
                WHERE status = 'ACTIVE' AND available_seats >= 2
                  AND TIMESTAMP(departure_date, departure_time) > (UTC_TIMESTAMP() + INTERVAL 6 HOUR));

START TRANSACTION;
  -- (a) lock the schedule row so concurrent bookings queue behind us
  SELECT id, fare, total_seats, available_seats FROM schedules WHERE id = @sid FOR UPDATE;
  -- (b) lock/check the seats we want (empty result = seats are free)
  SELECT seat_number FROM booking_seats
   WHERE schedule_id = @sid AND seat_status = 'BOOKED' AND seat_number IN (1, 2) FOR UPDATE;
  -- (c) insert booking; server computes fare from the schedule, never from the client
  INSERT INTO bookings (booking_reference, user_id, schedule_id, seat_count, total_fare)
  SELECT 'VR-DEMO000001', @uid, id, 2, fare * 2 FROM schedules WHERE id = @sid;
  SET @bid := LAST_INSERT_ID();
  INSERT INTO booking_seats (booking_id, schedule_id, seat_number) VALUES (@bid, @sid, 1), (@bid, @sid, 2);
  -- (d) trigger trg_bookings_after_insert already decreased available_seats by 2:
  SELECT id, total_seats, available_seats FROM schedules WHERE id = @sid;
ROLLBACK;   -- everything above is undone, including the trigger's effects
SELECT id, total_seats, available_seats FROM schedules WHERE id = @sid;  -- back to the original

-- 17. CANCELLATION EXAMPLE: status change fires trg_bookings_after_update
--     (seats restored once, seat rows released, audit row written). Rolls back.
SET @bk := (SELECT MIN(id) FROM bookings WHERE booking_status = 'CONFIRMED');
START TRANSACTION;
  SELECT schedule_id, seat_count, booking_status FROM bookings WHERE id = @bk FOR UPDATE;
  UPDATE bookings SET booking_status = 'CANCELLED', cancelled_at = UTC_TIMESTAMP()
   WHERE id = @bk AND booking_status = 'CONFIRMED';
  SELECT id, available_seats FROM schedules WHERE id = (SELECT schedule_id FROM bookings WHERE id = @bk);
  SELECT seat_number, seat_status FROM booking_seats WHERE booking_id = @bk;
  -- a second cancellation is rejected by trg_bookings_before_update (status is final):
  -- UPDATE bookings SET booking_status = 'CANCELLED' WHERE id = @bk;   -- ERROR 1644 (45000)
ROLLBACK;

-- 18. Proof that the database itself blocks double booking of a seat:
--     the generated column active_seat + UNIQUE(schedule_id, active_seat)
SHOW CREATE TABLE booking_seats;
SHOW TRIGGERS;
