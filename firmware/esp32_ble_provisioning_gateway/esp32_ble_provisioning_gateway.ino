#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
// ESP32 Arduino Core 自带 BLE（ESP32 BLE Arduino）
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "DHT.h"
#include <ArduinoJson.h>

/*
  ESP32 BLE 配网 + 网关注册固件（硬件优化版）
  - BLE 收到 WiFi JSON（ssid/password，可选 server_base/device_secret）
  - 写入 NVS（Preferences）
  - 连接 WiFi 并调用 POST /api/device/register（与你后端一致）
  - 通过 BLE notify 回传进度（便于 Web Bluetooth 页面展示）

  依赖库（Arduino IDE 库管理器）：
  1) ArduinoJson by Benoit Blanchon（建议 7.x）
*/

// ====== BLE UUID（需与 static/pages/ble_setup.html 完全一致）======
static const char* BLE_SERVICE_UUID     = "9b5c0001-3f38-4f4a-9c2f-2b6c2e4b5c01";
static const char* BLE_CHAR_CONFIG_UUID = "9b5c0002-3f38-4f4a-9c2f-2b6c2e4b5c01"; // write
static const char* BLE_CHAR_STATUS_UUID = "9b5c0003-3f38-4f4a-9c2f-2b6c2e4b5c01"; // notify/read

// ====== 设备默认参数（可被 BLE 下发覆盖一部分）======
static const char* DEFAULT_SERVER_BASE = "http://192.168.188.19:5000";
static const char* DEFAULT_DEVICE_SECRET = "esp32-io27-demo-secret";
static const char* DEVICE_NAME_PREFIX = "ESP32-PROV-";
static const char* FIRMWARE_VER = "v0.2.0-ble-prov";
static const unsigned long HEARTBEAT_INTERVAL_MS = 30000;
static unsigned long g_commandPollIntervalMs = 5000;
static const unsigned long DATA_INTERVAL_MS = 10000;
static const int OFFLINE_MAX = 100;
static const int OFFLINE_FLUSH_BATCH = 20;
static const unsigned long OFFLINE_FLUSH_INTERVAL_MS = 15000;
static const int HTTP_TIMEOUT_MS = 12000;
static const int HTTP_RETRY_DELAY_MS = 300;

Preferences prefs;

BLECharacteristic* g_charConfig = nullptr;
BLECharacteristic* g_charStatus = nullptr;
BLEServer* g_server = nullptr;

String g_deviceUid = "";
volatile bool g_bleConnected = false;

// provisioning state
String g_ssid = "";
String g_password = "";
String g_serverBase = "";
String g_deviceSecret = "";
volatile bool g_provTaskRunning = false;
volatile bool g_registered = false;
bool g_sensorEnabled = true;  // 供 sensor_on/off 指令切换（仍然读取真实 DHT11）
unsigned long g_lastHeartbeatMs = 0;
unsigned long g_lastCmdPollMs = 0;
unsigned long g_lastDataMs = 0;
unsigned long g_lastOfflineFlushMs = 0;

// DHT11 接线：DHT DATA -> GPIO27（与你既有硬件一致）
#define DHTPIN 27
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

struct DataSample {
  float temperature;
  float humidity;
};
DataSample g_offlineQueue[OFFLINE_MAX];
int g_offlineHead = 0;
int g_offlineSize = 0;

int offlineCount() {
  return g_offlineSize;
}

void offlinePush(float t, float h) {
  int idx = (g_offlineHead + g_offlineSize) % OFFLINE_MAX;
  if (g_offlineSize >= OFFLINE_MAX) {
    // 队列满时覆盖最旧数据，避免无限增长
    g_offlineHead = (g_offlineHead + 1) % OFFLINE_MAX;
    idx = (g_offlineHead + g_offlineSize - 1) % OFFLINE_MAX;
  } else {
    g_offlineSize++;
  }
  g_offlineQueue[idx].temperature = t;
  g_offlineQueue[idx].humidity = h;
}

bool offlinePopFront(DataSample& out) {
  if (g_offlineSize <= 0) return false;
  out = g_offlineQueue[g_offlineHead];
  g_offlineHead = (g_offlineHead + 1) % OFFLINE_MAX;
  g_offlineSize--;
  return true;
}

String getDeviceUid() {
  uint64_t chipid = ESP.getEfuseMac();
  char buf[32];
  snprintf(buf, sizeof(buf), "ESP32-%04X%08X", (uint16_t)(chipid >> 32), (uint32_t)chipid);
  return String(buf);
}

void bleSendStatusJson(const String& json) {
  if (!g_charStatus) return;
  g_charStatus->setValue(json.c_str());
  if (g_bleConnected) {
    g_charStatus->notify();
  }
  Serial.printf("[BLE][STATUS] %s\n", json.c_str());
}

void bleSendStatus(const char* stage, bool ok, const char* msg) {
  StaticJsonDocument<256> doc;
  doc["stage"] = stage;
  doc["ok"] = ok;
  doc["msg"] = msg;
  doc["device_uid"] = g_deviceUid;
  String out;
  serializeJson(doc, out);
  bleSendStatusJson(out);
}

bool postJson(const String& url, const String& body, String& respText) {
  int finalCode = -1;
  respText = "";
  for (int attempt = 0; attempt < 2; attempt++) {
    WiFiClient client;
    HTTPClient http;
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(body);
    String text = http.getString();
    http.end();

    finalCode = code;
    respText = text;
    Serial.printf("[HTTP] POST %s -> %d (attempt=%d)\n", url.c_str(), code, attempt + 1);
    if (respText.length() > 0) {
      Serial.println(respText);
    }
    if (code == 200) break;

    // 常见瞬时超时（如 -11）做一次短重试，降低偶发丢包影响
    if (attempt == 0 && code < 0) {
      delay(HTTP_RETRY_DELAY_MS);
      continue;
    }
    break;
  }
  return finalCode == 200;
}

bool getText(const String& url, String& respText) {
  int finalCode = -1;
  respText = "";
  for (int attempt = 0; attempt < 2; attempt++) {
    WiFiClient client;
    HTTPClient http;
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.begin(client, url);
    int code = http.GET();
    String text = http.getString();
    http.end();

    finalCode = code;
    respText = text;
    Serial.printf("[HTTP] GET %s -> %d (attempt=%d)\n", url.c_str(), code, attempt + 1);
    if (respText.length() > 0) {
      Serial.println(respText);
    }
    if (code == 200) break;
    if (attempt == 0 && code < 0) {
      delay(HTTP_RETRY_DELAY_MS);
      continue;
    }
    break;
  }
  return finalCode == 200;
}

String jsonEscape(const String& s) {
  String out;
  out.reserve(s.length() + 8);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '\\' || c == '"') {
      out += '\\';
      out += c;
    } else if (c == '\n') {
      out += "\\n";
    } else if (c == '\r') {
      out += "\\r";
    } else {
      out += c;
    }
  }
  return out;
}

bool registerDevice() {
  String base = g_serverBase.length() ? g_serverBase : String(DEFAULT_SERVER_BASE);
  String secret = g_deviceSecret.length() ? g_deviceSecret : String(DEFAULT_DEVICE_SECRET);

  String url = base + "/api/device/register";
  String body = "{";
  body += "\"device_uid\":\"" + g_deviceUid + "\",";
  body += "\"device_secret\":\"" + secret + "\",";
  body += "\"firmware_ver\":\"" + String(FIRMWARE_VER) + "\",";
  body += "\"name\":\"" + String(DEVICE_NAME_PREFIX) + g_deviceUid + "\"";
  body += "}";

  String resp;
  bool ok = postJson(url, body, resp);
  if (!ok) return false;
  // Flask jsonify 可能输出为 "code": 0（带空格），因此两种写法都兼容
  bool regOk = resp.indexOf("\"code\":0") >= 0 || resp.indexOf("\"code\": 0") >= 0;
  g_registered = regOk;
  return regOk;
}

bool sendDataJsonPayload(const String& payloadJson, int& outCount) {
  String base = g_serverBase.length() ? g_serverBase : String(DEFAULT_SERVER_BASE);
  String secret = g_deviceSecret.length() ? g_deviceSecret : String(DEFAULT_DEVICE_SECRET);
  String url = base + "/api/device/data";
  String body = "{";
  body += "\"device_uid\":\"" + g_deviceUid + "\",";
  body += "\"device_secret\":\"" + secret + "\",";
  body += "\"payload\":" + payloadJson;
  body += "}";

  String resp;
  bool ok = postJson(url, body, resp);
  if (!ok) return false;
  if (!(resp.indexOf("\"code\":0") >= 0 || resp.indexOf("\"code\": 0") >= 0)) {
    return false;
  }

  // 解析 count（可选）
  outCount = 0;
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, resp);
  if (!err) {
    outCount = doc["data"]["count"] | 0;
  }
  return true;
}

void sendRealtimeDataOrCache() {
  if (!g_sensorEnabled) return;

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println("DHT11 读取失败（NaN），请检查接线和供电");
    bleSendStatus("data", false, "DHT11 读取失败（NaN）");
    return;
  }
  String payload = "{";
  payload += "\"temperature\":" + String(t, 2) + ",";
  payload += "\"humidity\":" + String(h, 2);
  payload += "}";

  int count = 0;
  bool ok = sendDataJsonPayload(payload, count);
  if (ok) {
    Serial.printf("[DATA] 实时上传成功 T=%.2f H=%.2f\n", t, h);
    return;
  }

  offlinePush(t, h);
  Serial.printf("[DATA] 上传失败，已离线缓存。queue=%d\n", offlineCount());
  bleSendStatus("data", false, ("实时上传失败，已缓存 " + String(offlineCount()) + " 条").c_str());
}

void flushOfflineDataIfNeeded() {
  if (offlineCount() <= 0) return;

  unsigned long now = millis();
  if (now - g_lastOfflineFlushMs < OFFLINE_FLUSH_INTERVAL_MS) return;
  g_lastOfflineFlushMs = now;

  int n = offlineCount() < OFFLINE_FLUSH_BATCH ? offlineCount() : OFFLINE_FLUSH_BATCH;
  String payload = "[";
  for (int i = 0; i < n; i++) {
    int idx = (g_offlineHead + i) % OFFLINE_MAX;
    const DataSample& s = g_offlineQueue[idx];
    if (i > 0) payload += ",";
    payload += "{";
    payload += "\"temperature\":" + String(s.temperature, 2) + ",";
    payload += "\"humidity\":" + String(s.humidity, 2);
    payload += "}";
  }
  payload += "]";

  int count = 0;
  bool ok = sendDataJsonPayload(payload, count);
  if (!ok) {
    Serial.printf("[DATA] 补发失败，queue=%d\n", offlineCount());
    bleSendStatus("data", false, "离线补发失败，稍后重试");
    return;
  }

  for (int i = 0; i < n; i++) {
    DataSample dummy;
    offlinePopFront(dummy);
  }
  Serial.printf("[DATA] 离线补发成功，本次=%d，剩余=%d\n", n, offlineCount());
  bleSendStatus("data", true, ("离线补发成功 " + String(n) + " 条，剩余 " + String(offlineCount()) + " 条").c_str());
}

void sendHeartbeat() {
  String base = g_serverBase.length() ? g_serverBase : String(DEFAULT_SERVER_BASE);
  String secret = g_deviceSecret.length() ? g_deviceSecret : String(DEFAULT_DEVICE_SECRET);

  String url = base + "/api/device/heartbeat";
  String body = "{";
  body += "\"device_uid\":\"" + g_deviceUid + "\",";
  body += "\"device_secret\":\"" + secret + "\"";
  body += "}";
  String resp;
  bool ok = postJson(url, body, resp);
  if (!ok) {
    bleSendStatus("heartbeat", false, "心跳请求失败");
    return;
  }
  bool hbOk = resp.indexOf("\"code\":0") >= 0 || resp.indexOf("\"code\": 0") >= 0;
  bleSendStatus("heartbeat", hbOk, hbOk ? "心跳成功" : "心跳失败（鉴权或服务端错误）");
}

bool ackCommand(long commandId, bool success, const String& resultMsg) {
  String base = g_serverBase.length() ? g_serverBase : String(DEFAULT_SERVER_BASE);
  String secret = g_deviceSecret.length() ? g_deviceSecret : String(DEFAULT_DEVICE_SECRET);

  String url = base + "/api/device/command/ack";
  String body = "{";
  body += "\"device_uid\":\"" + g_deviceUid + "\",";
  body += "\"device_secret\":\"" + secret + "\",";
  body += "\"command_id\":" + String(commandId) + ",";
  body += "\"success\":" + String(success ? "true" : "false") + ",";
  body += "\"result_msg\":\"" + jsonEscape(resultMsg) + "\"";
  body += "}";

  String resp;
  bool ok = postJson(url, body, resp);
  if (!ok) return false;
  return resp.indexOf("\"code\":0") >= 0 || resp.indexOf("\"code\": 0") >= 0;
}

bool executeCommand(const String& commandType, JsonVariant payload, String& resultMsg) {
  if (commandType == "sensor_on") {
    g_sensorEnabled = true;
    resultMsg = "传感功能已开启";
    return true;
  }
  if (commandType == "sensor_off") {
    g_sensorEnabled = false;
    resultMsg = "传感功能已关闭";
    return true;
  }
  if (commandType == "set_interval") {
    int sec = payload["seconds"] | 5;
    if (sec < 2 || sec > 3600) {
      resultMsg = "seconds 越界（2~3600）";
      return false;
    }
    g_commandPollIntervalMs = (unsigned long)sec * 1000UL;
    resultMsg = "轮询间隔已设为 " + String(sec) + " 秒";
    return true;
  }
  if (commandType == "reboot") {
    resultMsg = "即将重启";
    return true;
  }

  resultMsg = "未知指令类型: " + commandType;
  return false;
}

void pollAndExecuteCommand() {
  String base = g_serverBase.length() ? g_serverBase : String(DEFAULT_SERVER_BASE);
  String secret = g_deviceSecret.length() ? g_deviceSecret : String(DEFAULT_DEVICE_SECRET);
  String url = base + "/api/device/command?device_uid=" + g_deviceUid + "&device_secret=" + secret;

  String resp;
  bool ok = getText(url, resp);
  if (!ok) {
    bleSendStatus("command", false, "拉取指令失败（HTTP）");
    return;
  }

  StaticJsonDocument<1024> doc;
  DeserializationError err = deserializeJson(doc, resp);
  if (err) {
    bleSendStatus("command", false, "拉取响应 JSON 解析失败");
    return;
  }

  int code = doc["code"] | -1;
  if (code != 0) {
    bleSendStatus("command", false, "拉取返回非 0");
    return;
  }

  JsonVariant data = doc["data"];
  if (data.isNull()) {
    return;  // 暂无待执行指令
  }

  long commandId = data["id"] | 0;
  String commandType = String((const char*)(data["command_type"] | ""));
  JsonVariant payload = data["payload"];
  if (commandId <= 0 || commandType.length() == 0) {
    bleSendStatus("command", false, "指令字段不完整");
    return;
  }

  bleSendStatus("command", true, ("收到指令 " + commandType + " #" + String(commandId)).c_str());
  String resultMsg;
  bool execOk = executeCommand(commandType, payload, resultMsg);

  bool ackOk = ackCommand(commandId, execOk, resultMsg);
  if (ackOk) {
    bleSendStatus("command", execOk, ("回执成功: " + resultMsg).c_str());
  } else {
    bleSendStatus("command", false, "回执失败（请检查鉴权/后端）");
  }

  if (execOk && commandType == "reboot") {
    delay(300);
    ESP.restart();
  }
}

bool connectWifiOnce() {
  if (g_ssid.length() == 0) {
    bleSendStatus("wifi", false, "未配置 SSID（请先通过 BLE 下发）");
    return false;
  }

  bleSendStatus("wifi", true, "开始连接 WiFi...");
  Serial.printf("连接 WiFi: %s\n", g_ssid.c_str());

  WiFi.mode(WIFI_STA);
  WiFi.begin(g_ssid.c_str(), g_password.c_str());

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 30) {
    delay(500);
    retry++;
    if (retry % 4 == 0) {
      bleSendStatus("wifi", true, "连接中...");
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    StaticJsonDocument<256> doc;
    doc["stage"] = "wifi";
    doc["ok"] = true;
    doc["msg"] = "WiFi 已连接";
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    doc["device_uid"] = g_deviceUid;
    String out;
    serializeJson(doc, out);
    bleSendStatusJson(out);
    return true;
  }

  bleSendStatus("wifi", false, "WiFi 连接失败（请检查 SSID/密码、路由器 2.4G、信号）");
  return false;
}

void provisioningTask(void* param) {
  (void)param;
  g_provTaskRunning = true;

  bleSendStatus("prov", true, "收到配置，写入 NVS 完成，准备连网...");

  if (!connectWifiOnce()) {
    g_provTaskRunning = false;
    vTaskDelete(nullptr);
    return;
  }

  bleSendStatus("register", true, "开始调用 /api/device/register ...");
  bool ok = registerDevice();
  if (ok) {
    bleSendStatus("register", true, "注册/校验成功");
    g_registered = true;
  } else {
    bleSendStatus("register", false, "注册失败（检查 SERVER_BASE、后端是否启动、device_secret 是否一致）");
    g_registered = false;
  }

  g_provTaskRunning = false;
  vTaskDelete(nullptr);
}

void loadFromNvs() {
  prefs.begin("prov", true);
  g_ssid = prefs.getString("ssid", "");
  g_password = prefs.getString("pwd", "");
  g_serverBase = prefs.getString("server", "");
  g_deviceSecret = prefs.getString("secret", "");
  prefs.end();

  if (g_ssid.length()) {
    Serial.printf("[NVS] ssid=%s\n", g_ssid.c_str());
  } else {
    Serial.println("[NVS] 未找到已保存的 WiFi 配置");
  }
}

void saveToNvs() {
  prefs.begin("prov", false);
  prefs.putString("ssid", g_ssid);
  prefs.putString("pwd", g_password);
  prefs.putString("server", g_serverBase);
  prefs.putString("secret", g_deviceSecret);
  prefs.end();
}

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    (void)pServer;
    g_bleConnected = true;
    bleSendStatus("ble", true, "BLE 已连接");
  }
  void onDisconnect(BLEServer* pServer) override {
    (void)pServer;
    g_bleConnected = false;
    Serial.println("[BLE] 断开连接，继续广播");
    BLEDevice::startAdvertising();
  }
};

class ConfigCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    String value = characteristic->getValue();
    if (value.length() == 0) return;

    // 解析 JSON（容量留大一些，避免密码较长时溢出）
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, value);
    if (err) {
      bleSendStatus("prov", false, "JSON 解析失败（请检查格式）");
      return;
    }

    const char* ssid = doc["ssid"] | "";
    const char* password = doc["password"] | "";
    const char* server_base = doc["server_base"] | "";
    const char* device_secret = doc["device_secret"] | "";

    if (ssid[0] == '\0') {
      bleSendStatus("prov", false, "ssid 不能为空");
      return;
    }

    g_ssid = String(ssid);
    g_password = String(password);
    if (server_base[0] != '\0') g_serverBase = String(server_base);
    if (device_secret[0] != '\0') g_deviceSecret = String(device_secret);

    saveToNvs();
    bleSendStatus("prov", true, "配置已保存（NVS）");

    if (!g_provTaskRunning) {
      xTaskCreatePinnedToCore(provisioningTask, "provTask", 8192, nullptr, 1, nullptr, 1);
    } else {
      bleSendStatus("prov", true, "正在处理中，请稍候...");
    }
  }
};

void setupBle() {
  g_deviceUid = getDeviceUid();
  String devName = String(DEVICE_NAME_PREFIX) + g_deviceUid.substring(g_deviceUid.length() - 6);

  BLEDevice::init(devName.c_str());
  g_server = BLEDevice::createServer();
  g_server->setCallbacks(new ServerCallbacks());

  BLEService* service = g_server->createService(BLEUUID(BLE_SERVICE_UUID));

  g_charConfig = service->createCharacteristic(
    BLEUUID(BLE_CHAR_CONFIG_UUID),
    BLECharacteristic::PROPERTY_WRITE
  );
  g_charConfig->setCallbacks(new ConfigCallbacks());

  g_charStatus = service->createCharacteristic(
    BLEUUID(BLE_CHAR_STATUS_UUID),
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
  );
  g_charStatus->addDescriptor(new BLE2902());
  g_charStatus->setValue("{\"stage\":\"boot\",\"ok\":true,\"msg\":\"ready\"}");

  service->start();

  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(BLEUUID(BLE_SERVICE_UUID));
  advertising->setScanResponse(true);
  advertising->setMinPreferred(0x06);
  advertising->setMinPreferred(0x12);

  BLEDevice::startAdvertising();
  Serial.printf("[BLE] Advertising as %s\n", devName.c_str());
}

void setup() {
  Serial.begin(115200);
  delay(800);

  g_deviceUid = getDeviceUid();
  Serial.printf("设备UID: %s\n", g_deviceUid.c_str());

  dht.begin();

  loadFromNvs();
  setupBle();

  // 若已有保存的 WiFi，尝试自动连网 + 注册（不阻塞太久，失败可重新通过 BLE 下发）
  if (g_ssid.length()) {
    bleSendStatus("boot", true, "检测到已保存配置，尝试自动连网...");
    if (!g_provTaskRunning) {
      xTaskCreatePinnedToCore(provisioningTask, "provTask", 8192, nullptr, 1, nullptr, 1);
    }
  } else {
    bleSendStatus("boot", true, "等待 BLE 下发 WiFi 配置...");
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED && g_registered) {
    unsigned long now = millis();
    if (now - g_lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
      sendHeartbeat();
      g_lastHeartbeatMs = now;
    }
    if (now - g_lastCmdPollMs >= g_commandPollIntervalMs) {
      pollAndExecuteCommand();
      g_lastCmdPollMs = now;
    }
    if (now - g_lastDataMs >= DATA_INTERVAL_MS) {
      sendRealtimeDataOrCache();
      g_lastDataMs = now;
    }
    flushOfflineDataIfNeeded();
  }

  // 保持主循环轻量；配网/注册在 task 中执行
  delay(200);
}

