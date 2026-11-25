"""Simulador do sensor: publica no MQTT o mesmo que a ESP32-CAM, para testes e plano B da apresentacao.

- A cada --intervalo segundos: {"sensor_id": ..., "distancia_cm": ...} em pluvia/<sensor>/leituras.
  O nivel da agua sobe e desce em ciclos de --ciclo segundos (de seco ate ~80% da altura), simulando uma chuva.
- Opcional (--fotos <pasta>): a cada 10 s publica um JPEG da pasta em pluvia/<sensor>/camera.

Uso:  python embarcado/simulador.py --broker localhost
      docker compose --profile simulador up simulador
"""
import argparse
import itertools
import json
import math
import os
import random
import time
from pathlib import Path

import paho.mqtt.client as mqtt


def distancia_simulada(t, altura_cm, ciclo_s):
    """Distancia do sensor ate a agua no instante t: nivel = 0,8 * altura * sen^2, com ruido de 0,5 cm."""
    nivel = 0.8 * altura_cm * math.sin(math.pi * (t % ciclo_s) / ciclo_s) ** 2
    return min(max(altura_cm - nivel + random.gauss(0, 0.5), 2.0), 400.0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--broker", default=os.environ.get("PLUVIA_BROKER", "localhost"))
    p.add_argument("--porta", type=int, default=1883)
    p.add_argument("--sensor", default=os.environ.get("PLUVIA_SENSOR", "sensor01"))
    p.add_argument("--altura", type=float, default=float(os.environ.get("PLUVIA_ALTURA_CM", 30)),
                   help="altura de montagem do sensor (cm)")
    p.add_argument("--intervalo", type=float, default=2.0)
    p.add_argument("--ciclo", type=float, default=300.0, help="duracao de um ciclo de cheia (s)")
    p.add_argument("--fotos", default=os.environ.get("PLUVIA_FOTOS_SIM"), help="pasta com .jpg para publicar")
    a = p.parse_args()

    fotos = sorted(Path(a.fotos).glob("*.jpg")) if a.fotos else []
    fila_fotos = itertools.cycle(fotos) if fotos else None

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"simulador-{a.sensor}")
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(a.broker, a.porta)
    client.loop_start()
    print(f"Simulando {a.sensor} em {a.broker}:{a.porta} (altura {a.altura} cm, {len(fotos)} fotos).")

    inicio, ultima_foto = time.time(), 0.0
    try:
        while True:
            agora = time.time()
            leitura = {"sensor_id": a.sensor, "distancia_cm": round(distancia_simulada(agora - inicio, a.altura, a.ciclo), 2)}
            client.publish(f"pluvia/{a.sensor}/leituras", json.dumps(leitura))
            print("publicado", leitura, flush=True)
            if fila_fotos and agora - ultima_foto >= 10:
                client.publish(f"pluvia/{a.sensor}/camera", next(fila_fotos).read_bytes())
                ultima_foto = agora
            time.sleep(a.intervalo)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
