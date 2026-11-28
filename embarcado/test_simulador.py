import unittest

from embarcado.simulador import distancia_no_ciclo


class SimuladorTest(unittest.TestCase):
    def test_ciclo_atraves_dos_extremos_e_reinicio(self):
        self.assertEqual(distancia_no_ciclo(0, 5, 30, 60), 30)
        self.assertEqual(distancia_no_ciclo(30, 5, 30, 60), 5)
        self.assertEqual(distancia_no_ciclo(60, 5, 30, 60), 30)
        self.assertEqual(distancia_no_ciclo(15, 5, 30, 60), 17.5)


if __name__ == "__main__":
    unittest.main()
