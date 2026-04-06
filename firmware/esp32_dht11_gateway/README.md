# ESP32 + DHT11 网关联调说明（GPIO27）

## 1. 硬件连接

- DHT11 VCC -> ESP32 `3V3`
- DHT11 GND -> ESP32 `GND`
- DHT11 DATA -> ESP32 `GPIO27`

## 2. Arduino IDE 配置

- 开发板：`ESP32 Dev Module`（或与你板子等价配置）
- 串口：选择识别出的 COM 口（CH340 驱动）
- 依赖库：
  - `DHT sensor library`（Adafruit，建议 1.4.6）
  - `Adafruit Unified Sensor`（建议 1.1.14）

## 3. 修改固件参数

在 `esp32_dht11_gateway.ino` 顶部修改：

- `WIFI_SSID`
- `WIFI_PASSWORD`
- `SERVER_BASE`：填运行 Flask 的电脑局域网地址，例如 `http://192.168.5.111:5000`
- `DEVICE_SECRET`：设备密钥（需与服务端注册/校验一致）

## 4. 运行顺序

1. 先启动 Flask：`python run.py`
2. 烧录固件并打开串口监视器（115200）
3. 观察日志：
   - WiFi 连接成功
   - `/api/device/register` 返回成功
   - 周期上传温湿度与心跳
4. 打开网页 `监测` 页面查看设备数据曲线

## 5. 常见问题

- `DHT11 读取失败 NaN`：检查线序与供电，降低采样频率
- 连接不上服务器：`SERVER_BASE` 不能写 `127.0.0.1`
- 服务端 403：`device_uid` / `device_secret` 不匹配
