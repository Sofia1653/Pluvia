# Plano de LED RGB e tarefas FreeRTOS

O firmware atual roda no `loop` do Arduino, sobre o FreeRTOS do ESP32. A reconexão Wi-Fi é automática, com tentativa adicional a cada 30 s; MQTT tenta imediatamente ao recuperar Wi-Fi e depois a cada 3 s. A medição e a foto só são processadas com MQTT conectado, sem buffer local. A publicação de JPEG e a tentativa de conexão podem bloquear temporariamente as demais atividades.

## LED RGB

Definir primeiro o LED (comum anodo ou catodo), corrente, resistores e placa exata. Levantar GPIOs realmente livres no esquemático da AI Thinker: câmera, flash, TRIG 14, ECHO 15, serial e pinos de boot restringem as opções; não atribuir três GPIOs sem validar inclusive níveis durante boot. Se não houver três pinos adequados, avaliar LED endereçável ou expansor, com circuito e alimentação compatíveis. Proposta: azul durante conexão, amarelo sem MQTT, verde conectado e vermelho em erro de sensor; diferenciar erro de câmera e perda de rede por padrão de piscada. Cores e comportamento precisam de validação na placa.

## Tarefas propostas

- Uma tarefa de aquisição periódica mede o ultrassom e envia resultados a uma fila limitada, sem acessar o cliente MQTT.
- Uma única tarefa de comunicação possui `WiFiClient` e `PubSubClient`, administra reconexão, publica e processa `mqtt.loop`; o cliente não deve ser usado simultaneamente por várias tarefas.
- Uma tarefa de câmera captura periodicamente e entrega apenas um frame por vez, com propriedade clara e liberação garantida após envio. Medir RAM/PSRAM e efeito da transferência antes de separar: o envio grande ainda pode atrasar MQTT.
- Uma tarefa de estado do LED consome um estado compartilhado protegido; não pode afetar o controle de rede.
- Definir prioridades, stack, filas, timeouts, watchdog e tratamento de fila cheia com medições de latência/memória. Validar quedas de Wi-Fi e broker, concorrência, captura e estabilidade por tempo prolongado.

Não foram criadas tarefas ou saídas RGB nesta revisão: os pinos e o circuito não estão definidos, e dividir tarefas sem testar acesso à câmera e rede pode introduzir falhas difíceis de reproduzir.
