# -*- coding: utf-8 -*-
"""
Flask 应用工厂：注册蓝图、跨域、静态页访问等。
"""
from flask import Flask, send_from_directory
from flask_cors import CORS

from app.config import Config


def create_app():
    """创建并配置 Flask 应用实例。"""
    # root_path 为 app 包所在目录，故静态资源使用相对上级的 ../static
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.from_object(Config)

    # 允许前端跨域携带 Cookie（与 fetch credentials:include 配合）
    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
    )

    # 注册蓝图（路由层）
    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.device_routes import device_bp
    from app.routes.data_routes import data_bp
    from app.routes.command_routes import command_bp
    from app.routes.ai_routes import ai_bp
    from app.routes.device_gateway_routes import device_gateway_bp
    from app.routes.dashboard_routes import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(device_bp, url_prefix="/api/devices")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(data_bp, url_prefix="/api")
    app.register_blueprint(command_bp, url_prefix="/api")
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    app.register_blueprint(device_gateway_bp, url_prefix="/api/device")

    @app.route("/")
    def index_page():
        """默认打开登录页（静态页）。"""
        return send_from_directory(app.static_folder, "pages/login.html")

    @app.route("/pages/<path:name>")
    def static_pages(name):
        """便捷访问 /pages/xxx.html。"""
        return send_from_directory(f"{app.static_folder}/pages", name)

    return app
