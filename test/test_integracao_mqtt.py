"""Teste opcional com broker e PostgreSQL reais e dados isolados por sensor."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt
import psycopg

RAIZ = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("coletor_integracao", RAIZ / "src" / "coletor.py")
coletor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coletor)


@unittest.skipUnless(os.environ.get("PLUVIA_TEST_DB_URL"), "Defina PLUVIA_TEST_DB_URL para executar a integracao")
class IntegracaoMQTTTest(unittest.TestCase):
    def test_simulador_mqtt_coletor_postgres_e_foto(self):
        url = os.environ["PLUVIA_TEST_DB_URL"]
        broker = os.environ.get("PLUVIA_TEST_BROKER", "127.0.0.1")
        porta = int(os.environ.get("PLUVIA_TEST_BROKER_PORTA", "1883"))
        sensor = "teste_" + uuid.uuid4().hex
        inscrito = threading.Event()
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = coletor.on_message
        client.on_connect = coletor.on_connect
        client.on_subscribe = lambda client, userdata, mid, reasons, properties: inscrito.set() if all(not r.is_failure for r in reasons) else None
        anterior_url, anterior_pasta = coletor.DB_URL, coletor.PASTA_IMAGENS
        try:
            with tempfile.TemporaryDirectory() as pasta:
                coletor.DB_URL = url
                coletor.PASTA_IMAGENS = Path(pasta) / "recebidas"
                foto = Path(pasta) / "teste.jpg"
                # Os bytes de teste exercitam o transporte, sem alegar que sao uma foto decodificavel.
                foto.write_bytes(b"\xff\xd8teste\xff\xd9")
                client.connect(broker, porta, 60)
                client.loop_start()
                self.assertTrue(inscrito.wait(10), "Coletor nao confirmou as assinaturas MQTT")
                resultado = subprocess.run(
                    [sys.executable, str(RAIZ / "src" / "simulador.py"), "--broker", broker,
                     "--porta", str(porta), "--sensor", sensor, "--distancia", "12.5",
                     "--quantidade", "1", "--foto", str(foto)],
                    capture_output=True, text=True, timeout=20,
                )
                self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
                prazo = time.monotonic() + 10
                linha, fotos = None, []
                while time.monotonic() < prazo:
                    with psycopg.connect(url, connect_timeout=3) as conn:
                        linha = conn.execute("SELECT distancia_cm FROM leituras_sensor WHERE sensor_id = %s", (sensor,)).fetchone()
                    fotos = list((coletor.PASTA_IMAGENS / sensor).glob("*.jpg"))
                    if linha is not None and fotos:
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(linha, "Leitura nao chegou ao PostgreSQL")
                self.assertEqual(linha[0], 12.5)
                self.assertEqual(len(fotos), 1)
                self.assertEqual(fotos[0].read_bytes(), foto.read_bytes())
        finally:
            client.disconnect()
            client.loop_stop()
            coletor.DB_URL, coletor.PASTA_IMAGENS = anterior_url, anterior_pasta
            with psycopg.connect(url, connect_timeout=3) as conn:
                conn.execute("DELETE FROM leituras_sensor WHERE sensor_id = %s", (sensor,))


if __name__ == "__main__":
    unittest.main()
