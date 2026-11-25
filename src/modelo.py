"""Modelos, validacao e metricas do risco de alagamento.

Compartilhado pelos notebooks de treino, pelo DAG do Airflow e pela API de inferencia (que carrega ModeloRisco).
Depende de preparacao.py (precisa estar no mesmo caminho de importacao).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import AdaBoostClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier

import preparacao as prep

SEMENTE = 42
# do mais simples ao mais complexo (a regra de parcimonia percorre nesta ordem).
# logistica = baseline; arvore, floresta e adaboost = os tres modelos da lista da especificacao;
# boosting (HistGradientBoosting) = modelo adicional, fora da lista (depende de aval do professor)
COMPLEXIDADE = ["logistica", "arvore", "floresta", "adaboost", "boosting"]
BASELINE = "logistica"
MODELOS_DA_LISTA = ["arvore", "floresta", "adaboost"]
MODELO_ADICIONAL = "boosting"


def _pesos_positivos(y, expoente):
    """Peso do positivo = (negativos/positivos) ** expoente; 0.5 = raiz (o peso integral, ~1400x, causa sobreajuste)."""
    y = np.asarray(y)
    pos = max(int(y.sum()), 1)
    razao = (len(y) - pos) / pos
    return np.where(y == 1, razao ** expoente, 1.0)


# ------------------------------------------------------------------ estimadores (interface: fit / predict_proba)
class Logistica:
    def __init__(self, C=0.1, class_weight="balanced", max_iter=500):
        self.C, self.class_weight, self.max_iter = C, class_weight, max_iter

    def fit(self, X, y):
        self.m_ = LogisticRegression(C=self.C, class_weight=self.class_weight, max_iter=self.max_iter)
        self.m_.fit(X, y)
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(X)


class Arvore:
    """Arvore de decisao unica: o modelo de arvores mais simples e o mais facil de explicar (regras se/entao).
    Rasa e com folhas grandes porque, com ~160 eventos, uma arvore profunda decora os poucos positivos."""

    def __init__(self, max_depth=5, min_samples_leaf=300, peso_pos_exp=0.5, semente=SEMENTE):
        self.max_depth, self.min_samples_leaf = max_depth, min_samples_leaf
        self.peso_pos_exp, self.semente = peso_pos_exp, semente

    def fit(self, X, y):
        self.m_ = DecisionTreeClassifier(max_depth=self.max_depth, min_samples_leaf=self.min_samples_leaf,
                                         random_state=self.semente)
        self.m_.fit(X, y, sample_weight=_pesos_positivos(y, self.peso_pos_exp))
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(X)


class AdaBoost:
    """AdaBoost com arvores rasas (tocos de profundidade 2): cada arvore nova foca nos exemplos que as anteriores
    erraram. Os positivos ja comecam com peso maior (raiz do desbalanceamento), como no boosting."""

    def __init__(self, n_estimators=200, learning_rate=0.1, max_depth=2, min_samples_leaf=200, peso_pos_exp=0.5,
                 semente=SEMENTE):
        self.n_estimators, self.learning_rate, self.max_depth = n_estimators, learning_rate, max_depth
        self.min_samples_leaf, self.peso_pos_exp, self.semente = min_samples_leaf, peso_pos_exp, semente

    def fit(self, X, y):
        base = DecisionTreeClassifier(max_depth=self.max_depth, min_samples_leaf=self.min_samples_leaf,
                                      random_state=self.semente)
        self.m_ = AdaBoostClassifier(estimator=base, n_estimators=self.n_estimators,
                                     learning_rate=self.learning_rate, random_state=self.semente)
        self.m_.fit(X, y, sample_weight=_pesos_positivos(y, self.peso_pos_exp))
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(X)


class Floresta:
    def __init__(self, n_estimators=200, max_depth=10, min_samples_leaf=100, max_features="sqrt", max_samples=0.3,
                 semente=SEMENTE):
        self.n_estimators, self.max_depth, self.min_samples_leaf = n_estimators, max_depth, min_samples_leaf
        self.max_features, self.max_samples, self.semente = max_features, max_samples, semente

    def fit(self, X, y):
        self.m_ = RandomForestClassifier(n_estimators=self.n_estimators, max_depth=self.max_depth,
                                         min_samples_leaf=self.min_samples_leaf, max_features=self.max_features,
                                         max_samples=self.max_samples, class_weight="balanced_subsample",
                                         n_jobs=-1, random_state=self.semente)
        self.m_.fit(X, y)
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(X)


class Boosting:
    def __init__(self, max_depth=4, learning_rate=0.05, max_iter=200, min_samples_leaf=200, l2=1.0,
                 peso_pos_exp=0.5, semente=SEMENTE):
        self.max_depth, self.learning_rate, self.max_iter = max_depth, learning_rate, max_iter
        self.min_samples_leaf, self.l2, self.peso_pos_exp, self.semente = min_samples_leaf, l2, peso_pos_exp, semente

    def fit(self, X, y):
        w = _pesos_positivos(y, self.peso_pos_exp)
        self.m_ = HistGradientBoostingClassifier(max_depth=self.max_depth, learning_rate=self.learning_rate,
                                                 max_iter=self.max_iter, min_samples_leaf=self.min_samples_leaf,
                                                 l2_regularization=self.l2, early_stopping=False,
                                                 random_state=self.semente)
        self.m_.fit(X, y, sample_weight=w)
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(X)


FABRICAS = {"logistica": Logistica, "arvore": Arvore, "floresta": Floresta, "adaboost": AdaBoost,
            "boosting": Boosting}
PADROES = {"logistica": dict(C=0.1, class_weight="balanced"),
           "arvore": dict(max_depth=5, min_samples_leaf=300, peso_pos_exp=0.5),
           "floresta": dict(n_estimators=200, max_depth=10, min_samples_leaf=100, max_features="sqrt", max_samples=0.3),
           "adaboost": dict(n_estimators=200, learning_rate=0.1, max_depth=2, min_samples_leaf=200, peso_pos_exp=0.5),
           "boosting": dict(max_depth=4, learning_rate=0.05, max_iter=200, min_samples_leaf=200, l2=1.0, peso_pos_exp=0.5)}
# o preparo depende do modelo: lineares precisam de log+imputacao+escala; arvores (unica, floresta, AdaBoost) so de
# imputacao, pois sao invariantes a escala; o HistGradientBoosting aceita vazios nativamente
PREP_KW = {"logistica": dict(log=True, escala=True, imputar=True),
           "arvore": dict(log=False, escala=False, imputar=True),
           "floresta": dict(log=False, escala=False, imputar=True),
           "adaboost": dict(log=False, escala=False, imputar=True),
           "boosting": dict(log=False, escala=False, imputar=False)}


# ------------------------------------------------------------------ metricas
def metricas(y, p, qs=(0.01, 0.05)):
    """PR-AUC (principal), ROC-AUC e, para cada fatia q de maior risco em alerta, recall, precisao e
    F1 da classe positiva (media harmonica de recall e precisao nesse corte)."""
    y = np.asarray(y)
    p = np.asarray(p, dtype=float)
    out = {"pr_auc": np.nan, "roc_auc": np.nan, "taxa_base": float(y.mean())}
    for q in qs:
        out[f"recall_top{round(q * 100)}"] = np.nan
        out[f"precisao_top{round(q * 100)}"] = np.nan
        out[f"f1_top{round(q * 100)}"] = np.nan
    if y.sum() == 0 or y.sum() == len(y):
        return out
    out["pr_auc"] = float(average_precision_score(y, p))
    out["roc_auc"] = float(roc_auc_score(y, p))
    ordem = np.argsort(-p, kind="stable")
    for q in qs:
        k = max(int(len(p) * q), 1)
        achados = float(y[ordem[:k]].sum())
        rec, prec = achados / float(y.sum()), achados / k
        out[f"recall_top{round(q * 100)}"] = rec
        out[f"precisao_top{round(q * 100)}"] = prec
        out[f"f1_top{round(q * 100)}"] = 2 * rec * prec / (rec + prec) if rec + prec > 0 else 0.0
    return out


def confusao_topq(y, p, q=0.05):
    """Matriz [[VN, FP], [FN, VP]] alertando os q% de maior risco; devolve tambem o corte usado."""
    y = np.asarray(y)
    corte = np.quantile(p, 1 - q)
    pred = (np.asarray(p) >= corte).astype(int)
    vp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum()); vn = int(((pred == 0) & (y == 0)).sum())
    return np.array([[vn, fp], [fn, vp]]), float(corte)


# ------------------------------------------------------------------ treino e validacao
def construir_X(df, features, alvo, anos_treino, usa_propensao):
    X = df[features].copy()
    if usa_propensao:
        X["propensao_bairro"] = prep.propensao_treino(df, alvo, anos_treino)
    return X


def _ajusta_prediz(df, alvo, features, nome, params, anos_treino, anos_teste, usa_propensao, frac_neg_treino,
                   rng, devolver_treino=False):
    sub = df[df["ano"].isin(list(anos_treino) + list(anos_teste))]
    X = construir_X(sub, features, alvo, list(anos_treino), usa_propensao)
    y = sub[alvo].values
    idx_tr = np.where(sub["ano"].isin(list(anos_treino)).values)[0]
    idx_te = np.where(sub["ano"].isin(list(anos_teste)).values)[0]
    idx_fit = idx_tr
    if frac_neg_treino < 1.0:                                   # acelera a otimizacao: subamostra negativos so no treino
        neg = idx_tr[y[idx_tr] == 0]
        pos = idx_tr[y[idx_tr] == 1]
        neg = rng.choice(neg, size=max(int(len(neg) * frac_neg_treino), 1), replace=False)
        idx_fit = np.sort(np.concatenate([pos, neg]))
    preparador = prep.Preparador(**PREP_KW[nome]).fit(X.iloc[idx_fit])
    est = FABRICAS[nome](**params).fit(preparador.transform(X.iloc[idx_fit]), y[idx_fit])
    p_te = est.predict_proba(preparador.transform(X.iloc[idx_te]))[:, 1]
    saida = {"idx_te": sub.index[idx_te], "p_te": p_te, "y_te": y[idx_te]}
    if devolver_treino:
        p_tr = est.predict_proba(preparador.transform(X.iloc[idx_tr]))[:, 1]
        saida["metricas_treino"] = metricas(y[idx_tr], p_tr)
    return saida


def validar_loyo(df, alvo, features, nome, params=None, usa_propensao=True, anos=None, frac_neg_treino=1.0,
                 calcular_treino=False, semente=SEMENTE):
    """Validacao 'deixa um ano de fora': treina nos demais anos e preve o ano de fora, para cada ano."""
    params = {**PADROES[nome], **(params or {})}
    anos = sorted(df["ano"].unique()) if anos is None else sorted(anos)
    rng = np.random.default_rng(semente)
    partes, por_ano, treino = [], [], []
    for t in anos:
        r = _ajusta_prediz(df, alvo, features, nome, params, [a for a in anos if a != t], [t], usa_propensao,
                           frac_neg_treino, rng, calcular_treino)
        partes.append(pd.DataFrame({"y": r["y_te"], "p": r["p_te"], "ano": t}, index=r["idx_te"]))
        m = metricas(r["y_te"], r["p_te"])
        m.update(ano=t, positivos=int(r["y_te"].sum()))
        por_ano.append(m)
        if calcular_treino:
            mt = r["metricas_treino"]
            mt["ano_teste"] = t
            treino.append(mt)
    oof = pd.concat(partes)
    return {"oof": oof, "global": metricas(oof["y"].values, oof["p"].values),
            "por_ano": pd.DataFrame(por_ano).set_index("ano"),
            "treino": pd.DataFrame(treino) if treino else None, "params": params}


def treinar_testar(df, alvo, features, nome, params, anos_treino, anos_teste, usa_propensao=True, semente=SEMENTE,
                   devolver_treino=False):
    params = {**PADROES[nome], **(params or {})}
    r = _ajusta_prediz(df, alvo, features, nome, params, anos_treino, anos_teste, usa_propensao, 1.0,
                       np.random.default_rng(semente), devolver_treino)
    return metricas(r["y_te"], r["p_te"]), r


def importancia_permutacao(df, alvo, features, nome, params, anos_treino, anos_teste, repeticoes=10,
                           usa_propensao=True, semente=SEMENTE):
    """Importancia por permutacao, fora da amostra: treina em anos_treino e, nos anos_teste, embaralha uma
    variavel de entrada por vez (antes do preparo, como chegaria do sistema) e mede quanto PR-AUC e ROC-AUC caem.
    Variaveis derivadas pelo preparo (ex.: *_nunca) acompanham a variavel original."""
    params = {**PADROES[nome], **(params or {})}
    sub = df[df["ano"].isin(list(anos_treino) + list(anos_teste))]
    X = construir_X(sub, features, alvo, list(anos_treino), usa_propensao)
    y = sub[alvo].values
    tr = sub["ano"].isin(list(anos_treino)).values
    preparador = prep.Preparador(**PREP_KW[nome]).fit(X[tr])
    est = FABRICAS[nome](**params).fit(preparador.transform(X[tr]), y[tr])
    X_te, y_te = X[~tr].reset_index(drop=True), y[~tr]

    def pontua(Xx):
        p = est.predict_proba(preparador.transform(Xx))[:, 1]
        return average_precision_score(y_te, p), roc_auc_score(y_te, p)

    ap0, roc0 = pontua(X_te)
    rng = np.random.default_rng(semente)
    linhas = []
    for c in X_te.columns:
        quedas_ap, quedas_roc = [], []
        for _ in range(repeticoes):
            Xp = X_te.copy()
            Xp[c] = rng.permutation(Xp[c].values)
            ap, roc = pontua(Xp)
            quedas_ap.append(ap0 - ap); quedas_roc.append(roc0 - roc)
        linhas.append({"variavel": c, "queda_pr_auc": np.mean(quedas_ap), "queda_pr_auc_desvio": np.std(quedas_ap),
                       "queda_roc_auc": np.mean(quedas_roc), "queda_roc_auc_desvio": np.std(quedas_roc)})
    tab = pd.DataFrame(linhas).set_index("variavel").sort_values("queda_pr_auc", ascending=False)
    return tab, {"pr_auc": ap0, "roc_auc": roc0}


def validar_estratificado(df, alvo, features, nome, params=None, k=5, semente=SEMENTE):
    """Contraste: k-fold estratificado com linhas embaralhadas (mistura dias do mesmo evento entre treino e teste).
    Sem propensao do bairro: numa divisao aleatoria nao ha como calcula-la sem ler o proprio rotulo."""
    from sklearn.model_selection import StratifiedKFold
    params = {**PADROES[nome], **(params or {})}
    X = df[features].copy()
    y = df[alvo].values
    p = np.zeros(len(df))
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=semente).split(X, y):
        preparador = prep.Preparador(**PREP_KW[nome]).fit(X.iloc[tr])
        est = FABRICAS[nome](**params).fit(preparador.transform(X.iloc[tr]), y[tr])
        p[te] = est.predict_proba(preparador.transform(X.iloc[te]))[:, 1]
    return metricas(y, p), p


def curva_aprendizado(df, alvo, features, nome, params=None, ks=(2, 4, 7), repeticoes=2, usa_propensao=True,
                      semente=SEMENTE):
    """Desempenho (validacao por ano) em funcao do numero de anos usados no treino."""
    params = {**PADROES[nome], **(params or {})}
    anos = sorted(df["ano"].unique())
    rng = np.random.default_rng(semente)
    linhas = []
    for k in ks:
        for rep in range(repeticoes):
            ys, ps = [], []
            for t in anos:
                outros = [a for a in anos if a != t]
                tr = [int(a) for a in rng.choice(outros, size=min(k, len(outros)), replace=False)]
                r = _ajusta_prediz(df, alvo, features, nome, params, tr, [t], usa_propensao, 1.0, rng)
                ys.append(r["y_te"])
                ps.append(r["p_te"])
            linhas.append({"anos_treino": k, "repeticao": rep, **metricas(np.concatenate(ys), np.concatenate(ps))})
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ referencias sem aprendizado e incerteza
def referencias(df, alvo):
    """Criterios sem ML, calculados so com os anos de treino de cada rodada: 'so chuva' e 'chuva x bairro'."""
    faixa = pd.cut(df["chuva_dia_mm"], prep.FAIXAS_CHUVA, labels=False).values
    y = df[alvo].values
    anos = sorted(df["ano"].unique())
    p_cb = np.zeros(len(df))
    for t in anos:
        tr = (df["ano"] != t).values
        te = ~tr
        taxa_faixa = pd.Series(y[tr]).groupby(faixa[tr]).mean()
        prop = prep.tabela_propensao(df, alvo, [a for a in anos if a != t])
        f_te = pd.Series(faixa[te]).map(taxa_faixa).fillna(0).values
        b_te = df.loc[te, "bairro"].map(prop).fillna(prep.PROPENSAO_NEUTRA).values
        p_cb[te] = f_te * b_te
    rng = np.random.default_rng(SEMENTE)                         # ruido minusculo so para desempatar
    return {"referencia: so chuva": df["chuva_dia_mm"].values + rng.random(len(df)) * 1e-6,
            "referencia: chuva x bairro": p_cb + rng.random(len(df)) * 1e-12}


def bootstrap_dias(datas, y, scores, B=200, semente=SEMENTE):
    """Reamostra DIAS inteiros (os eventos se agrupam por tempestade). Devolve PR-AUC e recall@top5% por reamostra."""
    rng = np.random.default_rng(semente)
    idx_por_dia = pd.DataFrame({"d": np.asarray(datas)}).groupby("d").indices
    dias = list(idx_por_dia.keys())
    ap = {n: [] for n in scores}
    rc = {n: [] for n in scores}
    for _ in range(B):
        sel = rng.integers(0, len(dias), len(dias))
        idx = np.concatenate([idx_por_dia[dias[i]] for i in sel])
        yy = y[idx]
        if yy.sum() == 0:
            continue
        k = max(int(len(idx) * 0.05), 1)
        for n, s in scores.items():
            ss = s[idx]
            ap[n].append(average_precision_score(yy, ss))
            rc[n].append(yy[np.argsort(-ss)[:k]].sum() / yy.sum())
    return {n: np.array(v) for n, v in ap.items()}, {n: np.array(v) for n, v in rc.items()}


# ------------------------------------------------------------------ modelo final (o que a API carrega)
class ModeloRisco:
    """Preparador + estimador + tabela de propensao. Recebe um DataFrame com as colunas de 'features' e 'bairro'."""

    def __init__(self, estimador, preparador, features, tabela_propensao, nome, alvo, usa_propensao=True,
                 propensao_desconhecido=prep.PROPENSAO_NEUTRA):
        self.estimador, self.preparador, self.features = estimador, preparador, list(features)
        self.tabela_propensao, self.nome, self.alvo, self.usa_propensao = tabela_propensao, nome, alvo, usa_propensao
        self.propensao_desconhecido = propensao_desconhecido     # bairro fora da tabela (sem historico de eventos)
        self.cortes_ = None                                      # preenchido depois: {"top5": x, "niveis": [c1, c2, c3]}

    def _matriz(self, df):
        X = df[self.features].copy()
        if self.usa_propensao:
            # getattr: modelos salvos antes deste atributo continuam carregando (com o valor neutro antigo)
            padrao = getattr(self, "propensao_desconhecido", prep.PROPENSAO_NEUTRA)
            X["propensao_bairro"] = prep.aplicar_propensao(df, self.tabela_propensao, padrao)
        return self.preparador.transform(X)

    def prever(self, df):
        return self.estimador.predict_proba(self._matriz(df))[:, 1]

    def nivel(self, df):
        return np.digitize(self.prever(df), self.cortes_["niveis"])

    def predict(self, X):
        """Interface esperada pelo MLflow (pyfunc): devolve o risco previsto de cada linha."""
        return self.prever(X)


def ajustar_final(df, alvo, features, nome, params=None, usa_propensao=True):
    params = {**PADROES[nome], **(params or {})}
    anos = sorted(df["ano"].unique())
    X = construir_X(df, features, alvo, anos, usa_propensao)
    preparador = prep.Preparador(**PREP_KW[nome]).fit(X)
    est = FABRICAS[nome](**params).fit(preparador.transform(X), df[alvo].values)
    tabela = prep.tabela_propensao(df, alvo, anos) if usa_propensao else None
    desconhecido = prep.propensao_sem_evento(df, alvo, anos) if usa_propensao else prep.PROPENSAO_NEUTRA
    return ModeloRisco(est, preparador, features, tabela, nome, alvo, usa_propensao, desconhecido)
