CREATE TABLE IF NOT EXISTS leituras_sensor (
    leitura_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sensor_id TEXT NOT NULL,
    distancia_cm DOUBLE PRECISION NOT NULL CHECK (distancia_cm BETWEEN 2 AND 400)
);

CREATE INDEX IF NOT EXISTS leituras_sensor_ts_idx ON leituras_sensor (ts_utc DESC, leitura_id DESC);
