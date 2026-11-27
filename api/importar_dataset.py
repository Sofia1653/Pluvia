import os
import pandas as pd
from sqlalchemy import create_engine, inspect, text

url = os.environ["PLUVIA_DB_URL"]
url = url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(url)

if inspect(engine).has_table("dataset_historico"):
    print("Dataset historico ja importado.")
else:
    df = pd.read_csv("csv/dataset_ml_bairro_dia_completo.csv")
    df["data"] = pd.to_datetime(df["data"]).dt.date

    with engine.begin() as conexao:
        df.to_sql(
            "dataset_historico",
            conexao,
            if_exists="fail",
            index=False,
            chunksize=1000
        )

        conexao.execute(text("""
            CREATE INDEX idx_dataset_bairro_data
            ON dataset_historico (LOWER(bairro), data)
        """))

    print(f"{len(df)} registros importados com sucesso.")