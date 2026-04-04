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
2. 复制 `.env.example` 为 `.env`，填写 MySQL 账号与 `SECRET_KEY`。若使用火山方舟：同时填写 **`AI_API_KEY`** 与 **`AI_MODEL`**（控制台推理接入点 ID，形如 `doubao-seed-2-0-pro-xxxxxx`），并执行 `pip install -r requirements.txt` 安装 `requests`。
3. 在 MySQL 中执行 `sql/init.sql`（若报 `user` 表相关错误，请使用仓库内最新脚本：表名已加反引号，默认密码哈希为 pbkdf2）。脚本内含**演示设备与传感数据**，便于无 ESP32 时浏览监测与报告页。
4. 启动：
   ```bash
   python run.py
   ```
5. 浏览器访问 `http://127.0.0.1:5000/`  
   默认账号（执行 init.sql 后）：`admin` / `123456`。

**若登录提示需要 `cryptography` 包**：MySQL 8 默认 `caching_sha2_password` 认证，已写入 `requirements.txt`；执行 `pip install -r requirements.txt` 即可。

## 目录速览

- `app/routes` — 路由层  
- `app/service` — 业务层  
- `app/dao` — 数据访问（仅参数化 SQL）  
- `static/pages` — 前端页面  
- `sql/init.sql` — 建表与初始数据  

## 说明

- 设备网关、历史数据、AI 等接口已为占位实现，按《开发文档.md》逐模块补全即可。
