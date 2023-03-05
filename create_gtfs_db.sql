DROP TABLE IF EXISTS agency;
DROP TABLE IF EXISTS calendar;
DROP TABLE IF EXISTS calendar_dates;
-- DROP TABLE IF EXISTS fare_attributes;
-- DROP TABLE IF EXISTS fare_rules;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS shapes;
DROP TABLE IF EXISTS stop_times;
DROP TABLE IF EXISTS stops;
DROP TABLE IF EXISTS transfers;
DROP TABLE IF EXISTS trips;


CREATE TABLE agency (
    agency_name TEXT NOT NULL,
    agency_url TEXT NOT NULL,
    agency_timezone TEXT NOT NULL,
    agency_lang TEXT NULL,
    agency_fare_url TEXT NULL
);

CREATE TABLE calendar (
    service_id TEXT PRIMARY KEY,
    monday INT NOT NULL,
    tuesday INT NOT NULL,
    wednesday INT NOT NULL,
    thursday INT NOT NULL,
    friday INT NOT NULL,
    saturday INT NOT NULL,
    sunday INT NOT NULL,
    start_date NUMERIC(8) NOT NULL,
    end_date NUMERIC(8) NOT NULL
);

CREATE TABLE calendar_dates (
    service_id TEXT NOT NULL,
    date NUMERIC(8) NOT NULL,
    exception_type INT NOT NULL
);

-- CREATE TABLE fare_attributes (
--     fare_id INT,
--     price DECIMAL(3,2) DEFAULT NULL,
--     currency_type TEXT DEFAULT NULL,
--     payment_method INT DEFAULT NULL,
--     transfers INT DEFAULT NULL,
--     transfer_duration INT DEFAULT NULL
-- );

-- CREATE TABLE fare_rules (
--     fare_id INT,
--     origin_id INT,
--     destination_id INT
-- );

CREATE TABLE routes (
    route_id TEXT PRIMARY KEY,
    route_short_name TEXT NULL,
    route_long_name TEXT NULL,
    route_type INT NULL,
    route_color TEXT NULL,
    route_text_color TEXT NULL,
    route_url TEXT NULL
);

CREATE TABLE shapes (
    shape_id TEXT,
    shape_pt_lat DOUBLE PRECISION NOT NULL,
    shape_pt_lon DOUBLE PRECISION NOT NULL,
    shape_pt_sequence INT NOT NULL
);

CREATE TABLE stop_times (
    trip_id TEXT NOT NULL,
    arrival_time INTERVAL NOT NULL,
    departure_time INTERVAL NOT NULL,
    stop_id TEXT NOT NULL,
    stop_sequence INT NOT NULL
);

CREATE TABLE stops (
    stop_id INT,
    stop_name TEXT,
    stop_lat DECIMAL,
    stop_lon DECIMAL,
    location_type TEXT DEFAULT NULL,
    parent_station TEXT DEFAULT NULL,
    zone_id INT DEFAULT NULL,
    wheelchair_boarding INT DEFAULT NULL
);

CREATE TABLE transfers (
    from_stop_id TEXT NOT NULL,
    to_stop_id TEXT NOT NULL,
    transfer_type INT NOT NULL,
    min_transfer_time TEXT NULL
);

CREATE TABLE trips (
    route_id TEXT NOT NULL,
    service_id TEXT NOT NULL,
    trip_id TEXT NOT NULL PRIMARY KEY,
    trip_headsign TEXT NULL,
    block_id TEXT NULL,
    direction_id BOOLEAN NULL,
    shape_id TEXT NULL
);

-- \copy agency from './google_bus/agency.txt' with csv header
-- \copy stops from './google_bus/stops.txt' with csv header
-- \copy routes from './google_bus/routes.txt' with csv header
-- \copy calendar from './google_bus/calendar.txt' with csv header
-- \copy calendar_dates from './google_bus/calendar_dates.txt' with csv header
-- \copy shapes from './google_bus/shapes.txt' with csv header
-- \copy trips from './google_bus/trips.txt' with csv header
-- \copy stop_times from './google_bus/stop_times.txt' with csv header
-- \copy transfers from './google_bus/transfers.txt' with csv header