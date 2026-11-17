# Dashboard PLUVIA

Mostra, a cada 5 segundos, o nível da água medido pelo sensor ultrassônico e as fotos da ESP32-CAM
com análise opcional da IA (lixo / água acumulada / normal). Lê os arquivos que `embarcado/coletor.py` grava.

## Instalar (uma vez)

Na raiz do repositório:

```
pip install -r applications/dashboard/requirements.txt
```

Para a análise das fotos com IA (opcional, cerca de 1 GB de download na primeira vez):

```
pip install -r applications/dashboard/requirements-ia.txt
```

Sem a IA, o dashboard funciona normalmente e mostra só o nível da água e as fotos.

## Rodar

São três janelas de terminal, todas na raiz do repositório:

1. Broker: `docker start mosquitto`
2. Coletor: `python embarcado/coletor.py` (configure `PLUVIA_BROKER` com o endereço do broker)
3. Dashboard: `streamlit run applications/dashboard/app.py`

O navegador abre sozinho em `http://localhost:8501`.

## Como o status é calculado

- **Nível da água** = altura do sensor até o fundo seco − distância medida. A altura é ajustada na barra lateral.
- **Nível do sensor** (0 a 3) pela fração da altura ocupada pela água: Atenção ≥ 25%, Alerta ≥ 50%, Crítico ≥ 75%.
- **Nível da imagem**: lixo/obstrução = Atenção (1); água acumulada = Alerta (2).
- **Status do ponto** = o maior dos dois. Os níveis 0 a 3 são os mesmos do modelo de risco por bairro.
- Este painel ainda não executa o modelo de risco por bairro: a integração com ele fica em `src/alerta.py` e precisa ser chamada com o modelo e os dados de entrada.
- Os percentuais do painel são provisórios e diferem dos limites fixos em centímetros de `src/alerta.py`; ambos precisam ser calibrados. Leituras com mais de 10 minutos não geram status do sensor.
- A análise de imagem é experimental; a pontuação do CLIP não é uma probabilidade de risco calibrada.

## Sobre a IA de imagem

Primeira versão: CLIP (`openai/clip-vit-base-patch32`) em modo zero-shot, que compara a foto com descrições
em texto e não precisa de treino. As descrições estão em `classificador.py`. A classe "fora de contexto" evita
alarmes falsos nos testes de bancada (rostos, mesa). Próximo passo (Semana 16): treinar um modelo próprio
com fotos do ponto real.
