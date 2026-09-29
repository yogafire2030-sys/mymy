# -*- coding: utf-8 -*-
"""
월스트리트견문(WallStreetCN) 실시간 속보 한국어 요약 서비스
- 원문 전체를 복제하지 않고, 짧은 발췌 + 한국어 번역 + 원문 링크만 제공합니다.
- 출처 표기를 항상 포함합니다.
"""
import logging

from flask import Flask, jsonify, render_template

from config import Config
from services.news_service import news_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.after_request
    def set_secure_headers(response):
        # 기본적인 보안 헤더 (Secure Coding)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            source_name=Config.SOURCE_NAME,
            source_url=Config.SOURCE_HOME_URL,
            poll_interval_ms=Config.CLIENT_POLL_INTERVAL_MS,
        )

    @app.route("/api/news")
    def api_news():
        try:
            snapshot = news_service.get_snapshot()
            return jsonify({"ok": True, **snapshot})
        except Exception as exc:  # 내부 오류가 그대로 노출되지 않도록 처리
            logger.exception("API 처리 중 오류: %s", exc)
            return jsonify({"ok": False, "error": "일시적인 오류가 발생했습니다."}), 500

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"ok": False, "error": "요청하신 경로를 찾을 수 없습니다."}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"ok": False, "error": "서버 내부 오류가 발생했습니다."}), 500

    # 백그라운드 뉴스 폴링 시작 (앱 프로세스당 1회).
    # __main__ 블록이 아니라 여기서 시작해야, gunicorn 등 운영용 WSGI 서버가
    # 이 모듈을 "import"만 하고 실행하는 배포 환경(Render, Railway 등)에서도
    # 실시간 수집이 정상적으로 동작합니다. news_service.start()는 이미 실행 중이면
    # 아무 동작도 하지 않으므로 중복 호출에 안전합니다.
    news_service.start()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
