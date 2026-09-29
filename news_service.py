# -*- coding: utf-8 -*-
"""
실시간 뉴스 수집 서비스
- 백그라운드 스레드가 일정 주기로 원본 소스를 조회하여 최신 속보를 가져옵니다.
- 모든 사용자(브라우저 탭)는 이 서비스가 메모리에 들고 있는 캐시를 공유합니다.
  (사용자마다 원본 사이트를 스크래핑하면 원본 서버에 과도한 부하를 주고 성능도 나빠지므로,
   서버당 단일 폴링 스레드만 운영하는 구조로 설계했습니다.)
- 저작권 보호를 위해 원문 전체가 아닌 "짧은 발췌 + 번역 + 원문 링크"만 제공합니다.
"""
import html
import logging
import re
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from config import Config
from services.translator import translator

logger = logging.getLogger(__name__)


def _clean_text(raw: Optional[str]) -> str:
    """HTML 태그 제거 및 공백 정리 (XSS 방지를 위한 1차 정제)"""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _truncate(text: str, max_chars: int) -> str:
    """저작권 보호를 위해 발췌 길이를 제한 (원문 전재 방지)"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _format_time(ts) -> str:
    try:
        ts = int(ts)
        # 초 단위 / 밀리초 단위 모두 대응
        if ts > 10_000_000_000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime("%H:%M")
    except Exception:
        return datetime.now().strftime("%H:%M")


class NewsService:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": cfg.USER_AGENT,
                "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
            }
        )
        self._items: List[Dict] = []
        self._seen_ids = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_updated: Optional[str] = None
        self._last_error: Optional[str] = None

    # ---------- 공개 API ----------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="news-poller")
        self._thread.start()
        logger.info("뉴스 폴링 백그라운드 스레드 시작")

    def stop(self) -> None:
        self._stop_event.set()

    def get_snapshot(self) -> Dict:
        with self._lock:
            items = list(self._items)
        return {
            "items": items,
            "last_updated": self._last_updated,
            "last_error": self._last_error,
            "source_name": self._cfg.SOURCE_NAME,
            "source_url": self._cfg.SOURCE_HOME_URL,
        }

    # ---------- 내부 동작 ----------

    def _run_loop(self) -> None:
        # 시작하자마자 1회 즉시 수집 후, 이후 주기적으로 반복
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as exc:  # 백그라운드 스레드가 죽지 않도록 방어적으로 처리
                logger.exception("뉴스 수집 중 오류 발생: %s", exc)
                with self._lock:
                    self._last_error = str(exc)
            self._stop_event.wait(self._cfg.POLL_INTERVAL_SECONDS)

    def _poll_once(self) -> None:
        raw_items = self._fetch_from_api()
        if raw_items is None:
            raw_items = self._fetch_from_html_fallback()

        if not raw_items:
            return

        new_items = []
        for raw in raw_items:
            parsed = self._parse_item(raw)
            if not parsed:
                continue
            if parsed["id"] in self._seen_ids:
                continue
            new_items.append(parsed)

        if not new_items:
            with self._lock:
                self._last_error = None
            return

        # 번역은 CPU/네트워크 비용이 있으므로 새 항목에 대해서만 수행 (성능 최적화)
        for item in new_items:
            item["title_ko"] = translator.translate(item["title_raw"])
            item["summary_ko"] = translator.translate(item["summary_raw"]) if item["summary_raw"] else ""

        with self._lock:
            for item in new_items:
                self._seen_ids.add(item["id"])
            # 최신순으로 합치고 최대 개수 제한 (메모리 누수 방지)
            self._items = (new_items + self._items)[: self._cfg.MAX_ITEMS_IN_MEMORY]
            # seen_ids도 함께 정리
            self._seen_ids = {it["id"] for it in self._items}
            self._last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._last_error = None

        logger.info("새 속보 %d건 수집 및 번역 완료", len(new_items))

    def _fetch_from_api(self) -> Optional[List[Dict]]:
        try:
            resp = self._session.get(self._cfg.SOURCE_API_URL, timeout=self._cfg.REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning("JSON API 수집 실패, HTML 폴백을 시도합니다: %s", exc)
            return None

        items = (payload or {}).get("data", {}).get("items", [])
        if not isinstance(items, list):
            return None
        return items

    def _fetch_from_html_fallback(self) -> Optional[List[Dict]]:
        """
        JSON API가 막히거나 구조가 바뀐 경우를 대비한 최소한의 HTML 폴백.
        원본 페이지 구조 변경에 취약할 수 있으므로 best-effort로만 동작합니다.
        """
        try:
            resp = self._session.get(self._cfg.SOURCE_PAGE_URL, timeout=self._cfg.REQUEST_TIMEOUT)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("HTML 폴백 수집도 실패했습니다: %s", exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = soup.select("[class*='live'], [class*='article'], li, article")
        results = []
        time_pattern = re.compile(r"^\d{2}:\d{2}$")

        for node in candidates:
            text = _clean_text(node.get_text(separator="\n"))
            if not text:
                continue
            lines = [l for l in text.split("\n") if l.strip()]
            if not lines:
                continue
            if time_pattern.match(lines[0].strip()):
                title = lines[1] if len(lines) > 1 else lines[0]
                results.append(
                    {
                        "resource": {
                            "title": title,
                            "content_short": title,
                            "uri": self._cfg.SOURCE_PAGE_URL,
                            "display_time": time.time(),
                        }
                    }
                )
        # 중복 제거 및 상한
        return results[:30] if results else None

    def _parse_item(self, raw: Dict) -> Optional[Dict]:
        resource = raw.get("resource", raw)  # 폴백 데이터는 이미 resource 형태
        title = _clean_text(resource.get("title") or resource.get("content_short") or "")
        summary = _clean_text(resource.get("content_short") or "")
        if not title and not summary:
            return None
        if not title:
            title = summary

        summary = summary if summary != title else ""

        uri = resource.get("uri") or self._cfg.SOURCE_PAGE_URL
        display_time = resource.get("display_time") or time.time()
        item_id = str(resource.get("id") or uri or title)

        return {
            "id": item_id,
            "time": _format_time(display_time),
            "title_raw": _truncate(title, self._cfg.SUMMARY_MAX_CHARS),
            "summary_raw": _truncate(summary, self._cfg.SUMMARY_MAX_CHARS) if summary else "",
            "url": uri,
        }


news_service = NewsService(Config())
