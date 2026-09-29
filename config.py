# -*- coding: utf-8 -*-
"""
애플리케이션 설정값
운영 환경에 따라 환경변수로 덮어쓸 수 있도록 os.environ 사용
"""
import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24).hex())
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))

    # 원본 뉴스 소스 (실시간 속보 JSON 피드)
    # 주의: 비공식 엔드포인트이므로 원본 사이트 구조 변경 시 동작하지 않을 수 있습니다.
    #       운영 배포 전 반드시 실제 응답을 확인하고, 원본 사이트의 이용약관을 확인하세요.
    SOURCE_API_URL = os.environ.get(
        "SOURCE_API_URL",
        "https://api-one-wscn.awtmt.com/apiv1/content/information-flow"
        "?channel=global&accept=article&limit=30",
    )
    # 스크래핑 폴백용 원본 페이지 (JSON API 실패 시 사용)
    SOURCE_PAGE_URL = os.environ.get("SOURCE_PAGE_URL", "https://wallstreetcn.com/live/global")
    SOURCE_ARTICLE_BASE = "https://wallstreetcn.com/articles/"

    # 출처 표기 (저작권/콘텐츠 정책 준수를 위한 필수 표기)
    SOURCE_NAME = "Wall Street CN (华尔街见闻)"
    SOURCE_HOME_URL = "https://wallstreetcn.com"

    # 백그라운드 폴링 주기(초) - 원본 서버 부하를 주지 않도록 30초 이상 권장
    POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", 30))

    # 프런트엔드가 폴링하는 주기(ms) - 서버 폴링 주기와 맞추거나 더 짧게
    CLIENT_POLL_INTERVAL_MS = int(os.environ.get("CLIENT_POLL_INTERVAL_MS", 15000))

    # 메모리 사용량 제한 (무한정 누적 방지)
    MAX_ITEMS_IN_MEMORY = int(os.environ.get("MAX_ITEMS_IN_MEMORY", 100))
    MAX_TRANSLATION_CACHE = int(os.environ.get("MAX_TRANSLATION_CACHE", 500))

    # 요약 길이 제한 (원문 전재 방지 - 저작권 보호를 위해 짧은 발췌만 사용)
    SUMMARY_MAX_CHARS = int(os.environ.get("SUMMARY_MAX_CHARS", 110))

    # 외부 요청 타임아웃 (초)
    REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", 8.0))

    # User-Agent (원본 서버에 정상적인 브라우저 요청처럼 식별)
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
        "WSCN-KR-Mirror/1.0 (+https://github.com/) "
    )
