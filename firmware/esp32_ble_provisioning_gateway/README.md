# ESP32 BLE 配网固件（Web Bluetooth 对接）

本目录提供一个**真机可用**的 BLE 配网固件，配合网页 `static/pages/ble_setup.html` 使用。

## 1. 功能概览

- ESP32 上电后进入 BLE 广播（设备名形如 `ESP32-PROV-xxxxxx`）
- 浏览器（Windows 桌面 Chrome/Edge）通过 Web Bluetooth 连接
- 网页下发 WiFi JSON（`ssid/password`，可选 `server_base/device_secret`）
- 设备写入 NVS（Preferences）后连接 WiFi
- WiFi 连上后调用后端：`POST /api/device/register`
- 设备通过 BLE notify 回传进度（网页日志会显示）
- 注册成功后固件会定时：
  - `POST /api/device/heartbeat`
  - `POST /api/device/data` 上报数据（读取 DHT11：GPIO27）
  - `GET /api/device/command` 拉取待执行指令
  - `POST /api/device/command/ack` 回执执行结果（状态会从 `pending` 变 `done/fail`）
- 若 `data` 上报失败，会进入离线缓存队列（最多 100 条）；网络恢复后按批次自动补发。

当前演示实现支持指令类型：`reboot`、`set_interval`、`sensor_on`、`sensor_off`。

## 2. Arduino IDE 配置

- 开发板：`ESP32 Dev Module`（或与你板子等价配置）
- 串口：115200
- 依赖库（Arduino IDE 库管理器）：
  - `ArduinoJson`（建议 7.x）
  - `DHT sensor library by Adafruit`（DHT11）
  - `Adafruit Unified Sensor`（依赖项）

## 3. UUID 约定（必须一致）

以下 UUID 在 **固件 + 网页** 必须一致：

- Service UUID：`9b5c0001-3f38-4f4a-9c2f-2b6c2e4b5c01`
- Config（WRITE）Characteristic UUID：`9b5c0002-3f38-4f4a-9c2f-2b6c2e4b5c01`
- Status（READ/NOTIFY）Characteristic UUID：`9b5c0003-3f38-4f4a-9c2f-2b6c2e4b5c01`

## 4. 下发 JSON 格式

网页写入 Config 特征值的内容为 UTF-8 JSON：

```json
{
  "ssid": "Lab_IoT",
  "password": "12345678",
  "server_base": "http://192.168.188.19:5000",
  "device_secret": "esp32-ble-demo-secret"
}
```

- `ssid`：必填
- `password`：可为空（开放网络）；一般建议填写
- `server_base`：可选，不填则固件使用默认值（在 `.ino` 顶部 `DEFAULT_SERVER_BASE`）
- `device_secret`：可选，不填则固件使用默认值（在 `.ino` 顶部 `DEFAULT_DEVICE_SECRET`）

> 注意：如果你的后端数据库里已存在同一 `device_uid` 的旧记录且密钥不同，会导致 403。可删除旧记录或把密钥改一致再联调。

## 5. Web Bluetooth 使用限制

- 需要 **Windows 桌面 Chrome/Edge**
- 页面需要在 **HTTPS 或 localhost**（安全上下文）下运行
- 手机浏览器多数不支持/限制 Web Bluetooth（答辩演示建议使用电脑）

## 6. 常见问题

- **扫描不到设备**
  - Windows 蓝牙未打开 / 权限未授予
  - ESP32 未在广播（重启板子、靠近电脑）
  - 设备选择框太多：本实现按 Service UUID 过滤，通常更容易定位
- **能连接但下发后没回执**
  - 检查网页是否已订阅 notify（已在 `ble_setup.html` 实现）
  - 串口查看是否 JSON 解析失败（ArduinoJson 未安装、或 JSON 格式错误）
- **register 失败**
  - `server_base` 写错（不能用 127.0.0.1，应填运行 Flask 的电脑局域网 IP）
  - 后端未启动
- `device_secret` 与后端记录不一致导致 403
