# 부산 AI 민원 길잡이

민원 내용을 입력하면 담당 부서, 처리기한, 수수료, 서식, 연락처를 바로 안내해 주는 웹 서비스입니다.
부산민원120 민원편람 데이터를 기반으로 검색하고, 선택적으로 LLM(OpenRouter)이 요약과 답변 초안을 만들어 줍니다.

## 주요 기능

- 문자 bigram TF-IDF와 동의어 확장을 이용한 민원 검색 (`app/engine.py`)
- 민원 유형 분류 (`app/types.py`, `app/categories.py`)
- LLM 요약 및 답변 초안 생성, 시간당 호출 제한 (`app/llm.py`)
- 검색 기록 및 조회수 저장 (SQLite), 검색 로그는 전화번호·메일을 마스킹하고 90일 후 삭제
- 표준 라이브러리만 사용하는 단일 웹서버 (`app/server.py`) — 별도 패키지 설치 불필요

## 구조

```
app/    서버, 검색 엔진, LLM 연동
web/    프론트엔드 (index.html 단일 페이지)
data/   민원 데이터 (db.json 등)
tools/  데이터 수집·가공·분석 스크립트
```

## 실행

Python 3 (표준 라이브러리만 사용)

```bash
cp .env.example .env     # OPENROUTER_API_KEY 입력 (없으면 AI 기능 없이 검색만 동작)
python3 app/server.py 8810
```

브라우저에서 `http://localhost:8810` 접속.

### 환경변수 (`.env`)

| 이름 | 설명 | 기본값 |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API 키 | 없음 |
| `OPENROUTER_MODEL` | OpenRouter 모델 ID | `openai/gpt-6-luna` |
| `AI_LIMIT_PER_HOUR` | 시간당 AI 호출 제한 | `20` |

## 데이터 갱신

```bash
python3 tools/parse_hwpx.py      # 민원목록 hwpx -> data/minwon.json
python3 tools/parse_onestop.py   # 원스톱 정보
python3 tools/crawl_manual.py    # 민원편람 수집 -> data/manual.json
python3 tools/crawl_detail.py    # 상세 본문 추출 -> data/manual_detail.json
python3 tools/build_data.py      # 통합 -> data/db.json
python3 tools/analyze_log.py 30  # 최근 30일 검색 품질 분석
```

## 배포 (systemd 예시)

```ini
[Service]
WorkingDirectory=/path/to/minwon
ExecStart=/usr/bin/python3 -I app/server.py 8810
Restart=always
```

## 데이터 출처

부산광역시 부산민원120 민원편람. 크롤링 시 요청 간 0.4초 간격을 둡니다.
