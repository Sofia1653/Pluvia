"""Copia o bootstrap dataset e o dicionario de variaveis para onde os notebooks e o src/ esperam.

Os CSVs sao gerados pelo pipeline de dados (fontes em baixar_dados.py e baixar_local.py) e ficam versionados
na branch main, em csv/. Nas demais branches o .gitignore ignora *.csv, entao este script os traz de la:

    python data/obter_dataset.py

Gera:
    processed/dataset_ml_bairro_dia_completo.csv   bootstrap dataset (bairro x dia, 2014-2021, ~228 mil linhas)
    dicionario_variaveis.csv                       descricao de cada coluna
"""
import hashlib
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = "origin/main"
ARQUIVOS = {
    "csv/dataset_ml_bairro_dia_completo.csv": RAIZ / "processed" / "dataset_ml_bairro_dia_completo.csv",
    "csv/dicionario_variaveis.csv": RAIZ / "dicionario_variaveis.csv",
}


def git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, check=True, capture_output=True).stdout


def main():
    git("fetch", "origin", "main")
    for origem, destino in ARQUIVOS.items():
        conteudo = git("show", f"{ORIGEM}:{origem}")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        print(f"{destino.relative_to(RAIZ)}: {len(conteudo):,} bytes, sha256[:16]={hashlib.sha256(conteudo).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
