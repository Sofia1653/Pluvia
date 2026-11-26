from fastapi.testclient import TestClient
from api.main import app
from io import BytesIO
from PIL import Image

client = TestClient(app)


def test_saude():
    resposta = client.get("/saude")

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["status"] == "ok"
    assert dados["banco"] == "ok"
    assert dados["broker"] == "ok"
    assert dados["mlflow"] == "ok"
    assert dados["modelo"] == "ok"


def test_leituras():
    resposta = client.get("/leituras?limite=5")

    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)
    assert len(resposta.json()) <= 5


def test_leituras_limite_invalido():
    resposta = client.get("/leituras?limite=0")

    assert resposta.status_code == 422


def test_metricas():
    resposta = client.get("/metricas")

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["modelo"] == "risco_alagamento"
    assert dados["alias"] == "campeao"
    assert "pr_auc" in dados["metricas"]
    assert "roc_auc" in dados["metricas"]
    assert "recall_top1" in dados["metricas"]


def test_risco():
    resposta = client.post("/risco", json={
        "bairro": "Aflitos",
        "data": "2014-04-22"
    })

    assert resposta.status_code == 200

    dados = resposta.json()

    assert 0 <= dados["probabilidade"] <= 1
    assert 0 <= dados["nivel_risco"] <= 3
    assert "nivel_agua_cm" in dados
    assert "versao" in dados


def test_risco_bairro_inexistente():
    resposta = client.post("/risco", json={
        "bairro": "BairroInexistente",
        "data": "2014-04-22"
    })

    assert resposta.status_code == 404


def test_risco_bairro_vazio():
    resposta = client.post("/risco", json={
        "bairro": "",
        "data": "2014-04-22"
    })

    assert resposta.status_code == 422


def test_risco_data_invalida():
    resposta = client.post("/risco", json={
        "bairro": "Aflitos",
        "data": "data-invalida"
    })

    assert resposta.status_code == 422


def test_imagem():
    imagem = BytesIO()
    Image.new("RGB", (224, 224), "blue").save(imagem, format="PNG")
    imagem.seek(0)

    resposta = client.post("/imagem", files={
        "arquivo": ("teste.png", imagem, "image/png")
    })

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["classe"] in ["lixo", "agua", "normal", "fora"]
    assert 0 <= dados["confianca"] <= 1
    assert 0 <= dados["nivel_minimo"] <= 3


def test_imagem_formato_invalido():
    resposta = client.post("/imagem", files={
        "arquivo": ("teste.txt", b"teste", "text/plain")
    })

    assert resposta.status_code == 415