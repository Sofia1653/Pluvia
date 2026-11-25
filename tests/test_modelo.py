import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import modelo as mod
import preparacao as prep


def dados(n=4000, semente=0):
    rng = np.random.default_rng(semente)
    X = pd.DataFrame({"chuva_dia_mm": rng.gamma(0.5, 10, n), "alt_media_m": rng.normal(10, 5, n)})
    X.loc[::9, "alt_media_m"] = np.nan                          # vazios: o preparo de cada modelo deve trata-los
    y = (X["chuva_dia_mm"] + rng.normal(0, 5, n) > 40).astype(int).values
    return X, y


class ModelosTest(unittest.TestCase):
    def test_especificacao_baseline_e_tres_da_lista(self):
        self.assertEqual(mod.BASELINE, "logistica")
        self.assertGreaterEqual(len(mod.MODELOS_DA_LISTA), 3)
        self.assertNotIn(mod.MODELO_ADICIONAL, mod.MODELOS_DA_LISTA)
        self.assertEqual(set(mod.COMPLEXIDADE), {mod.BASELINE, mod.MODELO_ADICIONAL, *mod.MODELOS_DA_LISTA})

    def test_todo_modelo_tem_fabrica_padrao_e_preparo(self):
        for nome in mod.COMPLEXIDADE:
            self.assertIn(nome, mod.FABRICAS)
            self.assertIn(nome, mod.PADROES)
            self.assertIn(nome, mod.PREP_KW)

    def test_treina_e_preve_probabilidades(self):
        X, y = dados()
        for nome in mod.COMPLEXIDADE:
            with self.subTest(modelo=nome):
                preparador = prep.Preparador(**mod.PREP_KW[nome]).fit(X)
                est = mod.FABRICAS[nome](**mod.PADROES[nome]).fit(preparador.transform(X), y)
                p = est.predict_proba(preparador.transform(X))[:, 1]
                self.assertEqual(p.shape, (len(X),))
                self.assertTrue(np.all((p >= 0) & (p <= 1)))
                self.assertGreater(mod.metricas(y, p)["roc_auc"], 0.7)   # aprende o sinal obvio da chuva

    def test_metricas_f1_no_corte(self):
        y = np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0])
        p = np.array([.9, .8, .1, .1, .2, .1, .1, .1, .1, .1])
        m = mod.metricas(y, p, qs=(0.2,))                         # alerta 2 de 10: acha 1 dos 2 positivos
        self.assertAlmostEqual(m["recall_top20"], 0.5)
        self.assertAlmostEqual(m["precisao_top20"], 0.5)
        self.assertAlmostEqual(m["f1_top20"], 0.5)

    def test_pesos_positivos(self):
        w = mod._pesos_positivos(np.array([1, 0, 0, 0, 0]), 0.5)
        self.assertAlmostEqual(w[0], 2.0)                          # raiz de 4 negativos / 1 positivo
        self.assertTrue(np.all(w[1:] == 1.0))


if __name__ == "__main__":
    unittest.main()
