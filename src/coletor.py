import csv, json, os
from datetime import datetime
import paho.mqtt.client as mqtt

ARQUIVO = "leituras.csv"
TOPICO = "pluvia/+/leituras"

def on_connect(client, userdata, flags, reason_code, properties):
    print("Conectado ao broker:", reason_code)
    client.subscribe(TOPICO)

def on_message(client, userdata, msg):
    dados = json.loads(msg.payload.decode())
    ts = datetime.now().isoformat(timespec="seconds")
    novo = not os.path.exists(ARQUIVO)
    with open(ARQUIVO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["timestamp", "sensor_id", "distancia_cm"])
        w.writerow([ts, dados["sensor_id"], dados["distancia_cm"]])
    print(ts, dados)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
client.loop_forever()