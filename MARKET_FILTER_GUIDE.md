# 시장 필터 (Market Regime Filter) 가이드

## 개요

시장 필터는 SPY(S&P 500)와 VIX(공포지수)를 활용하여 시장 약세장/강세장을 자동으로 감지하고, 매수 금지 또는 현금 보유 신호를 제공하는 기능입니다.

## 핵심 로직

```python
if SPY < MA200 or (SPY < MA120 and VIX > 20):
    hold_cash = True   # 매수 금지
else:
    hold_cash = False  # 정상 매수
```

### 약세장 조건
1. **조건 1**: SPY 가격이 200일 이동평균선(MA200) 아래
2. **조건 2**: SPY 가격이 120일 이동평균선(MA120) 아래 **AND** VIX가 20 초과

둘 중 하나라도 만족하면 **약세장**으로 판단합니다.

## 주요 기능

### 1. 실시간 알림 (Telegram)
- 매일 아침 시장 상태를 Telegram으로 알림
- 약세장일 때: "⚠️ 약세장 감지 - 매수 금지" 경고
- 강세장일 때: "✅ 정상 시장 - 매수 가능" 메시지
- SPY, VIX, MA200, MA120 현재값 표시

### 2. 백테스팅 적용
- 백테스팅 시뮬레이션에 시장 필터 자동 적용
- 약세장일 때는 현금 보유 (포트폴리오 가치 동결)
- 강세장 복귀 시 정상 매매 재개
- 성과 지표에 **현금 보유 일수** 및 **비율** 추가

### 3. 대시보드 시각화
- 메인 대시보드 상단에 시장 상태 섹션 표시
- SPY vs MA200/MA120 차트
- VIX 과열 여부 표시
- 실시간 업데이트 시간 표시

## 설정

### config.py
```python
# 시장 필터 설정
ENABLE_MARKET_FILTER = True  # 시장 필터 활성화
VIX_THRESHOLD = 20           # VIX 임계값 (기본: 20)
```

### 환경 변수 (.env)
```bash
ENABLE_MARKET_FILTER=True
VIX_THRESHOLD=20
```

## 사용법

### 1. 시장 필터 테스트
```bash
python test_market_filter.py
```

출력 예시:
```
📅 날짜: 2025-11-02
💰 SPY 가격: $580.25
📊 SPY MA200: $520.18
📊 SPY MA120: $545.30
📈 VIX: 15.42

🔍 판단: 정상 (강세장)
✅ **정상 시장 - 매수 가능**
```

### 2. 메인 스크립트 실행
```bash
python main.py
```

시장 필터가 자동으로 체크되어:
- Telegram 알림에 시장 상태 포함
- 백테스팅에서 약세장 시 현금 보유 적용

### 3. 대시보드 확인
```bash
python run_dashboard.py
```

대시보드 상단에 시장 상태 섹션이 표시됩니다.

## 데이터 소스

- **SPY**: `^GSPC` (S&P 500 Index) via yfinance
- **VIX**: `^VIX` (CBOE Volatility Index) via yfinance

## 캐싱

시장 데이터는 매일 한 번만 조회하여 `daily_data/market_regime_cache.json`에 저장됩니다.

캐시 파일 예시:
```json
{
  "hold_cash": false,
  "spy_price": 580.25,
  "spy_ma200": 520.18,
  "spy_ma120": 545.30,
  "vix": 15.42,
  "vix_threshold": 20,
  "date": "2025-11-02",
  "timestamp": "2025-11-02 09:00:00",
  "reason": "정상 (강세장)"
}
```

## 백테스팅 결과 해석

백테스팅 결과에 다음 정보가 추가됩니다:

```json
{
  "total_return": 15.5,
  "annualized_return": 22.3,
  "mdd": -12.4,
  "sharpe_ratio": 1.85,
  "cash_holding_days": 45,
  "cash_holding_ratio": 15.2
}
```

- `cash_holding_days`: 약세장으로 현금 보유한 일수
- `cash_holding_ratio`: 전체 거래일 대비 현금 보유 비율 (%)

### 해석 예시
- 총 300일 거래 중 45일 현금 보유 → 15.2%
- 약세장 기간 동안 손실을 회피하여 MDD 감소 효과

## 대시보드 화면

### 시장 상태 섹션
- **정상 시장**: 녹색 배너 "✅ 정상 시장 - 매수 가능"
- **약세장**: 빨간색 배너 "⚠️ 약세장 감지 - 매수 금지"

### 메트릭
1. SPY 가격 (현재값)
2. MA200 (200일 이동평균)
3. MA120 (120일 이동평균)
4. VIX (공포지수)

### 차트
SPY vs MA200/MA120 비교 바 차트

## 주의사항

1. **데이터 지연**: yfinance는 실시간이 아닌 일봉 데이터를 제공합니다.
2. **장 마감 후 업데이트**: 시장 데이터는 장 마감 후에 최신 데이터로 업데이트됩니다.
3. **네트워크 필요**: 인터넷 연결이 필요합니다 (yfinance API).
4. **백테스팅 성능**: 히스토리 백테스팅 시 각 날짜마다 시장 데이터를 조회하므로 시간이 걸릴 수 있습니다.

## 문제 해결

### 시장 데이터를 가져올 수 없습니다
- 인터넷 연결 확인
- yfinance 라이브러리 업데이트: `pip install --upgrade yfinance`

### 캐시 강제 갱신
```python
from market_filter import check_market_regime
result = check_market_regime(use_cache=False)
```

### VIX 임계값 변경
```python
# config.py
VIX_THRESHOLD = 25  # 더 보수적인 설정
```

## 참고 자료

- [S&P 500 Index (^GSPC)](https://finance.yahoo.com/quote/%5EGSPC)
- [VIX Index (^VIX)](https://finance.yahoo.com/quote/%5EVIX)
- [yfinance Documentation](https://pypi.org/project/yfinance/)

## 향후 개선 계획

- [ ] 다양한 시장 지표 추가 (RSI, MACD 등)
- [ ] 백테스팅 결과 비교 (시장 필터 적용 전/후)
- [ ] 알림 레벨 설정 (critical, warning, info)
- [ ] 멀티 타임프레임 분석 (일봉, 주봉)


