-- =============================================================================
-- VoiceRoute - database/generate_schedules.sql
-- Generates SAMPLE schedules for the next 30 days (Bangladesh time, UTC+6) for every
-- route: 3 departures per route and day, different buses, times and fares.
-- Idempotent and re-runnable any time to roll the window forward: INSERT IGNORE
-- against UNIQUE (bus_id, route_id, departure_date, departure_time). Existing
-- schedules, their seat counts and bookings are never modified by the INSERT.
--
-- *** DEMONSTRATION DATA ONLY - not real operator timetables or fares. ***
-- =============================================================================

INSERT IGNORE INTO schedules
  (bus_id, route_id, departure_date, departure_time, arrival_time, fare,
   total_seats, available_seats, status)
WITH RECURSIVE
  day_offsets (n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM day_offsets WHERE n < 29
  ),
  bd_today (d) AS (
    SELECT DATE(UTC_TIMESTAMP() + INTERVAL 6 HOUR)
  ),
  slots (k, base_minutes, fare_mult) AS (
    SELECT 0, 390, 1.00 UNION ALL SELECT 1, 780, 1.08 UNION ALL SELECT 2, 1320, 0.94
  ),
  ranked_buses AS (
    SELECT id, bus_type, total_seats,
           ROW_NUMBER() OVER (ORDER BY id) - 1 AS rn
      FROM buses WHERE is_active = 1
  ),
  bus_count (c) AS (
    SELECT COUNT(*) FROM buses WHERE is_active = 1
  )
SELECT br.id,
       r.id,
       DATE_ADD(bt.d, INTERVAL dn.n DAY),
       SEC_TO_TIME((sl.base_minutes + MOD(r.id, 6) * 10) * 60),
       TIME(TIMESTAMP(DATE_ADD(bt.d, INTERVAL dn.n DAY),
                      SEC_TO_TIME((sl.base_minutes + MOD(r.id, 6) * 10) * 60))
            + INTERVAL COALESCE(r.estimated_duration_minutes, 360) MINUTE),
       GREATEST(150, ROUND(COALESCE(r.distance_km, 100)
                           * IF(br.bus_type = 'AC', 4.5, 2.7) * sl.fare_mult / 10) * 10),
       br.total_seats,
       br.total_seats,
       'ACTIVE'
  FROM routes r
  CROSS JOIN slots sl
  CROSS JOIN day_offsets dn
  CROSS JOIN bd_today bt
  CROSS JOIN bus_count bc
  JOIN ranked_buses br ON br.rn = MOD(r.id * 3 + sl.k * 5, bc.c)
 WHERE bc.c > 0;

-- Departures already in the past (Bangladesh time) are no longer bookable.
UPDATE schedules
   SET status = 'COMPLETED'
 WHERE status = 'ACTIVE'
   AND TIMESTAMP(departure_date, departure_time) < (UTC_TIMESTAMP() + INTERVAL 6 HOUR);
