# PLUVIA — sistema embarcado (Grupo 2)

O PLUVIA estima o risco de alagamento em pontos críticos do Recife cruzando chuva, maré e histórico de
ocorrências com um modelo de Machine Learning. Este repositório tem a parte embarcada: uma ESP32-CAM com
sensor ultrassônico e câmera que mede o nível da água e fotografa o ponto, enviando tudo por MQTT, mais o
coletor e o dashboard. O modelo de risco por bairro fica em [pluvia-ml](https://github.com/ninahffbs/pluvia-ml).

![Arquitetura](docs/arquitetura_pluvia.png)

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `platformio.ini`, `src/main.cpp` | Firmware da ESP32-CAM (sensor + câmera + MQTT) |
| `src/teste_camera.cpp` | Teste isolado da câmera (foto no navegador, sem MQTT) |
| `include/secrets.example.h` | Modelo de configuração de rede (copiar para `secrets.h`, que não vai para o Git) |
| `src/coletor.py` | Assina o broker e salva leituras no PostgreSQL e fotos em `data/imagens/` |
| `applications/dashboard/` | Dashboard Streamlit com nível da água e análise das fotos por IA |
| `schematics/` | Esquemático das ligações |
| `docs/` | Guia de montagem, gravação e solução de problemas; diagrama da arquitetura |
| `test/test_coletor.py` | Testes do coletor |

## Como rodar

1. Crie `include/secrets.h` a partir do exemplo, com a rede Wi-Fi (2,4 GHz) e o IP do computador do broker.
2. Grave o firmware com o PlatformIO (ambiente `esp32cam`; veja o passo a passo em `docs/guia_montagem.md`).
3. Broker: `docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto mosquitto -c /mosquitto-no-auth.conf`
   (depois, só `docker start mosquitto`). No Windows, libere a porta 1883 no firewall (comando no guia).
4. Banco: copie `.env.example` para `.env`, escolha uma senha e execute `docker compose up -d postgres`.
   A tabela e criada automaticamente na primeira inicializacao do volume.
5. Instale as dependencias com `pip install -r requirements.txt`. Configure `PLUVIA_DB_URL`
   para `postgresql://pluvia:SENHA@localhost:5432/pluvia`, usando a senha escolhida (caracteres especiais
   na URL devem ser codificados). No PowerShell: `$env:PLUVIA_DB_URL = 'postgresql://pluvia:SENHA@localhost:5432/pluvia'`.
6. Coletor: `python src/coletor.py` (outro computador: defina `PLUVIA_BROKER` com o IP dele).
7. Dashboard: `pip install -r applications/dashboard/requirements.txt`, configure a mesma `PLUVIA_DB_URL` no terminal e execute
   `streamlit run applications/dashboard/app.py`.

As leituras novas ficam no banco; o CSV antigo nao e importado automaticamente. As imagens continuam em disco.
Se o banco ficar indisponivel, a leitura que falhar sera informada no log e nao sera reenviada; o coletor
continua tentando salvar as proximas mensagens. Para testar: `python -m unittest discover -s test -v`.

## Tópicos MQTT

| Tópico | Publica | Assina | Conteúdo |
|---|---|---|---|
| `pluvia/sensor01/leituras` | ESP32-CAM | coletor | JSON `{"sensor_id":"PLUVIA_01","distancia_cm":12.34}` a cada 2 s |
| `pluvia/sensor01/camera` | ESP32-CAM | coletor | JPEG 320×240 (≈3–5 KB) a cada 10 s |

## Integrantes

Beatriz Victória Costa Pinto · Gabrielle Mastellari Velozo · Júlio César Aragão Vilas Bôas ·
Sofia Gomes Tenório · Nina Henrique França Fernandes Bento de Sá · Thiago Vinnícius de Vasconcelos Brayner ·
Maria Cláudia Rodrigues Corrêa de Oliveira Andrade
