import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg
import pandas as pd
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "applications" / "dashboard"))
import app as dashboard


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class BancoTeste:
    def __init__(self):
        agora = datetime.now(timezone.utc)
        self.registros = [
            (agora - timedelta(minutes=30), "A", 10.0),
            (agora - timedelta(minutes=20), "A", 20.0),
            (agora - timedelta(seconds=5), "B", 25.0),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=None):
        if "DISTINCT sensor_id" in sql:
            return Cursor([("A",), ("B",)])
        sensor = params[0]
        registros = [r for r in self.registros if r[1] == sensor]
        if "MIN(distancia_cm)" in sql:
            valores = [r[2] for r in registros if params[1] <= r[0] < params[2]]
            return Cursor([(min(valores) if valores else None,)])
        if "LIMIT 1" in sql:
            return Cursor([(registros[-1][0], registros[-1][2])] if registros else [])
        return Cursor([r for r in registros if params[1] <= r[0] < params[2]])


class DashboardTest(unittest.TestCase):
    def test_associacao_de_camera_usa_foto_correta_e_recente(self):
        agora = datetime.now()
        fotos = [
            {"sensor": "camera_a", "arquivo": "a.jpg", "timestamp": agora - timedelta(seconds=5)},
            {"sensor": "camera_b", "arquivo": "b.jpg", "timestamp": agora - timedelta(seconds=2)},
        ]
        analises = pd.DataFrame([
            {"arquivo": "a.jpg", "nivel_minimo": 2},
            {"arquivo": "b.jpg", "nivel_minimo": 3},
        ])
        nivel, analise = dashboard.nivel_imagem_recente(fotos, analises, "camera_a", agora)
        self.assertEqual((nivel, analise["arquivo"]), (2, "a.jpg"))
        self.assertEqual(dashboard.nivel_imagem_recente(fotos, analises, "Nenhuma", agora), (0, None))
        self.assertEqual(dashboard.nivel_imagem_recente(fotos, analises, "camera_a", agora + timedelta(minutes=11))[0], 0)

    def test_filtro_sensor_maximo_e_sensor_parado(self):
        with patch.dict(os.environ, {"PLUVIA_DB_URL": "postgresql://teste"}), patch("psycopg.connect", side_effect=lambda *a, **k: BancoTeste()):
            app = AppTest.from_file(str(RAIZ / "applications" / "dashboard" / "app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            metricas = {m.label: m.value for m in app.metric}
            self.assertEqual(metricas["Máximo de hoje"], "20.0 cm")
            self.assertEqual(metricas["Status do ponto"], "Sem leitura recente")
            self.assertTrue(any("não envia leituras" in w.value for w in app.warning))
            app.selectbox[0].select("B").run()
            self.assertFalse(app.exception)
            metricas = {m.label: m.value for m in app.metric}
            self.assertEqual(metricas["Nível da água"], "5.0 cm")
            self.assertFalse(any("não envia leituras" in w.value for w in app.warning))
            ontem = datetime.now().date() - timedelta(days=1)
            app.date_input[0].set_value(ontem).run()
            app.date_input[1].set_value(ontem).run()
            self.assertTrue(any("Nenhuma leitura" in i.value for i in app.info))
            self.assertEqual({m.label: m.value for m in app.metric}["Nível da água"], "5.0 cm")

    def test_banco_indisponivel_mostra_erro(self):
        with patch.dict(os.environ, {"PLUVIA_DB_URL": "postgresql://teste"}), patch("psycopg.connect", side_effect=psycopg.OperationalError("fora")):
            app = AppTest.from_file(str(RAIZ / "applications" / "dashboard" / "app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("PostgreSQL" in e.value for e in app.error))


if __name__ == "__main__":
    unittest.main()
