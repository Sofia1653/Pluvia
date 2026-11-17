// Teste local da camera e do ultrassom, sem depender de Wi-Fi ou MQTT.

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

WebServer servidor(80);
bool cameraPronta = false;
unsigned long ultimaLeitura = 0;

float medirDistancia() {
    digitalWrite(14, LOW);
    delayMicroseconds(3);
    digitalWrite(14, HIGH);
    delayMicroseconds(10);
    digitalWrite(14, LOW);
    unsigned long duracao = pulseIn(15, HIGH, 30000);
    float distancia = duracao * 0.0343f / 2.0f;
    return duracao && distancia >= 2 && distancia <= 400 ? distancia : -1;
}

bool iniciarCamera() {
    camera_config_t config = {};
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = 5;
    config.pin_d1 = 18;
    config.pin_d2 = 19;
    config.pin_d3 = 21;
    config.pin_d4 = 36;
    config.pin_d5 = 39;
    config.pin_d6 = 34;
    config.pin_d7 = 35;
    config.pin_xclk = 0;
    config.pin_pclk = 22;
    config.pin_vsync = 25;
    config.pin_href = 23;
    config.pin_sccb_sda = 26;
    config.pin_sccb_scl = 27;
    config.pin_pwdn = 32;
    config.pin_reset = -1;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_QVGA;   // 320x240
    config.jpeg_quality = 15;
    config.fb_count = 1;
    config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

    esp_err_t erro = esp_camera_init(&config);
    if (erro != ESP_OK) {
        Serial.printf("ERRO: camera nao iniciou (codigo 0x%x)\n", erro);
        return false;
    }
    Serial.println("Camera iniciada.");
    return true;
}

// Pagina inicial: mostra a foto e um botao para tirar outra.
void paginaInicial() {
    servidor.send(200, "text/html",
        "<html><body style='font-family:sans-serif;text-align:center'>"
        "<h2>Teste da camera e ultrassom - Pluvia</h2>"
        "<p id='distancia'>Medindo...</p>"
        "<img id='foto' src='/foto' style='max-width:100%'><br><br>"
        "<button onclick=\"document.getElementById('foto').src='/foto?t='+Date.now()\">Tirar outra foto</button>"
        "<script>async function medir(){try{document.getElementById('distancia').textContent=await (await fetch('/distancia')).text()}catch(e){document.getElementById('distancia').textContent='Falha de conexao'}} medir();setInterval(medir,2000)</script>"
        "</body></html>");
}

// Tira uma foto e envia para o navegador.
void enviarFoto() {
    if (!cameraPronta) {
        servidor.send(503, "text/plain", "Camera nao iniciou");
        return;
    }
    // A camera guarda a foto tirada logo depois da anterior.
    // Descartamos essa foto "velha" e pegamos uma nova.
    camera_fb_t* velha = esp_camera_fb_get();
    if (velha) esp_camera_fb_return(velha);

    camera_fb_t* foto = esp_camera_fb_get();
    if (!foto) {
        Serial.println("ERRO: falha ao capturar foto.");
        servidor.send(500, "text/plain", "Falha ao capturar foto");
        return;
    }
    Serial.printf("Foto capturada: %u bytes\n", (unsigned)foto->len);
    WiFiClient cliente = servidor.client();
    servidor.setContentLength(foto->len);
    servidor.send(200, "image/jpeg", "");
    cliente.write(foto->buf, foto->len);
    esp_camera_fb_return(foto);
}

void setup() {
    Serial.begin(9600);
    delay(500);
    Serial.println("\n--- Teste da camera e ultrassom ---");
    pinMode(14, OUTPUT);
    pinMode(15, INPUT);
    digitalWrite(14, LOW);
    cameraPronta = iniciarCamera();
    if (!cameraPronta) Serial.println("Confira o cabo da camera e a alimentacao.");

    WiFi.mode(WIFI_AP);
    if (!WiFi.softAP("Pluvia-Teste", "pluvia123")) {
        Serial.println("Falha ao iniciar rede Wi-Fi de teste.");
    }

    servidor.on("/", paginaInicial);
    servidor.on("/foto", enviarFoto);
    servidor.on("/distancia", []() {
        float distancia = medirDistancia();
        servidor.send(200, "text/plain", distancia < 0 ? "Ultrassom sem leitura valida" : "Distancia: " + String(distancia, 1) + " cm");
    });
    servidor.begin();

    Serial.print("Abra no navegador: http://");
    Serial.println(WiFi.softAPIP());
    Serial.println("Rede: Pluvia-Teste | Senha: pluvia123");
}

void loop() {
    servidor.handleClient();
    if (millis() - ultimaLeitura >= 2000) {
        ultimaLeitura = millis();
        float distancia = medirDistancia();
        if (distancia < 0) Serial.println("Ultrassom sem leitura valida (TRIG 14, ECHO 15).");
        else Serial.printf("Distancia: %.1f cm\n", distancia);
    }
}
