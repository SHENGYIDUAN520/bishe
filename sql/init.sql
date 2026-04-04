-- 物联网设备管理平台 — MySQL 8.0 初始化脚本
-- 字符集与引擎约定：utf8mb4 + InnoDB（与《开发文档.md》一致）

CREATE DATABASE IF NOT EXISTS iot_platform
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE iot_platform;

-- ----------------------------
-- 用户表
-- ----------------------------
DROP TABLE IF EXISTS ai_report;
DROP TABLE IF EXISTS operation_log;
DROP TABLE IF EXISTS command_log;
DROP TABLE IF EXISTS device_data;
DROP TABLE IF EXISTS device;
DROP TABLE IF EXISTS `user`;

-- 表名 user 为 MySQL 保留相关关键字，必须反引号；避免客户端解析异常
CREATE TABLE `user` (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  username      VARCHAR(64)     NOT NULL COMMENT '登录名',
  password_hash VARCHAR(512)    NOT NULL COMMENT '密码哈希（Werkzeug scrypt/pbkdf2 等可能较长）',
  nickname      VARCHAR(128)    NULL     COMMENT '昵称',
  phone         VARCHAR(20)     NULL     COMMENT '手机号',
  email         VARCHAR(128)    NULL     COMMENT '邮箱',
  status        TINYINT         NOT NULL DEFAULT 1 COMMENT '1正常 0禁用',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户表';

-- ----------------------------
-- 设备表
-- ----------------------------
CREATE TABLE device (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  device_uid      VARCHAR(64)     NOT NULL COMMENT '设备唯一标识如MAC',
  device_secret   VARCHAR(128)    NOT NULL COMMENT '设备密钥（毕设演示可用明文，生产应加密存储）',
  user_id         BIGINT UNSIGNED NULL     COMMENT '绑定用户，未绑定为NULL',
  name            VARCHAR(128)    NULL     COMMENT '设备名称',
  status          TINYINT         NOT NULL DEFAULT 1 COMMENT '1正常 0停用',
  last_heartbeat  DATETIME        NULL     COMMENT '最后心跳时间',
  firmware_ver    VARCHAR(32)     NULL     COMMENT '固件版本',
  created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_device_uid (device_uid),
  KEY idx_device_user (user_id),
  CONSTRAINT fk_device_user FOREIGN KEY (user_id) REFERENCES `user` (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='设备表';

-- ----------------------------
-- 设备传感数据表
-- ----------------------------
CREATE TABLE device_data (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  device_id    BIGINT UNSIGNED NOT NULL COMMENT '设备ID',
  temperature  DECIMAL(6,2)    NULL     COMMENT '温度℃',
  humidity     DECIMAL(6,2)    NULL     COMMENT '湿度%RH',
  illuminance  DECIMAL(10,2)   NULL     COMMENT '光照lux',
  raw_json     JSON            NULL     COMMENT '原始扩展字段',
  recorded_at  DATETIME        NOT NULL COMMENT '采集时间',
  created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  PRIMARY KEY (id),
  KEY idx_data_device_time (device_id, recorded_at),
  CONSTRAINT fk_data_device FOREIGN KEY (device_id) REFERENCES device (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='设备数据表';

-- ----------------------------
-- 指令日志表
-- ----------------------------
CREATE TABLE command_log (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  device_id     BIGINT UNSIGNED NOT NULL COMMENT '设备ID',
  command_type  VARCHAR(64)     NOT NULL COMMENT '指令类型',
  payload       JSON            NULL     COMMENT '指令参数',
  status        VARCHAR(32)     NOT NULL DEFAULT 'pending' COMMENT 'pending/sent/done/fail',
  result_msg    VARCHAR(512)    NULL     COMMENT '设备回执说明',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_cmd_device (device_id),
  CONSTRAINT fk_cmd_device FOREIGN KEY (device_id) REFERENCES device (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='指令日志表';

-- ----------------------------
-- 操作审计表
-- ----------------------------
CREATE TABLE operation_log (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id    BIGINT UNSIGNED NULL     COMMENT '用户ID',
  action     VARCHAR(64)     NOT NULL COMMENT '动作编码',
  detail     VARCHAR(512)    NULL     COMMENT '详情',
  ip         VARCHAR(45)     NULL     COMMENT '来源IP',
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_op_user (user_id),
  CONSTRAINT fk_op_user FOREIGN KEY (user_id) REFERENCES `user` (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='操作日志表';

-- ----------------------------
-- AI 分析报告表
-- ----------------------------
CREATE TABLE ai_report (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id     BIGINT UNSIGNED NOT NULL COMMENT '所属用户',
  device_id   BIGINT UNSIGNED NULL     COMMENT '关联设备，可为空表示多设备汇总',
  report_type VARCHAR(32)     NOT NULL DEFAULT 'summary' COMMENT '报告类型',
  title       VARCHAR(256)    NULL     COMMENT '标题',
  summary     TEXT            NULL     COMMENT '摘要',
  content     LONGTEXT        NULL     COMMENT '正文（可含Markdown）',
  chart_meta  JSON            NULL     COMMENT '图表配置快照',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_ai_user (user_id),
  KEY idx_ai_device (device_id),
  CONSTRAINT fk_ai_user FOREIGN KEY (user_id) REFERENCES `user` (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_ai_device FOREIGN KEY (device_id) REFERENCES device (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='AI分析报告表';

-- ----------------------------
-- 默认数据：演示账号 admin / 123456（答辩后请修改密码）
-- password_hash：Werkzeug 3 pbkdf2:sha256（较 scrypt 更短，避免部分环境下误判列/截断）
-- 建议整行执行：Windows 下 source 若遇编码问题，可在客户端执行 SET NAMES utf8mb4;
-- ----------------------------
INSERT INTO `user` (username, password_hash, nickname, status) VALUES ('admin', 'pbkdf2:sha256:1000000$cTX0gmpoPlbGmKP2$334dd28d71bf4d21474e45837f2dbb8c139b15ddf86a1e58898a2b40b9db9ff5', '管理员', 1);

-- ----------------------------
-- 演示设备与数据（无硬件亦可浏览监测/报告页面；重新 source 会重建）
-- ----------------------------
INSERT INTO device (device_uid, device_secret, user_id, name, status, last_heartbeat, firmware_ver) VALUES
('SIMULATED-ESP32-A1', 'secret-a1-demo', 1, '客厅环境监测（演示）', 1, NOW() - INTERVAL 3 MINUTE, '0.9.0-demo'),
('UNBOUND-DEMO-01', 'bind-me-888', NULL, '待绑定演示设备', 1, NULL, NULL);

INSERT INTO device_data (device_id, temperature, humidity, illuminance, recorded_at) VALUES
(1, 22.10, 58.00, 120.00, NOW() - INTERVAL 6 HOUR),
(1, 22.40, 57.00, 180.00, NOW() - INTERVAL 5 HOUR),
(1, 22.80, 56.00, 250.00, NOW() - INTERVAL 4 HOUR),
(1, 23.10, 55.00, 310.00, NOW() - INTERVAL 3 HOUR),
(1, 23.50, 53.00, 380.00, NOW() - INTERVAL 2 HOUR),
(1, 23.80, 52.00, 400.00, NOW() - INTERVAL 90 MINUTE),
(1, 24.00, 50.00, 420.00, NOW() - INTERVAL 60 MINUTE),
(1, 24.20, 49.00, 405.00, NOW() - INTERVAL 45 MINUTE),
(1, 24.10, 48.50, 390.00, NOW() - INTERVAL 30 MINUTE),
(1, 23.90, 48.00, 370.00, NOW() - INTERVAL 15 MINUTE),
(1, 23.70, 47.50, 360.00, NOW() - INTERVAL 5 MINUTE),
(1, 23.60, 47.00, 355.00, NOW());

INSERT INTO command_log (device_id, command_type, payload, status, result_msg) VALUES
(1, 'set_interval', JSON_OBJECT('seconds', 120), 'pending', NULL);

INSERT INTO ai_report (user_id, device_id, report_type, title, summary, content) VALUES
(1, 1, 'summary', '演示：环境数据初览', '温湿度在舒适区间内波动。', '本记录由初始化脚本写入。点击「生成分析」可基于当前库内数据生成新的离线模拟报告。');
