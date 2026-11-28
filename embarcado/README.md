# Embarcados Pluvia

ESP32-CAM AI Thinker com câmera OV2640 e sensor ultrassônico. O firmware está em `embarcado/firmware`, o coletor em `embarcado/coletor.py` e o simulador em `embarcado/simulador.py`. Para arquitetura, tópicos MQTT e execução integrada, consulte `INTEGRACAO.md` na raiz.

## Executar a infraestrutura

Copie `.env.example` para `.env`, configure as senhas e execute na raiz:

```powershell
docker compose up -d --build
docker compose logs -f coletor
```

O Compose configura `PLUVIA_BROKER` e `PLUVIA_DB_URL`. O coletor exige o banco, grava leituras na tabela `leituras_sensor` e imagens em `data/imagens` no volume compartilhado. Para execução local, instale `embarcado/requirements.txt`, configure as duas variáveis para o broker e o PostgreSQL acessíveis e rode `python embarcado/coletor.py`. A porta MQTT pode ser definida por `PLUVIA_BROKER_PORTA` (padrão 1883).

## Simulador

```powershell
# Na raiz, com a infraestrutura em execução
docker compose --profile simulador up -d --build simulador
# Uma leitura de teste, sem alterar o simulador em execução
docker compose run --rm simulador --sensor demo --distancia 12.5 --quantidade 1
# Localmente, após instalar as dependências e com broker acessível
python embarcado/simulador.py --broker 127.0.0.1 --sensor demo --distancia 12.5 --quantidade 1 --foto caminho/foto.jpg
# Niveis variam automaticamente entre 5 e 30 cm em 60 segundos
python embarcado/simulador.py --broker 127.0.0.1 --sensor demo --variar --minimo 5 --maximo 30 --periodo 60
```

Sem `--quantidade`, publica continuamente; `--intervalo` define o intervalo em segundos, e `--foto` publica um JPEG local a cada 10 segundos. Com `--variar`, a distância oscila entre `--minimo` e `--maximo` durante `--periodo`; sem essa opção ela é fixa. `--help` lista os argumentos. `PLUVIA_ALTURA_CM` não altera os valores do simulador. Para usar o ciclo no Docker: `docker compose run --rm simulador --sensor demo --variar --minimo 5 --maximo 30 --periodo 60`. Pare o serviço contínuo com `docker compose --profile simulador stop simulador`.

## Firmware e montagem

1. Copie `embarcado/firmware/include/secrets.example.h` para `secrets.h` na mesma pasta e preencha Wi-Fi de 2,4 GHz e IP do computador que hospeda o broker. Não use `localhost` na placa.
2. Dentro de `embarcado/firmware`, compile com `pio run -e esp32cam`; para gravar, use `pio run -e esp32cam -t upload`. O monitor serial usa 9600 baud. Para o teste isolado da câmera, use o ambiente `teste-camera`.
3. O código usa TRIG no GPIO14 e ECHO no GPIO15, pinos compartilhados com microSD; não inicializa o cartão. Para HC-SR04 de 5 V, reduza ECHO a 3,3 V com divisor ou conversor, mantenha GND comum e alimentação estável. Confira pinagem e níveis antes de ligar.
4. O firmware publica uma leitura a cada 2 s e JPEG a cada 10 s enquanto conectado. Câmera e ligações precisam ser validadas na placa. Fotos acumulam no disco.

## Testes e material

`python -m unittest embarcado.test_coletor -v` executa os testes unitários. O teste com banco e broker reais é opcional e descrito em `ROBUSTEZ.md`.

- `ROBUSTEZ.md`: limites atuais e proposta de recuperação de leituras.
- `ROTEIRO.md`: preparação e roteiro para demonstração.
- `TEXTO_EMBARCADOS.md`: texto inicial para o trabalho escrito.
- `PLANO_FIRMWARE.md`: reconexão e planejamento de LED RGB e FreeRTOS.
