"""Classificacao das fotos da ESP32-CAM (lixo / agua acumulada / normal).

Usa o CLIP (OpenAI, via Hugging Face) em modo "zero-shot": o modelo compara a foto com
descricoes em texto e escolhe a mais parecida, sem precisar de treino com fotos nossas.
E a primeira versao; o modelo proprio, treinado com fotos do local, esta previsto na Semana 16.

Se torch/transformers nao estiverem instalados, classificar() devolve None e o dashboard
continua funcionando sem a analise de imagem.
"""
from functools import lru_cache

MODELO = "openai/clip-vit-base-patch32"

# classe -> (descricao em ingles para o CLIP, rotulo exibido, nivel minimo de alerta 0-3)
CLASSES = {
    "lixo":   ("a photo of trash and garbage blocking a drain, gutter or canal",
               "Lixo / obstrucao", 1),
    "agua":   ("a photo of a flooded street with high standing water",
               "Agua acumulada", 2),
    "normal": ("a photo of a clean and dry street, drain or canal",
               "Normal", 0),
    "fora":   ("a photo of a person, a face, a room or objects on a desk",
               "Fora de contexto (teste)", 0),
}


@lru_cache(maxsize=1)
def _pipeline():
    try:
        from transformers import pipeline
    except ImportError:
        return None
    return pipeline("zero-shot-image-classification", model=MODELO)


def disponivel():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def classificar(caminho_imagem):
    """Devolve {"classe", "rotulo", "confianca", "nivel_minimo"} ou None se o CLIP nao estiver instalado."""
    clf = _pipeline()
    if clf is None:
        return None
    from PIL import Image
    descricoes = {v[0]: k for k, v in CLASSES.items()}
    with Image.open(caminho_imagem) as img:
        resultado = clf(img.convert("RGB"), candidate_labels=list(descricoes))
    melhor = max(resultado, key=lambda r: r["score"])
    classe = descricoes[melhor["label"]]
    return {"classe": classe, "rotulo": CLASSES[classe][1],
            "confianca": round(float(melhor["score"]), 3), "nivel_minimo": CLASSES[classe][2]}
