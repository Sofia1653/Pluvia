# Guia da ESP32-CAM — montagem, gravação e problemas comuns

Testado de 27/10 a 10/11/2026. Esquemático: `schematics/esquematico_pluvia.png`.

## Montagem

- **Conversor FTDI (YP-05)** com o jumper de tensão em **5V**. RX → U0T da ESP (branco), TX → U0R (roxo),
  GND → GND da ESP ao lado do IO0 (cinza), VCC → linha 10 da protoboard (azul). DTR e CTS vazios.
- **5 V compartilhado** numa linha do meio da protoboard (linha 10, furos a–c), com **3 jumpers macho-fêmea
  inteiros, sem emendas**: VCC do conversor, 5V da ESP e Vcc do sensor. Emendas e a fileira lateral derrubam
  a tensão e causam *brownout* quando a câmera e o Wi-Fi ligam.
- **HC-SR04**: Trig → IO14; Echo → divisor de tensão → IO15; Gnd → GND comum. Não confie nas cores sem verificar as conexões.
  O sensor precisa de 5 V: no pino VCC da ESP (3,3 V) ele dá "leitura inválida" o tempo todo.
- O pino **VCC** da ESP fica **vazio** (é saída, não entrada). O **cartão microSD fica fora** (usa IO14/IO15).
- Divisor necessário: Echo → resistor de 1 kΩ → IO15, e deste ponto resistor de 2 kΩ → GND. Um resistor em série sozinho não reduz o sinal de 5 V a 3,3 V.

## Gravar o firmware

1. Abra no VS Code a pasta que contém o `platformio.ini` (não a pasta de cima).
2. Escolha o ambiente na barra azul: `env:esp32cam` (projeto) ou `env:teste-camera` (só a câmera).
3. Com o USB desconectado, ligue **IO0** ao **GND comum**, preservando as demais ligações de terra. Confirme os rótulos dos pinos e o esquema da sua placa antes de conectar.
4. Feche o Serial Monitor, conecte o USB (empurre o mini-USB até o fim) e clique em Upload.
5. Aperte o RST só se o `Connecting...` ficar parado por vários segundos.
6. Depois do `SUCCESS`: desconecte o USB, tire o jumper do IO0 e conecte novamente.

## Rede, broker e coletor (em qualquer computador)

1. **Uma vez por computador**, no PowerShell como administrador:
   `New-NetFirewallRule -DisplayName "Pluvia MQTT 1883" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow -Profile Any`
2. `ipconfig` → IPv4 do Wi-Fi → colocar em `MQTT_BROKER` no `include/secrets.h`, junto com o nome e a senha
   da rede (2,4 GHz). Gravar a ESP de novo.
3. `docker start mosquitto` (na primeira vez, `docker run`, ver README) e conferir com `docker ps`.
4. `$env:PLUVIA_BROKER = "<IPv4>"` e `python src/coletor.py`.
5. Na faculdade, se continuar `-2` com o firewall liberado, a rede está isolando os aparelhos: usar o roteador
   do celular em 2,4 GHz e repetir os passos 2 a 4.

## Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `Falha MQTT: estado -2` / `-4` | Firewall do Windows bloqueando a porta 1883, IP errado ou broker parado | Regra de firewall, `ipconfig`, `docker ps` |
| `Wi-Fi desconectado` sem parar | `secrets.h` com outra rede | Conferir SSID e senha, regravar |
| `Brownout detector was triggered` | Queda de tensão quando câmera e Wi-Fi ligam | 5 V sem emendas; USB direto no notebook |
| "Ultrassom sem leitura válida" o tempo todo | Sensor em 3,3 V ou microSD encaixado | Sensor no 5 V; tirar o cartão |
| `Failed to connect to ESP32` | IO0 fora de um GND de verdade, ou RST na hora errada | GND ao lado do 5V; RST só se travar |
| ESP muito quente | Wi-Fi e câmera ligados sem parar | Firmware já reduz a CPU para 160 MHz e economiza Wi-Fi; morna é normal |
| Barra do PlatformIO some | Pasta errada aberta no VS Code | Abrir a pasta que tem o `platformio.ini` |
| Foto mostra o momento anterior | Câmera guarda a imagem anterior | Firmware descarta a foto antiga antes de capturar |
