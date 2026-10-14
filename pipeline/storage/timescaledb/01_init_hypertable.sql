-- =======================================================
-- CanSat Telemetry & Flight Analytics - TimescaleDB Init
-- Enriched with Cognitive CanSat Aerospace Sensor Suite
-- =======================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Hot Path: Raw and Processed Telemetry Table
CREATE TABLE IF NOT EXISTS raw_telemetry (
    time TIMESTAMPTZ NOT NULL,
    mission_id VARCHAR(64) NOT NULL DEFAULT 'MISSION_ALPHA_01',
    packet_id BIGINT NOT NULL,
    altitude_m DOUBLE PRECISION,
    pressure_hpa DOUBLE PRECISION,
    velocity_mps DOUBLE PRECISION,
    accel_x_g DOUBLE PRECISION,
    accel_y_g DOUBLE PRECISION,
    accel_z_g DOUBLE PRECISION,
    gyro_x_dps DOUBLE PRECISION,
    gyro_y_dps DOUBLE PRECISION,
    gyro_z_dps DOUBLE PRECISION,
    battery_v DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION,
    flight_stage VARCHAR(32) DEFAULT 'LAUNCH_PAD',
    status VARCHAR(64) DEFAULT 'OK',
    -- Enriched Aerospace & Kinematic Columns
    humidity_pct DOUBLE PRECISION DEFAULT 50.0,
    lat DOUBLE PRECISION DEFAULT 22.5727,
    lon DOUBLE PRECISION DEFAULT 88.3655,
    pitch_deg DOUBLE PRECISION DEFAULT 0.0,
    roll_deg DOUBLE PRECISION DEFAULT 0.0,
    accel_mag_g DOUBLE PRECISION DEFAULT 1.0,
    anomaly_score DOUBLE PRECISION DEFAULT 0.0,
    is_anomaly BOOLEAN DEFAULT FALSE,
    dew_point_c DOUBLE PRECISION,
    air_density_kg_m3 DOUBLE PRECISION,
    calibrated_altitude_m DOUBLE PRECISION
);

-- Idempotent column migrations for existing instances
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS humidity_pct DOUBLE PRECISION DEFAULT 50.0;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION DEFAULT 22.5727;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION DEFAULT 88.3655;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS pitch_deg DOUBLE PRECISION DEFAULT 0.0;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS roll_deg DOUBLE PRECISION DEFAULT 0.0;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS accel_mag_g DOUBLE PRECISION DEFAULT 1.0;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS anomaly_score DOUBLE PRECISION DEFAULT 0.0;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS is_anomaly BOOLEAN DEFAULT FALSE;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS dew_point_c DOUBLE PRECISION;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS air_density_kg_m3 DOUBLE PRECISION;
ALTER TABLE raw_telemetry ADD COLUMN IF NOT EXISTS calibrated_altitude_m DOUBLE PRECISION;

-- Convert to Hypertable (partitioned by time in 1-hour chunks)
SELECT create_hypertable('raw_telemetry', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 hour');

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_telemetry_packet ON raw_telemetry (packet_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_stage ON raw_telemetry (flight_stage, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_mission ON raw_telemetry (mission_id, time DESC);

-- Flight Events & Anomaly Table
CREATE TABLE IF NOT EXISTS flight_events (
    time TIMESTAMPTZ NOT NULL,
    mission_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'INFO',
    description TEXT,
    metric_value DOUBLE PRECISION
);

SELECT create_hypertable('flight_events', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_flight_events_mission ON flight_events (mission_id, time DESC);

-- Continuous Aggregate View for 1-Second Flight Aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_1s_summary
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 second', time) AS bucket,
    mission_id,
    AVG(altitude_m) AS avg_altitude,
    MAX(altitude_m) AS max_altitude,
    AVG(velocity_mps) AS avg_velocity,
    AVG(accel_z_g) AS avg_accel_z,
    AVG(battery_v) AS avg_battery,
    AVG(anomaly_score) AS avg_anomaly_score,
    COUNT(*) AS packets_per_second
FROM raw_telemetry
GROUP BY bucket, mission_id
WITH NO DATA;
