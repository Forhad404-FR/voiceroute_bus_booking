-- =============================================================================
-- VoiceRoute - database/seed.sql   (reference data)
-- Idempotent: INSERT IGNORE against UNIQUE keys, never deletes or overwrites rows.
--
-- *** DEMONSTRATION / SAMPLE DATA ONLY ***
-- Operators, buses, terminals, distances, durations and fares are fictional sample
-- data for an academic project. They are NOT verified live operator information
-- and imply no affiliation with any real transport company.
--
-- Run order: schema.sql -> triggers.sql -> seed.sql -> generate_schedules.sql
-- =============================================================================

SET NAMES utf8mb4;

-- 1. Exactly 30 districts --------------------------------------------------------
INSERT IGNORE INTO districts (district_name, slug) VALUES
 ('Dhaka','dhaka'),('Chattogram','chattogram'),('Gazipur','gazipur'),('Narayanganj','narayanganj'),
 ('Cumilla','cumilla'),('Cox''s Bazar','coxs-bazar'),('Feni','feni'),('Noakhali','noakhali'),
 ('Chandpur','chandpur'),('Brahmanbaria','brahmanbaria'),('Sylhet','sylhet'),('Moulvibazar','moulvibazar'),
 ('Habiganj','habiganj'),('Sunamganj','sunamganj'),('Rajshahi','rajshahi'),('Bogura','bogura'),
 ('Pabna','pabna'),('Sirajganj','sirajganj'),('Rangpur','rangpur'),('Dinajpur','dinajpur'),
 ('Kurigram','kurigram'),('Khulna','khulna'),('Jashore','jashore'),('Satkhira','satkhira'),
 ('Kushtia','kushtia'),('Barishal','barishal'),('Patuakhali','patuakhali'),('Bhola','bhola'),
 ('Mymensingh','mymensingh'),('Tangail','tangail');

-- 2. One sample terminal per district -------------------------------------------
INSERT IGNORE INTO stations (station_name, district_id, address)
SELECT CONCAT(d.district_name, ' Central Bus Terminal (Sample)'), d.id,
       CONCAT('Sample address, ', d.district_name)
  FROM districts d;

-- 3. Fictional demonstration operators ------------------------------------------
INSERT IGNORE INTO transport_operators (operator_name, contact_phone, contact_email) VALUES
 ('GreenLine Express', '+8801000000101', 'demo@greenline-express.example'),
 ('Royal Coach',       '+8801000000102', 'demo@royal-coach.example'),
 ('Shohagh Travels',   '+8801000000103', 'demo@shohagh-travels.example'),
 ('Eagle Transport',   '+8801000000104', 'demo@eagle-transport.example'),
 ('Starline Express',  '+8801000000105', 'demo@starline-express.example'),
 ('Northern Express',  '+8801000000106', 'demo@northern-express.example');

-- 4. Demonstration buses (3 per operator; mixed types and capacities) ------------
INSERT IGNORE INTO buses (operator_id, bus_name, bus_type, registration_number, total_seats)
SELECT o.id, v.bus_name, v.bus_type, v.reg, v.seats
  FROM (
    SELECT 'GreenLine Express' AS op, 'Green Voyager' AS bus_name, 'AC' AS bus_type, 'DEMO-GL-1001' AS reg, 36 AS seats
    UNION ALL SELECT 'GreenLine Express','Green Cruiser','AC','DEMO-GL-1002',40
    UNION ALL SELECT 'GreenLine Express','Green Saver','NON_AC','DEMO-GL-1003',44
    UNION ALL SELECT 'Royal Coach','Royal Sovereign','AC','DEMO-RC-2001',32
    UNION ALL SELECT 'Royal Coach','Royal Crown','AC','DEMO-RC-2002',36
    UNION ALL SELECT 'Royal Coach','Royal Standard','NON_AC','DEMO-RC-2003',40
    UNION ALL SELECT 'Shohagh Travels','Shohagh Gold','AC','DEMO-ST-3001',40
    UNION ALL SELECT 'Shohagh Travels','Shohagh Classic','NON_AC','DEMO-ST-3002',44
    UNION ALL SELECT 'Shohagh Travels','Shohagh Local','NON_AC','DEMO-ST-3003',40
    UNION ALL SELECT 'Eagle Transport','Eagle Sky','AC','DEMO-ET-4001',36
    UNION ALL SELECT 'Eagle Transport','Eagle Wing','AC','DEMO-ET-4002',32
    UNION ALL SELECT 'Eagle Transport','Eagle Ride','NON_AC','DEMO-ET-4003',44
    UNION ALL SELECT 'Starline Express','Star Premium','AC','DEMO-SL-5001',40
    UNION ALL SELECT 'Starline Express','Star Comfort','AC','DEMO-SL-5002',36
    UNION ALL SELECT 'Starline Express','Star Economy','NON_AC','DEMO-SL-5003',40
    UNION ALL SELECT 'Northern Express','Northern Pride','AC','DEMO-NE-6001',40
    UNION ALL SELECT 'Northern Express','Northern Standard','NON_AC','DEMO-NE-6002',44
    UNION ALL SELECT 'Northern Express','Northern Plus','AC','DEMO-NE-6003',32
  ) v
  JOIN transport_operators o ON o.operator_name = v.op;

-- 5. Two-hub route network ---------------------------------------------------------
-- Approximate SAMPLE road distances (km) from each hub. Not surveyed data.
DROP TEMPORARY TABLE IF EXISTS tmp_km;
CREATE TEMPORARY TABLE tmp_km (
  district_name VARCHAR(60) PRIMARY KEY,
  km_dhaka SMALLINT UNSIGNED NOT NULL,
  km_ctg   SMALLINT UNSIGNED NOT NULL
);
INSERT INTO tmp_km (district_name, km_dhaka, km_ctg) VALUES
 ('Dhaka',0,250),('Chattogram',250,0),('Gazipur',40,270),('Narayanganj',25,240),
 ('Cumilla',100,160),('Cox''s Bazar',400,150),('Feni',160,100),('Noakhali',170,140),
 ('Chandpur',110,190),('Brahmanbaria',100,200),('Sylhet',240,350),('Moulvibazar',180,330),
 ('Habiganj',130,300),('Sunamganj',300,420),('Rajshahi',255,500),('Bogura',200,450),
 ('Pabna',160,410),('Sirajganj',130,380),('Rangpur',300,520),('Dinajpur',400,620),
 ('Kurigram',350,570),('Khulna',270,480),('Jashore',190,440),('Satkhira',300,540),
 ('Kushtia',180,420),('Barishal',180,350),('Patuakhali',250,400),('Bhola',280,330),
 ('Mymensingh',120,330),('Tangail',90,300);

-- Hub = Dhaka: Dhaka -> X
INSERT IGNORE INTO routes (source_station_id, destination_station_id, distance_km, estimated_duration_minutes, description)
SELECT hs.id, xs.id, k.km_dhaka, CEIL(k.km_dhaka * 1.4) + 15, 'Sample route (demonstration data)'
  FROM districts hd
  JOIN stations hs ON hs.district_id = hd.id
  JOIN districts xd ON xd.district_name <> hd.district_name
  JOIN stations xs ON xs.district_id = xd.id
  JOIN tmp_km k ON k.district_name = xd.district_name
 WHERE hd.district_name = 'Dhaka';

-- Hub = Dhaka: X -> Dhaka
INSERT IGNORE INTO routes (source_station_id, destination_station_id, distance_km, estimated_duration_minutes, description)
SELECT xs.id, hs.id, k.km_dhaka, CEIL(k.km_dhaka * 1.4) + 15, 'Sample route (demonstration data)'
  FROM districts hd
  JOIN stations hs ON hs.district_id = hd.id
  JOIN districts xd ON xd.district_name <> hd.district_name
  JOIN stations xs ON xs.district_id = xd.id
  JOIN tmp_km k ON k.district_name = xd.district_name
 WHERE hd.district_name = 'Dhaka';

-- Hub = Chattogram: Chattogram -> X   (Chattogram->Dhaka already exists: ignored)
INSERT IGNORE INTO routes (source_station_id, destination_station_id, distance_km, estimated_duration_minutes, description)
SELECT hs.id, xs.id, k.km_ctg, CEIL(k.km_ctg * 1.4) + 15, 'Sample route (demonstration data)'
  FROM districts hd
  JOIN stations hs ON hs.district_id = hd.id
  JOIN districts xd ON xd.district_name <> hd.district_name
  JOIN stations xs ON xs.district_id = xd.id
  JOIN tmp_km k ON k.district_name = xd.district_name
 WHERE hd.district_name = 'Chattogram';

-- Hub = Chattogram: X -> Chattogram   (Dhaka->Chattogram already exists: ignored)
INSERT IGNORE INTO routes (source_station_id, destination_station_id, distance_km, estimated_duration_minutes, description)
SELECT xs.id, hs.id, k.km_ctg, CEIL(k.km_ctg * 1.4) + 15, 'Sample route (demonstration data)'
  FROM districts hd
  JOIN stations hs ON hs.district_id = hd.id
  JOIN districts xd ON xd.district_name <> hd.district_name
  JOIN stations xs ON xs.district_id = xd.id
  JOIN tmp_km k ON k.district_name = xd.district_name
 WHERE hd.district_name = 'Chattogram';

DROP TEMPORARY TABLE IF EXISTS tmp_km;
