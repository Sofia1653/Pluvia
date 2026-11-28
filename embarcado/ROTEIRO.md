# Roteiro de demonstração

## Preparação

- Configurar `.env`, iniciar Docker e executar `docker compose up -d --build`; confirmar os logs de Mosquitto, PostgreSQL e coletor. Abrir dashboard e documentação da API.
- Se houver placa, configurar `secrets.h`, conferir alimentação, divisor do ECHO, Wi-Fi e IP do broker; acompanhar o monitor serial a 9600 baud. Não assumir que a montagem física foi validada.
- Plano sem placa: `docker compose --profile simulador up -d --build simulador`. Para uma leitura pontual: `docker compose run --rm simulador --sensor demo --distancia 12.5 --quantidade 1`. Para testar foto, executar o simulador local com `--foto` e JPEG de teste.

## Apresentação

1. Apresentar o caminho ultrassom/câmera → ESP32 → tópicos MQTT → Mosquitto → coletor → banco/fotos → dashboard. Explicar que a previsão histórica do ML é separada.
2. Mostrar no serial ou simulador uma leitura e no dashboard selecionar o sensor correspondente. Ajustar a altura e explicar que o nível é altura menos distância. Com placa, aproximar um objeto do sensor e observar a mudança.
3. Mostrar a foto no dashboard, quando disponível. O firmware usa `sensor01` no tópico e `PLUVIA_01` na leitura: selecionar manualmente a câmera `sensor01` para esse sensor. A associação vale para a sessão.
4. Mostrar uma mensagem inválida no teste automatizado e explicar que ela é descartada. Explicar a retomada de conexão e deixar claro que mensagens perdidas durante a falha não são recuperadas nesta versão.
5. Mostrar a documentação da API/ML sem afirmar que o sensor alimenta o modelo. Encerrar com limitações e próximos passos: calibração, fila persistente, testes de falha reais e validação do circuito.

Para evitar interferir em dados reais, faça testes de interrupção apenas em ambiente de teste isolado. Após a demonstração, `docker compose --profile simulador stop simulador` interrompe somente o simulador.
