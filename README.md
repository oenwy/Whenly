# 언제 만날까 — 일정 조율 앱

참여자들이 투표로 가장 많이 겹치는 날짜를 찾는 웹앱입니다.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend | Python 3.11 + FastAPI |
| DB | Upstash Redis (서버리스 Redis) |
| Frontend | 순수 HTML/CSS/JS (빌드 불필요) |
| 배포 | Vercel |

---

## 🚀 Vercel 배포 방법

### 1단계 — Upstash Redis 설정 (무료)

1. [https://upstash.com](https://upstash.com) 접속 → 회원가입
2. **Create Database** → Region: `ap-northeast-1 (Tokyo)` 선택 (한국과 가장 가까움)
3. **REST API** 탭에서 아래 두 값을 복사해 둡니다:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`

### 2단계 — GitHub 리포지토리 생성

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 3단계 — Vercel 배포

1. [https://vercel.com](https://vercel.com) 접속 → GitHub으로 로그인
2. **New Project** → 위 리포지토리 선택
3. **Environment Variables** 탭에서 아래 두 값 추가:

```
UPSTASH_REDIS_REST_URL   = https://xxxxx.upstash.io
UPSTASH_REDIS_REST_TOKEN = AxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxYYYY
```

4. **Deploy** 클릭 → 완료!

---

## 로컬 개발

```bash
pip install -r requirements.txt

# 환경변수 없이도 인메모리로 동작합니다 (서버 재시작 시 데이터 초기화)
cd api
uvicorn index:app --reload --port 8000
```

`public/index.html`의 `const API = '/api'` 부분을 `const API = 'http://localhost:8000/api'`로 바꾸면 로컬에서 테스트 가능합니다.

---

## 프로젝트 구조

```
.
├── api/
│   └── index.py          # FastAPI 앱 (Vercel 서버리스 함수)
├── public/
│   └── index.html        # 프론트엔드 (SPA)
├── requirements.txt      # Python 의존성
├── vercel.json           # Vercel 라우팅 설정
└── README.md
```

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/rooms` | 방 생성 |
| `GET`  | `/api/rooms/{id}` | 방 정보 조회 |
| `POST` | `/api/rooms/{id}/vote` | 투표 제출/수정 |
| `GET`  | `/api/rooms/{id}/results` | 결과 + 집계 조회 |
