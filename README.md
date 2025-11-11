# Finviz Daily Report

매일 아침마다 Finviz에서 대형주 상위 5개 + 초대형주 상위 5개 (총 10개) 종목을 3개월 수익률 기준으로 수집하고, 전날 및 일주일 전과 비교하여 Telegram으로 보고하는 시스템입니다.

## 🚀 기능

- 📊 **실시간 데이터 수집**: Finviz 웹 스크래핑으로 최신 데이터 수집
- 📈 **상위 5개 종목**: 3개월 수익률 기준 대형주 상위 5개 + 초대형주 상위 5개
- 🔄 **변화 분석**: 전날 및 일주일 전 대비 변화 분석
- 🎯 **다중 스크리너**: 대형주(cap_large)와 초대형주(cap_mega) 동시 분석
- 📱 **다중 알림 채널**: Telegram, 이메일, Discord 지원
- ⏰ **자동 스케줄링**: 매일 오전 9시 자동 실행
- 🏗️ **모듈화 구조**: 유지보수하기 쉬운 코드 구조
- 📊 **요약 통계**: 평균 수익률, 최대 상승/하락 종목 등
- 🔍 **순위 변화 추적**: 종목별 순위 변화 시각화
- 📝 **통합 로깅**: 상세한 실행 로그 및 에러 추적
- 🎨 **Markdown 지원**: 깔끔하게 포맷된 Telegram 메시지
- 📉 **기술적 분석**: 60일/120일 이동평균선 분석 및 조건 체크
- 🚀 **신고가 돌파**: 3개월 최고가 경신 시 매수 신호
- 🚨 **손절 신호**: MA60 이탈 시 자동 경고
- 🔴 **트레일링 스탑**: 3개월 최고가 대비 10-15% 하락 시 매도 신호
- 💰 **백테스팅**: 매일 리밸런싱 전략의 성과 시뮬레이션
- ✅ **현실적 백테스팅 (NEW!)**: Look-Ahead Bias 제거 + 거래비용 반영
- 🌐 **웹 대시보드**: Streamlit 기반 인터랙티브 시각화 대시보드

## 📦 설치

### 1. 저장소 클론

```bash
git clone <repository-url>
cd Mo
```

### 2. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. Telegram Bot 설정

#### 3.1 Bot Token 받기
1. Telegram에서 [@BotFather](https://t.me/BotFather)와 대화 시작
2. `/newbot` 명령어 입력
3. 봇 이름과 사용자명 입력
4. **Bot Token** 복사 (예: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### 3.2 Chat ID 받기
1. 생성한 봇과 대화 시작 (아무 메시지나 전송)
2. 웹 브라우저에서 다음 URL 접속:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. 응답에서 `"chat":{"id":123456789}` 부분의 **Chat ID** 복사

#### 3.3 설정 파일 업데이트
`config.py`에서 다음 설정을 변경:

```python
# config.py
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID = "123456789"
```

또는 환경변수로 설정:

```bash
# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
$env:TELEGRAM_CHAT_ID="123456789"

# Windows CMD
set TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
set TELEGRAM_CHAT_ID=123456789
```

## 🚀 사용법

### 1. 수동 실행

```bash
python main.py
```

### 2. Telegram 연결 테스트

```bash
python test_telegram.py
```

### 3. 자동 스케줄링 실행

```bash
python scheduler.py
```

이 명령어를 실행하면 매일 오전 9시에 자동으로 실행됩니다.

### 4. 웹 대시보드 실행 (NEW!)

**준비 상태 확인 (선택사항)**
```bash
python check_dashboard_ready.py
```

이 스크립트는 대시보드 실행에 필요한 데이터와 패키지를 확인합니다.

**방법 1: 실행 스크립트 사용 (권장)**
```bash
# Windows
run_dashboard.bat

# macOS/Linux
python run_dashboard.py
```

**방법 2: 직접 실행**
```bash
streamlit run src/dashboard/app.py
```

브라우저에서 자동으로 열리며, 수동으로는 `http://localhost:8501`로 접속하세요.

자세한 사용법은 [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)를 참고하세요.

### 5. 현실적인 백테스팅 비교 실행 (NEW!)

**개선된 백테스팅의 특징:**
- ✅ **Look-Ahead Bias 제거**: 미래 정보 사용 방지
- 💰 **거래 비용 반영**: 수수료 0.2% + 슬리피지 0.1%
- 📊 **현실적인 결과**: 실제 투자에 가까운 시뮬레이션

```bash
# 기존 vs 개선된 백테스팅 비교
python compare_backtests.py
```

이 명령어를 실행하면:
1. 기존 방식 (Look-Ahead Bias 있음) 백테스팅
2. 개선 방식 (Look-Ahead Bias 제거 + 거래비용) 백테스팅
3. 두 결과를 비교하여 Telegram으로 전송

**예상 결과:**
- 개선 버전의 수익률이 20-50% 정도 낮게 나옴
- 이것이 **실제 투자 시 예상되는 현실적인 수익률**입니다!

**개선된 백테스팅만 단독 실행:**
```python
from src.realistic_backtest import run_realistic_backtest

result = run_realistic_backtest(
    screener_type="large",
    initial_capital=10000,
    test_period_months=3,
    lookback_months=3,
    lag_months=1,
    rebalance_frequency='monthly'
)
```

### 6. Windows 작업 스케줄러 설정 (권장)

1. Windows 작업 스케줄러 열기
2. "기본 작업 만들기" 선택
3. 이름: "Finviz Daily Report"
4. 트리거: 매일 오전 9시
5. 동작: `python C:\Project\Mo\main.py` 실행

## 📁 프로젝트 구조

```
Mo/
├── main.py                    # 메인 실행 파일
├── scheduler.py               # 스케줄러
├── compare_backtests.py       # 백테스팅 비교 스크립트 (NEW!)
├── test_telegram.py          # Telegram 연결 테스트
├── test_slack.py             # Slack 연결 테스트 (레거시)
├── config.py                 # 설정 파일
├── requirements.txt          # 패키지 의존성
├── README.md                 # 사용법 설명
├── src/                      # 소스 코드 모듈
│   ├── __init__.py
│   ├── finviz_scraper.py     # Finviz 웹 스크래핑
│   ├── data_manager.py       # 데이터 저장/로드
│   ├── analyzer.py           # 데이터 분석
│   ├── technical_analyzer.py # 기술적 분석 (이동평균선)
│   ├── backtester.py         # 백테스팅 시뮬레이션
│   ├── historical_backtest.py # 3개월 역산 백테스팅
│   ├── realistic_backtest.py # 현실적 백테스팅 (NEW!)
│   ├── telegram_notifier.py  # Telegram 알림
│   ├── slack_notifier.py     # Slack 알림 (레거시)
│   ├── email_notifier.py     # 이메일 알림
│   ├── discord_notifier.py   # Discord 알림
│   ├── logger.py             # 로깅
│   └── dashboard/            # 웹 대시보드
│       ├── app.py            # 메인 대시보드
│       ├── pages/            # 서브 페이지들
│       ├── components/       # UI 컴포넌트
│       └── utils/            # 유틸리티
├── daily_data/               # 일일 데이터 저장 폴더
│   ├── finviz_data_large_2025-10-27.csv  # 대형주 데이터
│   ├── finviz_data_mega_2025-10-27.csv   # 초대형주 데이터
│   ├── backtest_cache.json   # 백테스팅 결과 캐시
│   ├── backtest_comparison.json # 백테스팅 비교 결과 (NEW!)
│   └── logs/                 # 로그 파일
└── archive/                  # 아카이브 폴더
```

## 출력 예시

### 콘솔 출력
```
=== Finviz 대형주 3개월 수익률 분석 - 2024-01-15 ===
데이터를 성공적으로 가져왔습니다.
데이터를 daily_data/finviz_data_2024-01-15.csv에 저장했습니다.
전날 대비 분석 완료
일주일 전 대비 분석 완료

=== 대형주 3개월 수익률 상위 5개 종목 ===
   Ticker Perf Quart   Price  Change
0   SNDK    320.43%  180.49  -3.05%
1   IREN    300.06%   63.17   0.43%
...
```

### Telegram 메시지
```
📈 Finviz 대형주 3개월 수익률 상위 10개
📅 2025-11-01

📊 요약 통계
• 평균 수익률: 150.5%
• 최고 수익률: 320.4%
• 평균 가격: $120.25
• 최대 상승: SNDK (+5.2%)

━━━━━━━━━━━━━━━━━━━━

🏆 포트폴리오 상위 5개 종목

1. SNDK - 368.90% ($199.33) 🆕 ✅ → 🟢 보유
2. IREN - 268.63% ($60.75) 🆕 ✅ → 🔴 매도
3. BE - 266.09% ($132.16) 🆕 ✅ → 🟢 보유
4. SATS - 184.35% ($74.87) 🆕 ✅ → 🔴 매도
5. RGTI - 180.90% ($44.27) 🆕 ✅ → 🔴 매도

━━━━━━━━━━━━━━━━━━━━

📊 전날 대비 변화

• 🆕 새로 진입: MSTR, ABC
• 📉 탈락: DEF, GHI

• 🔥 상위 3개 종목 변화:

  SNDK:
  • 📈 수익률: 315.20% → 320.43% (+5.2%)
  • 💰 가격: $175.44 → $180.49 (+$5.05, +2.9%)

  IREN:
  • ➡ 수익률: 299.80% → 300.06% (+0.3%)
  • 💰 가격: $62.90 → $63.17 (+$0.27, +0.4%)

━━━━━━━━━━━━━━━━━━━━

📊 기술적 분석 (이동평균선)

• ✅ 모든 조건 만족: 5개
  → SNDK, IREN, BE, SATS, RGTI
• ⚠️ 부분 조건 만족: 0개

조건: 현재가 > 60일선 > 120일선

━━━━━━━━━━━━━━━━━━━━

🚀 신고가 돌파 (매수 신호)

• SNDK: $199.33
  📊 전 최고가: $195.20
  🎯 돌파율: +2.1%

• NBIS: $130.82
  📊 전 최고가: $128.50
  🎯 돌파율: +1.8%

🎉 총 2개 종목이 3개월 신고가 경신!
💡 권장: 매수 또는 추가 매수 검토

━━━━━━━━━━━━━━━━━━━━

🔴 트레일링 스탑 경고 (매도 신호)

• IREN: $60.75
  📊 MA20: $60.96
  📉 이탈폭: -0.3% (2일째 하향 이탈)

• BABA: $170.43
  📊 MA20: $172.16
  📉 이탈폭: -1.0% (2일째 하향 이탈)

🚨 총 2개 종목이 MA20을 2일 이상 이탈
💡 권장: 즉시 매도 검토

━━━━━━━━━━━━━━━━━━━━

🚨 MA60 이탈 경고 (손절 신호)

• ABC: $95.50 (MA60 $98.20, -2.7% 이탈)

⚠️ 총 1개 종목이 60일선을 이탈했습니다.
💡 권장: 손절 검토

━━━━━━━━━━━━━━━━━━━━

💰 백테스팅 성과 (매일 리밸런싱)

• 기간: 2025-10-27 ~ 2025-11-01
• 초기 자본: $10,000
• 최종 가치: $10,150
• 총 수익률: 1.5%
• 연환산 수익률: 125.3%
• 최대낙폭 (MDD): -1.2%
• 샤프비율: 1.85
• 승률: 60.0%
• 거래일수: 5일

📈 최고 수익일: 2025-10-28 (+2.1%)
📉 최악 수익일: 2025-10-30 (-0.8%)
```

## 설정 옵션

`config.py`에서 다음 설정을 변경할 수 있습니다:

### 필수 설정
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `TELEGRAM_CHAT_ID`: Telegram Chat ID

### 선택적 설정
- `DATA_DIR`: 데이터 저장 디렉토리 (기본: "daily_data")
- `SCHEDULE_TIME`: 실행 시간 (기본: "09:00")
- `SCREENER_TYPES`: 분석할 종목 유형 (기본: "both")
  - "both": 대형주 + 초대형주 (Telegram 메시지 2개)
  - "large": 대형주만
  - "mega": 초대형주만
- `ENABLE_TELEGRAM_NOTIFICATIONS`: Telegram 알림 활성화 (기본: True)
- `ENABLE_EMAIL_NOTIFICATIONS`: 이메일 알림 활성화 (기본: False)
- `ENABLE_DISCORD_NOTIFICATIONS`: Discord 알림 활성화 (기본: False)

### 백테스팅 설정
- `ENABLE_BACKTESTING`: 백테스팅 활성화 (기본: True)
- `BACKTEST_WEEKS`: 백테스팅 기간 (기본: 4주 ≈ 한 달)
- `BACKTEST_INITIAL_CAPITAL`: 초기 자본금 (기본: $10,000)
- `RISK_FREE_RATE`: 무위험 수익률 (기본: 0.05 = 5%)

### 환경변수 설정 예시
```powershell
# 초대형주만 분석
$env:SCREENER_TYPES='mega'

# 백테스팅 기간 30주로 설정
$env:BACKTEST_WEEKS='30'

# 백테스팅 비활성화
$env:ENABLE_BACKTESTING='False'
```

## 🌐 웹 대시보드 (NEW!)

Streamlit 기반의 인터랙티브 웹 대시보드를 통해 데이터를 시각적으로 탐색하고 분석할 수 있습니다.

### 대시보드 기능

#### 1. 메인 대시보드
- 📊 실시간 상위 종목 테이블
- 📈 요약 통계 카드 (평균 수익률, 최고/최저 수익률)
- 🥧 포트폴리오 구성 파이 차트
- 🔍 기술적 분석 요약
- 💰 백테스팅 성과 지표
- 📉 성과 추이 그래프

#### 2. 종목 상세 분석 페이지
- 📊 캔들스틱 차트 + 이동평균선 (MA20/60/120)
- 🔍 기술적 지표 시각화
- 📈 종목별 상세 정보
- ⚙️ 차트 기간 조정 (1개월 ~ 2년)

#### 3. 백테스팅 결과 페이지
- 💵 포트폴리오 가치 변화 그래프
- 📊 일별 수익률 차트
- 📉 MDD (최대낙폭) 시각화
- 🎯 성과 지표 (샤프비율, 승률 등)
- 🏆 최고/최악의 거래일 하이라이트

#### 4. 히스토리 탐색 페이지
- 📅 날짜별 데이터 조회
- 📊 기간별 성과 비교
- 🔥 순위 변화 히트맵
- 📈 평균 수익률 추이 그래프

#### 5. 설정 및 관리 페이지
- ⚙️ 시스템 설정 확인
- 📧 알림 채널 상태
- 🔄 캐시 관리
- 📊 데이터 상태 확인

### 대시보드 실행 방법

```bash
# 웹 대시보드 실행
streamlit run src/dashboard/app.py
```

브라우저에서 자동으로 열리며, 수동으로는 `http://localhost:8501`로 접속하세요.

### 대시보드 특징

- ✨ **인터랙티브**: Plotly 기반 줌, 호버, 범례 기능
- 🎨 **깔끔한 UI**: Streamlit의 직관적인 인터페이스
- ⚡ **빠른 로딩**: 5분 캐싱으로 빠른 응답
- 📱 **반응형**: 다양한 화면 크기 지원
- 🔄 **실시간**: 데이터 새로고침 버튼

### 대시보드 스크린샷

메인 대시보드에서는:
- 상위 종목 한눈에 확인
- 기술적 분석 결과 즉시 파악
- 매매 신호 시각적으로 확인
- 백테스팅 성과 그래프로 확인

종목 상세 페이지에서는:
- 캔들스틱 차트로 가격 흐름 파악
- 이동평균선으로 추세 확인
- 기술적 지표 한눈에 확인

## 주요 기능 상세

### 💼 포트폴리오 구성
- **대형주 상위 5개** + **초대형주 상위 5개** = 총 10개 종목
- 각 종목당 10% 비중 (동일 가중)
- 매일 자동으로 포트폴리오 재조정
- 각 스크리너에서 상위 5개씩만 선별하여 품질 유지

### 🎯 매매 신호 (각 종목별 표시)
**🟢 매수/보유 신호:**
- 신고가 돌파 + 기술적 조건 만족 → 🟢 매수
- 기술적 조건 만족 (신고가 아님) → 🟢 보유

**🔴 매도 신호:**
- 트레일링 스탑 발동 (MA20 2일 이상 이탈) → 🔴 매도
- MA60 이탈 (전날 위 → 오늘 아래) → 🔴 매도

**🟡 관망:**
- 기술적 조건 미달 → 🟡 관망

### 🚀 신고가 돌파 (매수 신호)
- 3개월 최고가 실시간 추적
- 전날까지의 최고가를 현재가가 돌파하면 매수 신호
- 강한 상승 모멘텀 포착
- 예시: 전 최고가 $100 → 현재가 $102 → 2% 돌파 → 매수 신호

### 🔴 트레일링 스탑 (매도 신호)
- **MA20 (20일 이동평균선) 2일 이상 하향 이탈** 시 매도 신호
- 단기 추세 반전 신속 감지
- 손실을 최소화하고 수익 보호
- 예시: 
  - 1일차: 현재가 $100, MA20 $105 (MA20 아래)
  - 2일차: 현재가 $98, MA20 $104 (MA20 아래) → 매도 신호!

### 🚨 MA60 이탈 손절 신호
- 전날 60일선 위에 있었던 종목이 오늘 아래로 떨어지면 자동 경고
- 단기 추세 반전 감지
- 이탈 폭(%) 표시로 손실 정도 파악
- 손절 타이밍을 놓치지 않도록 도움

### 📊 기술적 분석 아이콘
- ✅ 모든 조건 만족 (강세)
- ⚠️ 부분 만족 (주의)
- ❌ 조건 미달 (약세)
- ❓ 데이터 없음

### 💰 백테스팅
- 매일 상위 10개 종목으로 리밸런싱
- 실제 역사적 가격으로 시뮬레이션
- 총 수익률, 연환산 수익률, MDD, 샤프비율, 승률 계산

### 🎯 매매 신호 시스템
**매수 신호:**
1. 🚀 **신고가 돌파**: 3개월 최고가 경신 → 강한 모멘텀
2. ✅ **기술적 조건 만족**: 현재가 > 60일선 > 120일선

**매도 신호:**
1. 🔴 **트레일링 스탑**: MA20을 2일 이상 하향 이탈 (즉시 매도)
2. 🚨 **MA60 이탈**: 60일선 하향 돌파 (손절 검토)

**자동 알림:** 모든 신호는 Telegram으로 실시간 전송

**트레일링 스탑 동작 원리:**
- Day 1: 현재가 < MA20 → 1일째 이탈 (대기)
- Day 2: 현재가 < MA20 → 2일째 이탈 → 🔴 매도 신호!

## 문제 해결

### 1. 데이터 수집 실패
- 인터넷 연결 확인
- Finviz 사이트 접근 가능 여부 확인
- User-Agent 헤더 업데이트

### 2. Telegram 전송 실패
- Bot Token이 정확한지 확인
- Chat ID가 정확한지 확인
- 봇에게 최소 한 번 메시지를 보냈는지 확인
- 네트워크 연결 확인
- `test_telegram.py`로 연결 테스트

### 3. 스케줄링 문제
- 시스템 시간 확인
- Python 경로 확인
- 작업 스케줄러 권한 확인

### 4. Chat ID를 찾을 수 없는 경우
1. 봇과 대화를 시작하고 아무 메시지나 전송
2. 다음 URL을 웹 브라우저에서 열기:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. 응답 JSON에서 `"chat":{"id":숫자}` 찾기
4. 또는 [@userinfobot](https://t.me/userinfobot)에게 메시지를 보내서 Chat ID 확인

## 라이선스

MIT License
