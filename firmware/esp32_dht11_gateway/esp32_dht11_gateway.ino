#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

/*
  ESP32-WROOM-32 + DHT11 最小网关联调固件
  - 传感器数据脚：GPIO27（你当前接线）
  - 每 10 秒上报温湿度到 Flask /api/device/data
  - 每 30 秒发送心跳 /api/device/heartbeat
  - 上电先调用 /api/device/register

  依赖库（Arduino IDE 库管理器）：
  1) DHT sensor library by Adafruit（建议 1.4.6）
  2) Adafruit Unified Sensor（建议 1.1.14）
*/

// ====== 1. 请先修改这里 ======
const char* WIFI_SSID = "Ace";
const char* WIFI_PASSWORD = "miku520a";
// 注意：不要填 127.0.0.1。应填写运行 Flask 的电脑局域网 IP。
const char* SERVER_BASE = "http://192.168.188.19:5000";
const char* DEVICE_SECRET = "esp32-io27-demo-secret";
const char* DEVICE_NAME = "ESP32-DHT11-IO27";
const char* FIRMWARE_VER = "v0.1.0";
// ===========================

#define DHTPIN 27
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);
String g_device_uid = "";
unsigned long lastDataMs = 0;
unsigned long lastHeartbeatMs = 0;

String getDeviceUid() {
  uint64_t chipid = ESP.getEfuseMac();
  char buf[32];
  snprintf(buf, sizeof(buf), "ESP32-%04X%08X", (uint16_t)(chipid >> 32), (uint32_t)chipid);
  return String(buf);
}

bool postJson(const String& url, const String& body, String& respText) {
  WiFiClient client;
  HTTPClient http;
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  respText = http.getString();
  Serial.printf("[HTTP] POST %s -> %d\n", url.c_str(), code);
  if (respText.length() > 0) {
    Serial.println(respText);
  }
  http.end();
  return code == 200;
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("连接 WiFi: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 30) {
    delay(500);
    Serial.print(".");
    retry++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi 已连接，IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi 连接失败，稍后重试");
  }
}

bool registerDevice() {
  String url = String(SERVER_BASE) + "/api/device/register";
  String body = "{";
  body += "\"device_uid\":\"" + g_device_uid + "\",";
  body += "\"device_secret\":\"" + String(DEVICE_SECRET) + "\",";
  body += "\"firmware_ver\":\"" + String(FIRMWARE_VER) + "\",";
  body += "\"name\":\"" + String(DEVICE_NAME) + "\"";
  body += "}";

  String resp;
  bool ok = postJson(url, body, resp);
  if (!ok) return false;
  // Flask jsonify 可能输出为 "code": 0（带空格），因此两种写法都兼容
  return resp.indexOf("\"code\":0") >= 0 || resp.indexOf("\"code\": 0") >= 0;
}

void sendHeartbeat() {
  String url = String(SERVER_BASE) + "/api/device/heartbeat";
  String body = "{";
  body += "\"device_uid\":\"" + g_device_uid + "\",";
  body += "\"device_secret\":\"" + String(DEVICE_SECRET) + "\"";
  body += "}";
  String resp;
  postJson(url, body, resp);
}

void sendData() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println("DHT11 读取失败（NaN），请检查接线和供电");
    return;
  }

  String url = String(SERVER_BASE) + "/api/device/data";
  String body = "{";
  body += "\"device_uid\":\"" + g_device_uid + "\",";
  body += "\"device_secret\":\"" + String(DEVICE_SECRET) + "\",";
  body += "\"payload\":{";
  body += "\"temperature\":" + String(t, 2) + ",";
  body += "\"humidity\":" + String(h, 2);
  body += "}}";

  Serial.printf("上传数据: T=%.2f H=%.2f\n", t, h);
  String resp;
  postJson(url, body, resp);
}

void setup() {
  Serial.begin(115200);
  delay(800);
  dht.begin();
  g_device_uid = getDeviceUid();
  Serial.printf("设备UID: %s\n", g_device_uid.c_str());

  ensureWifi();
  if (WiFi.status() == WL_CONNECTED) {
    if (registerDevice()) {
      Serial.println("设备注册/校验成功");
    } else {
      Serial.println("设备注册失败，请检查服务端与参数");
    }
  }
}

void loop() {
  ensureWifi();
  if (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    return;
  }

  unsigned long now = millis();
  if (now - lastDataMs >= 10000) {
    sendData();
    lastDataMs = now;
  }
  if (now - lastHeartbeatMs >= 30000) {
    sendHeartbeat();
    lastHeartbeatMs = now;
  }
  delay(100);
}
