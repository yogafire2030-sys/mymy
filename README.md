# 실시간 글로벌 속보 (한국어 요약) — Flask

Wall Street CN(华尔街见闻)의 실시간 속보 채널 제목/짧은 발췌를 한국어로 번역해 보여주는
Flask 웹 애플리케이션입니다.

> 저작권 보호를 위해 **원문 전체를 복제하지 않습니다.** 각 속보는 제목과 짧은 발췌(110자 이내)만
> 번역해서 보여주고, "원문 보기" 링크로 항상 원본 기사 페이지를 연결합니다.

## 폴더 구조

```
wscn_kr_live/
├── app.py                  # Flask 앱 진입점 (라우트)
├── config.py                # 설정값 (환경변수로 재정의 가능)
├── requirements.txt
├── Procfile                 # Render 등 클라우드 배포용 실행 명령
├── runtime.txt               # 배포 시 사용할 Python 버전
├── services/
│   ├── news_service.py      # 원본 소스 수집 + 파싱 + 백그라운드 폴링
│   └── translator.py        # 중국어→한국어 번역 (캐시 포함)
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/script.js
```

## 실행 방법

```bash
cd wscn_kr_live
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://localhost:5000` 접속하면 실시간으로 속보가 갱신됩니다.

## 동작 방식

1. 서버가 시작되면 백그라운드 스레드가 30초(기본값)마다 원본 소스를 조회합니다.
   - 모든 브라우저 탭이 이 캐시를 공유하므로, 방문자가 많아도 원본 사이트에는
     서버당 한 번만 요청이 갑니다.
2. 새로 들어온 속보만 번역합니다(이미 번역한 항목은 캐시에서 재사용).
3. 브라우저는 15초(기본값)마다 `/api/news`를 조회해 새 항목만 화면에 추가합니다.

## 환경변수로 조정 가능한 값 (`config.py`)

| 변수 | 설명 | 기본값 |
|---|---|---|
| `POLL_INTERVAL_SECONDS` | 서버가 원본을 조회하는 주기 | 30 |
| `CLIENT_POLL_INTERVAL_MS` | 브라우저가 서버를 조회하는 주기 | 15000 |
| `MAX_ITEMS_IN_MEMORY` | 메모리에 보관할 최대 속보 수 | 100 |
| `SUMMARY_MAX_CHARS` | 발췌 최대 길이(자) | 110 |
| `SOURCE_API_URL` | 원본 JSON 피드 주소 | (코드 참고) |

## 클라우드에 배포해서 24시간 여러 사람에게 공유하기 (Render 기준)

PC를 계속 켜두지 않고, 스마트폰·아이패드 등 어떤 기기에서든 고정 링크로 접속하게
하려면 아래처럼 Render(무료 티어 있음)에 배포하면 됩니다.

1. **GitHub에 올리기**: 이 `wscn_kr_live` 폴더 전체를 GitHub 저장소로 올립니다
   (GitHub Desktop 같은 GUI 툴을 쓰면 명령어 없이도 가능합니다).
2. **render.com** 가입 후 대시보드에서 **New → Web Service** 선택, 방금 올린
   저장소를 연결합니다.
3. 아래 값을 입력합니다.
   | 항목 | 값 |
   |---|---|
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT` |

   (Start Command는 이미 `Procfile`에 적어 두었으므로 Render가 자동으로 인식하는 경우도 많습니다.)
4. **Create Web Service**를 누르면 몇 분 내로 `https://프로젝트이름.onrender.com` 같은
   고정 주소가 생깁니다. 이 링크를 스마트폰, 아이패드 등 어디서든 그대로 열면 됩니다.

**꼭 알아두어야 할 점**
- `--workers 1`은 실수가 아니라 의도된 설정입니다. 이 앱은 속보 캐시를 메모리에 한 벌만
  들고 단일 백그라운드 스레드로 갱신하는 구조라, 워커를 여러 개로 늘리면 워커마다
  따로 원본 사이트를 긁어오게 되어 비효율적이고 사용자마다 다른 캐시를 보게 될 수
  있습니다. 트래픽이 아주 많아질 경우엔 Redis 등 공유 저장소로 구조를 바꿔야 워커를
  늘릴 수 있습니다.
- Render **무료 티어는 15분간 요청이 없으면 서버가 잠들고(sleep)**, 다음 접속 시
  다시 깨어나는 데 30초~1분 정도 걸릴 수 있습니다. 정말 "상시 실시간"이 중요하다면
  유료 플랜(월 7달러 내외의 Starter 플랜 등)으로 올리면 잠들지 않습니다.
- 배포 후에도 원본 소스 접근이 막히면(예: IP 차단) `SOURCE_API_URL` 등을 다시 점검해야
  할 수 있습니다.

## 꼭 확인해 주세요

- `SOURCE_API_URL`은 원본 사이트가 웹페이지 내부적으로 사용하는 비공식 엔드포인트입니다.
  사이트 구조가 바뀌면 동작하지 않을 수 있으며, 이 경우 `news_service.py`의
  `_fetch_from_html_fallback` 폴백이 시도되지만 100% 신뢰할 수는 없습니다. 실제 배포 전
  응답을 직접 확인하세요.
- 상업적으로 서비스하거나 대량으로 배포할 계획이라면, 반드시 원본 사이트(Wall Street CN)의
  이용약관과 콘텐츠 정책을 다시 확인하시길 권장합니다. 본 프로그램은 "짧은 발췌 + 번역 +
  원문 링크 + 출처 표기"라는 저작권 친화적 구조로 설계되었지만, 최종 법적 판단은 사용자
  책임입니다.
- 번역은 `deep-translator`의 무료 Google Translate 연동을 사용합니다. 대량 트래픽 환경에서는
  DeepL API, Papago API 등 유료 번역 API로 교체하는 것을 권장합니다
  (`services/translator.py`의 `GoogleTranslator` 부분만 교체하면 됩니다).

## 적용된 보안/성능/안정성 조치

- **Secure Coding**: 보안 헤더 적용(`X-Content-Type-Options`, `X-Frame-Options` 등),
  스크래핑한 텍스트는 HTML 태그 제거 후 사용, 프런트엔드는 `textContent`만 사용해 XSS 방지,
  외부 요청에 타임아웃 적용, 예외 발생 시 스택트레이스 미노출.
- **성능 최적화**: 서버당 단일 백그라운드 폴링 스레드(중복 스크래핑 방지), 번역 결과 캐싱,
  requests.Session 재사용(커넥션 풀링), 프런트엔드는 변경분만 DOM에 추가(diff 렌더링).
- **메모리 누수 방지**: 속보 캐시·번역 캐시 모두 최대 크기 제한 후 오래된 항목 자동 제거,
  프런트엔드 DOM 카드 수도 상한 적용.
