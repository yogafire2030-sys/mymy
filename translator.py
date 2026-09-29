# -*- coding: utf-8 -*-
"""
번역 서비스
- deep-translator(GoogleTranslator)를 사용하여 중국어 원문을 한국어로 번역
- 동일 원문 재번역을 막기 위한 캐시 적용 (성능 최적화 + 메모리 누수 방지를 위한 크기 제한)
- 번역 실패 시 예외를 삼키지 않고 안전하게 원문/대체 문구를 반환 (서비스 중단 방지)
"""
import hashlib
import logging
import threading
from collections import OrderedDict

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


class TranslationCache:
    """
    스레드 안전 LRU 캐시.
    - 백그라운드 폴링 스레드와 요청 스레드에서 동시 접근 가능하므로 Lock으로 보호합니다.
    - 크기를 제한하여 장시간 구동 시 메모리 누수를 방지합니다.
    """

    def __init__(self, max_size: int = 500):
        self._max_size = max_size
        self._store: "OrderedDict[str, str]" = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _key(text: str) -> str:
        # 원문 길이가 길 수 있으므로 해시로 키 크기를 고정 (메모리 절약)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str):
        key = self._key(text)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                return self._store[key]
        return None

    def set(self, text: str, translated: str) -> None:
        key = self._key(text)
        with self._lock:
            self._store[key] = translated
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)


class Translator:
    def __init__(self, max_cache_size: int = 500):
        self._cache = TranslationCache(max_cache_size)
        # GoogleTranslator 인스턴스는 상태가 거의 없어 재사용 가능 (호출 오버헤드 절감)
        self._engine = GoogleTranslator(source="zh-CN", target="ko")
        self._lock = threading.Lock()

    def translate(self, text: str) -> str:
        if not text:
            return ""

        cached = self._cache.get(text)
        if cached is not None:
            return cached

        try:
            # 외부 번역 API 동시 호출 폭주 방지 (원본 서비스 정책/부하 보호)
            with self._lock:
                translated = self._engine.translate(text)
            if not translated:
                translated = text
        except Exception as exc:  # 번역 실패 시 전체 서비스가 죽지 않도록 방어
            logger.warning("번역 실패, 원문으로 대체합니다: %s", exc)
            translated = text

        self._cache.set(text, translated)
        return translated


# 애플리케이션 전체에서 공유하는 싱글턴 인스턴스
translator = Translator()
