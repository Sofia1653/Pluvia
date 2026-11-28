# Dashboard PLUVIA

Mostra, a cada 5 segundos, o nível da água medido pelo sensor ultrassônico e as fotos da ESP32-CAM
com a análise da IA (lixo / água acumulada / normal). Lê as medições do PostgreSQL e as fotos gravadas pelo `src/coletor.py`.

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
2. Inicie o PostgreSQL e configure `PLUVIA_DB_URL` nos terminais do coletor e do dashboard, conforme o README da raiz.
3. Coletor: `python src/coletor.py`
4. Dashboard: `streamlit run applications/dashboard/app.py`

O navegador abre sozinho em `http://localhost:8501`.

O seletor de sensor e o intervalo de datas filtram o grafico de leituras. Os indicadores de nivel atual,
tempo desde a ultima leitura e maximo do dia usam o sensor selecionado, independentemente do periodo do
grafico. O dia segue o fuso America/Recife; o nivel maximo usa a menor distancia medida no dia e a altura
configurada na barra lateral. Apos 10 minutos sem leitura, o painel avisa e deixa o status como sem leitura recente.

Fotos usam o identificador do topico MQTT da camera, que pode ser diferente do `sensor_id` das leituras.
Selecione a camera associada ao sensor no painel: por exemplo, para a placa atual selecione `sensor01`
para o sensor `PLUVIA_01`. Quando os nomes coincidem, a camera e selecionada por padrao; caso contrario,
nenhuma e associada ate a escolha manual. A associacao vale para a sessao e deve ser confirmada para cada
sensor. Somente a ultima foto recente da camera associada pode contribuir para o status. Fotos antigas
podem ser exibidas, mas nao alteram o status. Configure os tres limites em ordem crescente.

## Como o status é calculado

- **Nível da água** = altura do sensor até o fundo seco − distância medida. A altura é ajustada na barra lateral.
- **Nível do sensor** (0 a 3) pela fração da altura ocupada pela água: Atenção ≥ 25%, Alerta ≥ 50%, Crítico ≥ 75%.
- **Nível da imagem**: lixo/obstrução = Atenção (1); água acumulada = Alerta (2).
- **Status do ponto** = o maior dos dois. Os níveis 0 a 3 são os mesmos do modelo de risco por bairro.

## Sobre a IA de imagem

Primeira versão: CLIP (`openai/clip-vit-base-patch32`) em modo zero-shot, que compara a foto com descrições
em texto e não precisa de treino. As descrições estão em `classificador.py`. A classe "fora de contexto" evita
alarmes falsos nos testes de bancada (rostos, mesa). Próximo passo (Semana 16): treinar um modelo próprio
com fotos do ponto real.
