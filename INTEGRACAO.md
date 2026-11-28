# Integração dos embarcados

O ESP32-CAM lê o ultrassom e envia dados ao Mosquitto. O coletor assina os tópicos, valida as mensagens e grava as leituras no PostgreSQL; os JPEGs são salvos no volume compartilhado com o dashboard. A API e o ML têm fluxo próprio: o sensor não é feature do modelo histórico, e `src/alerta.py` ainda espera um CSV que o coletor atual não produz. Não há integração automática entre essa função e o coletor.

## Execução com Docker

1. Copie `.env.example` para `.env` e altere as senhas. Em PowerShell: `Copy-Item .env.example .env`.
2. Execute `docker compose up -d --build` na raiz. Acompanhe com `docker compose logs -f mosquitto postgres coletor`.
3. Abra o dashboard em http://localhost:8501 e a API em http://localhost:8000/docs. A placa deve usar o IP do computador na rede como broker, não `localhost`.
4. Sem placa: `docker compose --profile simulador up -d --build simulador`. O simulador publica distância fixa de 20 cm por padrão. Veja opções com `docker compose run --rm simulador --help`; para foto, use o simulador local conforme `embarcado/README.md`.

O `schema.sql` completo é executado automaticamente apenas na criação de um volume PostgreSQL vazio. Em um banco existente criado pelo esquema completo anterior de integration, aplique `migrations/001_leituras_sensor.sql` com psql. Um banco criado apenas com o esquema reduzido desta branch precisa de migração adicional para as tabelas e views da API/ML. Preserve os dados antes de recriar o volume.

## Contrato MQTT

- `pluvia/<id>/leituras`: JSON UTF-8, por exemplo `{"sensor_id":"PLUVIA_01","distancia_cm":12.5}`. Distância numérica finita entre 2 e 400 cm. O timestamp é atribuído pelo PostgreSQL na recepção; não é o horário medido pela placa.
- `pluvia/<id>/camera`: bytes JPEG, até 2 MiB; o identificador do tópico deve conter apenas letras ASCII, números, `_` ou `-`. O coletor verifica marcadores JPEG, sem decodificar a imagem.
- O firmware atual publica nos tópicos `pluvia/sensor01/...`, mas o `sensor_id` do JSON é `PLUVIA_01`. No dashboard, selecione manualmente a câmera `sensor01` para esse sensor; a associação vale para a sessão. Unificar os identificadores exige planejar a transição do histórico.
- O broker local é anônimo e sem TLS; use apenas em rede controlada.

A conexão MQTT é refeita pelo cliente e as assinaturas são solicitadas novamente em `on_connect`. As mensagens são recebidas em QoS 0; uma interrupção pode causar perda. O coletor registra a falha de banco e segue operando, mas descarta a leitura que falhou. Fotos não são registradas na tabela `fotos_sensor` pelo coletor atual. O estudo para recuperação está em `embarcado/ROBUSTEZ.md`.

O dashboard calcula nível a partir da altura configurada e pode analisar fotos opcionalmente. A previsão por bairro é separada e não usa leituras do sensor. Os limites de alerta precisam de calibração real.
