-- Para bancos ja criados com o schema completo da integration.
-- Execute uma vez com psql antes de iniciar o coletor atualizado.
ALTER TABLE leituras_sensor ALTER COLUMN ts_utc SET DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS leituras_sensor_ts_idx ON leituras_sensor (ts_utc DESC, leitura_id DESC);
