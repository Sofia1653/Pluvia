# Dashboard PLUVIA (dados simulados)

Dashboard Streamlit com as telas exigidas pela especificação do projeto. **Todos os dados são simulados** por
`mock_api.py`, cujas funções imitam os endpoints planejados da API de inferência.

## Executar

A partir da raiz do repositório:

```bash
pip install -r app/requirements.txt
streamlit run app/app.py
```

Abra http://localhost:8501.

## Telas

| Aba | Conteúdo | Requisito do PDF |
|---|---|---|
| Indicadores (topo) | Nível da água, alerta do sensor, chuva, bairros em risco alto, saúde dos serviços | Indicadores relevantes |
| Sensor em tempo real | Série do nível da água com faixas de alerta, chuva e últimas mensagens MQTT | Consumo de dados da aquisição |
| Previsões por bairro | Mapa e ranking de risco, com o alerta combinado modelo × sensor (`src/alerta.py`) | Previsões do modelo |
| Métricas do modelo | Comparação dos modelos, PR-AUC por ano e versão registrada no MLflow | Visualização de métricas |
| Monitoramento | Estado dos serviços, idade da última mensagem por sensor e execuções da DAG | Monitoramento em tempo de execução |

Com a atualização automática ligada, a página atualiza a cada 5 s.

## Trocar os dados simulados pela API

Cada função de `mock_api.py` tem na docstring o endpoint que vai substituí-la (ex.: `previsoes()` → `GET /previsoes`).
Quando a API existir, troque o corpo de cada função por uma chamada HTTP que devolva um `DataFrame` com as
mesmas colunas; `app.py` não precisa mudar.
