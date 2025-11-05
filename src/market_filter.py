"""
시장 필터 모듈 (Market Regime Filter)
SPY와 VIX를 활용하여 시장 약세장/강세장 판단
"""
import yfinance as yf
import json
from datetime import datetime, timedelta
from pathlib import Path
from logger import get_logger
from config import DATA_DIR, VIX_THRESHOLD

logger = get_logger()

def get_market_data(ticker, days=250):
    """
    yfinance를 사용하여 시장 데이터 가져오기
    
    Args:
        ticker: 티커 심볼 (예: '^GSPC' for S&P 500, '^VIX' for VIX)
        days: 과거 데이터 일수 (MA200 계산을 위해 최소 200일 필요)
    
    Returns:
        pandas.DataFrame: 가격 데이터
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            logger.error(f"{ticker}: 데이터를 가져올 수 없습니다.")
            return None
        
        logger.debug(f"{ticker}: {len(hist)}일치 데이터 로드")
        return hist
    except Exception as e:
        logger.error(f"{ticker} 데이터 가져오기 실패: {e}")
        return None

def calculate_moving_average(data, period):
    """
    이동평균선 계산
    
    Args:
        data: pandas.DataFrame (Close 컬럼 필요)
        period: 이동평균 기간 (예: 200, 120)
    
    Returns:
        float: 최신 이동평균값
    """
    if data is None or len(data) < period:
        logger.warning(f"MA{period} 계산을 위한 데이터가 충분하지 않습니다.")
        return None
    
    ma = data['Close'].rolling(window=period).mean()
    return ma.iloc[-1]

def check_market_regime(vix_threshold=20, use_cache=True):
    """
    시장 상태 체크 (약세장/강세장)
    
    조건:
    - SPY < MA200 OR (SPY < MA120 AND VIX > 20) → 약세장 (hold_cash = True)
    - 그 외 → 강세장 (hold_cash = False)
    
    Args:
        vix_threshold: VIX 임계값 (기본: 20)
        use_cache: 캐시 사용 여부
    
    Returns:
        dict: {
            'hold_cash': bool,
            'spy_price': float,
            'spy_ma200': float,
            'spy_ma120': float,
            'vix': float,
            'date': str,
            'reason': str
        }
    """
    cache_file = Path(DATA_DIR) / 'market_regime_cache.json'
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 캐시 확인
    if use_cache and cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if cache.get('date') == today:
                    logger.info("캐시된 시장 상태 사용")
                    return cache
        except Exception as e:
            logger.warning(f"캐시 읽기 실패: {e}")
    
    logger.info("시장 상태 분석 중...")
    
    # SPY (S&P 500) 데이터 가져오기
    spy_data = get_market_data('^GSPC', days=250)
    if spy_data is None:
        logger.error("SPY 데이터를 가져올 수 없습니다.")
        return None
    
    # VIX 데이터 가져오기
    vix_data = get_market_data('^VIX', days=30)
    if vix_data is None:
        logger.error("VIX 데이터를 가져올 수 없습니다.")
        return None
    
    # 현재 가격
    spy_price = spy_data['Close'].iloc[-1]
    vix = vix_data['Close'].iloc[-1]
    
    # 이동평균 계산
    spy_ma200 = calculate_moving_average(spy_data, 200)
    spy_ma120 = calculate_moving_average(spy_data, 120)
    
    if spy_ma200 is None or spy_ma120 is None:
        logger.error("이동평균 계산 실패")
        return None
    
    # 약세장 판단
    hold_cash = False
    reason = ""
    
    if spy_price < spy_ma200:
        hold_cash = True
        reason = "SPY < MA200 (약세장)"
        logger.warning(f"⚠️ 약세장 감지: {reason}")
    elif spy_price < spy_ma120 and vix > vix_threshold:
        hold_cash = True
        reason = f"SPY < MA120 AND VIX > {vix_threshold} (변동성 과열)"
        logger.warning(f"⚠️ 약세장 감지: {reason}")
    else:
        reason = "정상 (강세장)"
        logger.info(f"✅ 강세장: {reason}")
    
    # 결과 생성
    result = {
        'hold_cash': hold_cash,
        'spy_price': float(spy_price),
        'spy_ma200': float(spy_ma200),
        'spy_ma120': float(spy_ma120),
        'vix': float(vix),
        'vix_threshold': vix_threshold,
        'date': today,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reason': reason
    }
    
    # 캐시 저장
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info("시장 상태 캐시 저장")
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")
    
    return result

def get_historical_market_regime(date_str, vix_threshold=20):
    """
    특정 날짜의 시장 상태 체크 (백테스팅용)
    
    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)
        vix_threshold: VIX 임계값
    
    Returns:
        dict: 시장 상태 정보 (check_market_regime와 동일)
    """
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = target_date + timedelta(days=1)
        start_date = target_date - timedelta(days=250)
        
        # SPY 데이터 가져오기
        spy = yf.Ticker('^GSPC')
        spy_data = spy.history(start=start_date, end=end_date)
        
        if spy_data.empty or len(spy_data) < 200:
            logger.warning(f"{date_str}: SPY 데이터 부족")
            return None
        
        # VIX 데이터 가져오기
        vix = yf.Ticker('^VIX')
        vix_data = vix.history(start=start_date, end=end_date)
        
        if vix_data.empty:
            logger.warning(f"{date_str}: VIX 데이터 없음")
            return None
        
        # 해당 날짜의 가격
        spy_price = spy_data['Close'].iloc[-1]
        vix_value = vix_data['Close'].iloc[-1]
        
        # 이동평균 계산
        spy_ma200 = spy_data['Close'].rolling(window=200).mean().iloc[-1]
        spy_ma120 = spy_data['Close'].rolling(window=120).mean().iloc[-1]
        
        # 약세장 판단
        hold_cash = False
        reason = ""
        
        if spy_price < spy_ma200:
            hold_cash = True
            reason = "SPY < MA200 (약세장)"
        elif spy_price < spy_ma120 and vix_value > vix_threshold:
            hold_cash = True
            reason = f"SPY < MA120 AND VIX > {vix_threshold} (변동성 과열)"
        else:
            reason = "정상 (강세장)"
        
        return {
            'hold_cash': hold_cash,
            'spy_price': float(spy_price),
            'spy_ma200': float(spy_ma200),
            'spy_ma120': float(spy_ma120),
            'vix': float(vix_value),
            'vix_threshold': vix_threshold,
            'date': date_str,
            'reason': reason
        }
    except Exception as e:
        logger.error(f"{date_str} 시장 상태 체크 실패: {e}")
        return None

if __name__ == "__main__":
    # 테스트
    print("=== 시장 필터 테스트 ===")
    result = check_market_regime(use_cache=False)
    
    if result:
        print(f"\n날짜: {result['date']}")
        print(f"SPY 가격: ${result['spy_price']:.2f}")
        print(f"SPY MA200: ${result['spy_ma200']:.2f}")
        print(f"SPY MA120: ${result['spy_ma120']:.2f}")
        print(f"VIX: {result['vix']:.2f}")
        print(f"\n약세장 여부: {'예' if result['hold_cash'] else '아니오'}")
        print(f"사유: {result['reason']}")
    else:
        print("시장 상태를 가져올 수 없습니다.")


