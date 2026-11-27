"""Publica leituras e, opcionalmente, uma foto JPEG nos topicos da ESP32."""
import argparse
import json
import math
import os
import re
import time
from pathlib import Path

import paho.mqtt.client as mqtt


def publicar_leitura(client, sensor, distancia):
    payload = json.dumps({"sensor_id": sensor, "distancia_cm": distancia})
    resultado = client.publish(f"pluvia/{sensor}/leituras", payload, qos=1)
    resultado.wait_for_publish(timeout=5)
    if not resultado.is_published():
        raise RuntimeError("Nao foi possivel publicar a leitura")


def publicar_foto(client, sensor, foto):
    resultado = client.publish(f"pluvia/{sensor}/camera", foto, qos=1)
    resultado.wait_for_publish(timeout=5)
    if not resultado.is_published():
        raise RuntimeError("Nao foi possivel publicar a foto")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default=os.environ.get("PLUVIA_BROKER", "127.0.0.1"))
    parser.add_argument("--porta", type=int, default=int(os.environ.get("PLUVIA_BROKER_PORTA", "1883")))
    parser.add_argument("--sensor", default="simulador01")
    parser.add_argument("--distancia", type=float, default=20.0, help="Distancia simulada em centimetros (2 a 400)")
    parser.add_argument("--intervalo", type=float, default=2.0, help="Segundos entre leituras")
    parser.add_argument("--quantidade", type=int, default=0, help="Numero de leituras; 0 publica ate Ctrl+C")
    parser.add_argument("--foto", type=Path, help="JPEG a publicar a cada 10 segundos")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.sensor):
        parser.error("sensor deve conter apenas letras, numeros, _ ou -")
    if not math.isfinite(args.distancia) or not 2 <= args.distancia <= 400:
        parser.error("distancia deve estar entre 2 e 400 cm")
    if not math.isfinite(args.intervalo) or args.intervalo <= 0 or args.quantidade < 0:
        parser.error("intervalo deve ser positivo e quantidade nao pode ser negativa")
    foto = None
    if args.foto:
        try:
            foto = args.foto.read_bytes()
        except OSError as erro:
            parser.error(f"nao foi possivel ler a foto: {erro}")
        if len(foto) > 2 * 1024 * 1024 or not (foto.startswith(b"\xff\xd8") and foto.endswith(b"\xff\xd9")):
            parser.error("a foto deve ser JPEG e ter no maximo 2 MB")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(args.broker, args.porta, 60)
        client.loop_start()
        proxima_foto = 0.0
        enviadas = 0
        while not args.quantidade or enviadas < args.quantidade:
            publicar_leitura(client, args.sensor, args.distancia)
            print(f"Leitura publicada: {args.sensor} - {args.distancia} cm", flush=True)
            enviadas += 1
            if foto is not None and time.monotonic() >= proxima_foto:
                publicar_foto(client, args.sensor, foto)
                print(f"Foto publicada: {len(foto)} bytes", flush=True)
                proxima_foto = time.monotonic() + 10
            if not args.quantidade or enviadas < args.quantidade:
                time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("Simulador encerrado.")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
