(function () {
  "use strict";

  const feedEl = document.getElementById("feed");
  const emptyEl = document.getElementById("feed-empty");
  const statusEl = document.getElementById("status-text");
  const liveDot = document.getElementById("live-dot");
  const template = document.getElementById("item-template");

  const POLL_MS = (window.__APP_CONFIG__ && window.__APP_CONFIG__.pollIntervalMs) || 15000;
  const renderedIds = new Set();
  let isFetching = false;

  function formatUpdatedLabel(lastUpdated) {
    if (!lastUpdated) return "업데이트 대기 중";
    return "마지막 업데이트 " + lastUpdated.split(" ")[1];
  }

  function renderItem(item) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.dataset.id = item.id;

    const timeEl = node.querySelector("time");
    timeEl.textContent = item.time;

    const titleEl = node.querySelector(".card__title");
    // textContent만 사용하여 스크립트 삽입 등 XSS 위험을 원천 차단
    titleEl.textContent = item.title_ko || "";

    const summaryEl = node.querySelector(".card__summary");
    if (item.summary_ko && item.summary_ko !== item.title_ko) {
      summaryEl.textContent = item.summary_ko;
    } else {
      summaryEl.remove();
    }

    const linkEl = node.querySelector(".card__link");
    linkEl.href = item.url;

    return node;
  }

  function applyItems(items) {
    if (!Array.isArray(items) || items.length === 0) return;

    const freshNodes = [];
    for (const item of items) {
      if (renderedIds.has(item.id)) continue;
      renderedIds.add(item.id);
      freshNodes.push(renderItem(item));
    }

    if (freshNodes.length === 0) return;

    if (emptyEl && emptyEl.parentNode) {
      emptyEl.remove();
    }

    // 최신 항목이 배열 맨 앞이므로, 화면 맨 위에 순서대로 삽입
    const frag = document.createDocumentFragment();
    freshNodes.forEach((n) => frag.appendChild(n));
    feedEl.prepend(frag);

    // DOM이 무한정 늘어나지 않도록 오래된 카드 정리 (성능/메모리 보호)
    const MAX_DOM_ITEMS = 150;
    const cards = feedEl.querySelectorAll(".card");
    if (cards.length > MAX_DOM_ITEMS) {
      for (let i = MAX_DOM_ITEMS; i < cards.length; i++) {
        const id = cards[i].dataset.id;
        renderedIds.delete(id);
        cards[i].remove();
      }
    }
  }

  async function poll() {
    if (isFetching) return; // 중복 호출 방지
    isFetching = true;
    try {
      const res = await fetch("/api/news", { cache: "no-store" });
      const payload = await res.json();

      if (!payload.ok) {
        throw new Error(payload.error || "알 수 없는 오류");
      }

      applyItems(payload.items);
      statusEl.textContent = formatUpdatedLabel(payload.last_updated);
      liveDot.classList.remove("is-error");
    } catch (err) {
      statusEl.textContent = "연결 오류 · 재시도 중";
      liveDot.classList.add("is-error");
      console.error("뉴스 폴링 실패:", err);
    } finally {
      isFetching = false;
    }
  }

  poll();
  setInterval(poll, POLL_MS);

  // 탭이 다시 보일 때 즉시 한 번 갱신 (사용자 체감 실시간성 향상)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") poll();
  });
})();
