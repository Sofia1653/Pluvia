
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

// Wi-Fi: usem a mesma rede do computador
const char* WIFI_SSID = "uaifai-tiradentes";
const char* WIFI_SENHA = "bemvindoaocesar";

// IP IPv4 do computador onde roda o Mosquitto
const char* MQTT_BROKER = "172.26.68.103"; 
const int MQTT_PORT = 1883;

const char* TOPICO = "pluvia/sensor01/leituras";

#define TRIG_PIN 5
#define ECHO_PIN 18

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

float medirDistancia() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(3);

    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    unsigned long duracao =
        pulseIn(ECHO_PIN, HIGH, 30000);

    if (duracao == 0) {
        return -1;
    }

    float distancia = duracao * 0.0343f / 2.0f;

    if (distancia < 2 || distancia > 400) {
        return -1;
    }

    return distancia;
}

void conectarWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_SENHA);

    Serial.print("Conectando ao Wi-Fi");

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWi-Fi conectado!");
    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());
}

void conectarMQTT() {
    while (!mqtt.connected()) {
        String clientId = "PluviaESP32-";
        clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

        Serial.print("Conectando ao MQTT... ");

        if (mqtt.connect(clientId.c_str())) {
            Serial.println("conectado!");
        } else {
            Serial.print("falhou. Estado: ");
            Serial.println(mqtt.state());
            delay(3000);
        }
    }
}

void setup() {
    Serial.begin(9600);

    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    digitalWrite(TRIG_PIN, LOW);

    conectarWiFi();

    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setBufferSize(256);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        conectarWiFi();
    }

    if (!mqtt.connected()) {
        conectarMQTT();
    }

    mqtt.loop();

    float distancia = medirDistancia();

    if (distancia >= 0) {
        char mensagem[160];

        snprintf(
            mensagem,
            sizeof(mensagem),
            "{\"sensor_id\":\"PLUVIA_01\","
            "\"distancia_cm\":%.2f}",
            distancia
        );

        bool enviado = mqtt.publish(TOPICO, mensagem);

        Serial.print("Mensagem: ");
        Serial.println(mensagem);

        Serial.println(
            enviado ? "Publicada no MQTT"
                    : "Falha ao publicar"
        );
    } else {
        Serial.println("Leitura invalida do sensor");
    }

    delay(2000);
}
