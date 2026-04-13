# 基于 Web 的物联网设备管理平台（Flask）

本科毕设项目：**Python 3 + Flask + PyMySQL** 后端，原生 HTML/CSS/JS 前端，MySQL 8.0，ESP32 终端（见 `firmware/` 后续补充）。

## 文档索引（防乱套）

| 文件 | 作用 |
|------|------|
| [开发需求.md](开发需求.md) | 业务范围、与课题对应 |
| [开发文档.md](开发文档.md) | **工程权威**：目录结构、接口路径、库表、检查清单 |

**改接口或改表 → 先改 `开发文档.md` 与 `sql/init.sql`，再写代码。**

## 快速启动

1. 安装 Python 3.10+，创建虚拟环境（推荐）。**请只执行与你系统对应的一节**，不要整段粘贴（Windows 没有 `python3` 命令会报错）。
   - **Windows（PowerShell）** — 若已有 `.venv` 且能 `activate`，可跳过创建，直接 `pip install`：
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - **macOS / Linux**：
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
2. 复制 `.env.example` 为 `.env`，填写 MySQL 账号与 `SECRET_KEY`。若使用火山方舟：同时填写 **`AI_API_KEY`** 与 **`AI_MODEL`**（控制台推理接入点 ID，形如 `doubao-seed-2-0-pro-xxxxxx`），并执行 `pip install -r requirements.txt` 安装 `requests`。云服务器建议补充：
   - `AI_HTTP_TIMEOUT=30~90`
   - `AI_MAX_RETRIES=1`
3. 在 MySQL 中执行 `sql/init.sql`（若报 `user` 表相关错误，请使用仓库内最新脚本：表名已加反引号，默认密码哈希为 pbkdf2）。脚本内含**演示设备与传感数据**，便于无 ESP32 时浏览监测与报告页。
4. 启动：
   ```bash
   python run.py
   ```
5. 浏览器访问 `http://127.0.0.1:5000/`  
   默认账号（执行 init.sql 后）：`admin` / `123456`。

**若登录提示需要 `cryptography` 包**：MySQL 8 默认 `caching_sha2_password` 认证，已写入 `requirements.txt`；执行 `pip install -r requirements.txt` 即可。

### 蓝牙配网（Web Bluetooth）

- 配网页：`http://127.0.0.1:5000/pages/ble_setup.html`（或登录后从导航「蓝牙配网」进入）。**请用 `127.0.0.1` 或 `localhost` 打开本页**：局域网纯 HTTP（如 `http://192.168.x.x:5000`）下，Chrome/Edge 通常不提供 Web Bluetooth。
- 下发给设备的 **`server_base` 须为电脑（或服务器）在局域网/公网可达的 Base URL**（常见为 `http://192.168.x.x:5000`），**勿填 `127.0.0.1` / `localhost`**（在 ESP32 上回环指设备自身，无法访问你的 PC）。
- 从本机回环打开时，点击 **「自动填入局域网地址」** 会调用 **`GET /api/server/lan-hint`**（无需登录）填入建议地址；失败时请对照本机网卡手动填写。协议与 UUID 见 [开发文档.md](开发文档.md) §7.3。
- 下一步生产化方案：改为 **域名 + HTTPS** 统一访问入口（已纳入计划），降低浏览器安全上下文限制导致的环境差异。

### 环境变量残留避坑（重要）

- 现象：你改了 `.env`（例如 `SMTP_SENDER`），服务仍读取旧值（如历史残留 `监控系统`），导致邮件报错。
- 原因：进程环境变量优先级高于 `.env`，且 `python-dotenv` 默认不覆盖同名已存在变量。
- 处理：
  1) 入口已改为 `load_dotenv(override=True)`，优先使用项目 `.env`。
  2) 修改 `.env` 后，必须**彻底重启 Flask 进程**（不能只刷新网页）。

## 目录速览

- `app/routes` — 路由层  
- `app/service` — 业务层  
- `app/dao` — 数据访问（仅参数化 SQL）  
- `static/pages` — 前端页面  
- `sql/init.sql` — 建表与初始数据  

## 说明

- 设备网关 `api/device/*` 已实现注册、心跳、数据上传、拉取指令、回执。
- 新增固件示例：`firmware/esp32_dht11_gateway/esp32_dht11_gateway.ino`（DHT11 接 GPIO27）。
- 新增 BLE 配网固件：`firmware/esp32_ble_provisioning_gateway/esp32_ble_provisioning_gateway.ino`，配合 `static/pages/ble_setup.html`；浏览器与 `server_base` 约定见上文 **「蓝牙配网（Web Bluetooth）」** 与 `开发文档.md` §7.3。
- 真机联调已验证通过：ESP32 + DHT11 可持续上报并在监测页展示曲线。
- 经验提示：DHT11 不建议接 GPIO12（会影响启动/下载稳定），统一推荐 GPIO27。
- 监测告警链路已验证：个人中心配置邮箱/电话，设备管理按设备设置温度阈值；超温触发监测页弹窗与邮件发送，并在监测页显示最近一次邮件告警状态。
- AI 报告支持场景化分析：机房、普通家庭、工厂、自定义；支持报告删除。
- 云上若出现 `/api/ai/analyze` 超时：优先检查 `AI_HTTP_TIMEOUT`、`AI_MAX_RETRIES` 与 gunicorn `-t` 参数是否匹配。
- 前端支持主题切换（默认/卡片/哔哩）与全局动效；监测页支持 24h/3d/7d/30d 快速筛选，AI 报告详情支持弹窗连续浏览。
