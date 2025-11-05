# 기술적 분석 모듈 - 이동평균선 분석
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger()

def get_moving_averages(ticker, period="6mo"):
    """
    yfinance로 역사적 가격 데이터를 가져와서 이동평균 계산
    
    Args:
        ticker: 종목 티커
        period: 가져올 기간 (기본 6개월 - 120일선 계산에 충분)
                "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
    
    Returns:
        DataFrame with price history or None
    """
    try:
        # yfinance Ticker 객체 생성
        stock = yf.Ticker(ticker)
        
        # 역사적 데이터 가져오기 (period 사용)
        hist = stock.history(period=period)
        
        if hist.empty:
            logger.warning(f"{ticker}: 역사적 데이터가 없습니다.")
            return None
        
        logger.debug(f"{ticker}: {len(hist)}일치 데이터 가져옴")
        
        return hist
    
    except Exception as e:
        logger.error(f"{ticker}: 데이터 가져오기 실패 - {e}")
        return None

def calculate_atr(ticker, period=14):
    """
    ATR (Average True Range) 계산
    
    Args:
        ticker: 종목 티커
        period: ATR 계산 기간 (기본 14일)
    
    Returns:
        dict: {
            'atr': ATR 값,
            'atr_pct': ATR 퍼센트 (ATR/현재가),
            'current_price': 현재가
        } or None
    """
    try:
        # 충분한 데이터 가져오기 (ATR은 14일+1 필요)
        hist = get_moving_averages(ticker, period="1mo")
        
        if hist is None or len(hist) < period + 1:
            logger.warning(f"{ticker}: ATR 계산을 위한 충분한 데이터가 없습니다.")
            return None
        
        # True Range 계산
        # TR = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
        high_low = hist['High'] - hist['Low']
        high_prev_close = abs(hist['High'] - hist['Close'].shift(1))
        low_prev_close = abs(hist['Low'] - hist['Close'].shift(1))
        
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        
        # ATR = True Range의 이동평균
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        current_price = hist['Close'].iloc[-1]
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0
        
        logger.debug(f"{ticker}: ATR={atr:.2f}, ATR%={atr_pct:.2f}%, Price=${current_price:.2f}")
        
        return {
            'atr': atr,
            'atr_pct': atr_pct,
            'current_price': current_price
        }
    
    except Exception as e:
        logger.error(f"{ticker}: ATR 계산 실패 - {e}")
        return None

def calculate_ma20_slope(ticker):
    """
    MA20 기울기 계산
    
    Args:
        ticker: 종목 티커
    
    Returns:
        dict: {
            'ma20_today': 오늘 MA20,
            'ma20_yesterday': 어제 MA20,
            'slope': 기울기 (퍼센트),
            'is_declining': 하락 추세 여부 (slope ≤ 0)
        } or None
    """
    try:
        # 최소 21일 데이터 필요 (MA20 + 1일)
        hist = get_moving_averages(ticker, period="2mo")
        
        if hist is None or len(hist) < 21:
            logger.warning(f"{ticker}: MA20 기울기 계산을 위한 충분한 데이터가 없습니다.")
            return None
        
        # MA20 계산
        ma20 = hist['Close'].rolling(window=20).mean()
        
        if len(ma20) < 2:
            return None
        
        ma20_today = ma20.iloc[-1]
        ma20_yesterday = ma20.iloc[-2]
        
        # 기울기 계산 (퍼센트 변화)
        slope = ((ma20_today - ma20_yesterday) / ma20_yesterday) * 100 if ma20_yesterday > 0 else 0
        is_declining = slope <= 0
        
        logger.debug(f"{ticker}: MA20 오늘={ma20_today:.2f}, 어제={ma20_yesterday:.2f}, 기울기={slope:.3f}%")
        
        return {
            'ma20_today': ma20_today,
            'ma20_yesterday': ma20_yesterday,
            'slope': slope,
            'is_declining': is_declining
        }
    
    except Exception as e:
        logger.error(f"{ticker}: MA20 기울기 계산 실패 - {e}")
        return None

def calculate_ma_status(ticker):
    """
    종목의 이동평균선 분석 수행
    
    Args:
        ticker: 종목 티커
    
    Returns:
        dict: {
            'price': 현재가,
            'ma20': 20일 이동평균,
            'ma60': 60일 이동평균,
            'ma120': 120일 이동평균,
            'above_ma20': 현재가 > 20일선,
            'above_ma60': 현재가 > 60일선,
            'above_ma120': 현재가 > 120일선,
            'ma60_above_ma120': 60일선 > 120일선,
            'all_conditions_met': 모든 조건 만족 여부,
            'status': 'success' or 'error'
        }
    """
    result = {
        'price': None,
        'ma20': None,
        'ma60': None,
        'ma120': None,
        'above_ma20': False,
        'above_ma60': False,
        'above_ma120': False,
        'ma60_above_ma120': False,
        'all_conditions_met': False,
        'status': 'error'
    }
    
    try:
        # 역사적 데이터 가져오기 (6개월 = 약 130영업일)
        hist = get_moving_averages(ticker, period="6mo")
        
        if hist is None or len(hist) < 120:
            logger.warning(f"{ticker}: 충분한 데이터가 없습니다 (필요: 120일, 보유: {len(hist) if hist is not None else 0}일)")
            return result
        
        # 현재가 (가장 최근 종가)
        current_price = hist['Close'].iloc[-1]
        
        # 20일 이동평균
        ma20 = hist['Close'].tail(20).mean()
        
        # 60일 이동평균
        ma60 = hist['Close'].tail(60).mean()
        
        # 120일 이동평균
        ma120 = hist['Close'].tail(120).mean()
        
        # 조건 체크
        above_ma20 = current_price > ma20
        above_ma60 = current_price > ma60
        above_ma120 = current_price > ma120
        ma60_above_ma120 = ma60 > ma120
        
        # 모든 조건 만족 여부
        all_conditions = above_ma60 and above_ma120 and ma60_above_ma120
        
        result = {
            'price': round(current_price, 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'ma120': round(ma120, 2),
            'above_ma20': above_ma20,
            'above_ma60': above_ma60,
            'above_ma120': above_ma120,
            'ma60_above_ma120': ma60_above_ma120,
            'all_conditions_met': all_conditions,
            'status': 'success'
        }
        
        logger.info(f"{ticker}: 현재가=${current_price:.2f}, MA20=${ma20:.2f}, MA60=${ma60:.2f}, MA120=${ma120:.2f}, 조건충족={all_conditions}")
        
        return result
    
    except Exception as e:
        logger.error(f"{ticker}: 이동평균 계산 실패 - {e}")
        return result

def analyze_top10_technical(df):
    """
    상위 5개 종목의 기술적 분석을 일괄 처리
    
    Args:
        df: Finviz에서 가져온 DataFrame
    
    Returns:
        dict: {ticker: ma_status_result}
    """
    top10 = df.head(5)
    technical_analysis = {}
    
    logger.info("=== 상위 5개 종목 기술적 분석 시작 ===")
    
    for i, row in top10.iterrows():
        ticker = row['Ticker']
        logger.info(f"분석 중: {ticker} ({i+1}/5)")
        
        # 각 종목의 이동평균선 분석
        ma_status = calculate_ma_status(ticker)
        technical_analysis[ticker] = ma_status
    
    logger.info("=== 기술적 분석 완료 ===")
    
    # 요약 통계
    success_count = sum(1 for v in technical_analysis.values() if v['status'] == 'success')
    all_conditions_count = sum(1 for v in technical_analysis.values() if v.get('all_conditions_met', False))
    
    logger.info(f"분석 성공: {success_count}/10, 모든 조건 만족: {all_conditions_count}/10")
    
    return technical_analysis

def get_technical_icon(ma_status):
    """
    이동평균선 분석 결과에 따른 아이콘 반환
    
    Args:
        ma_status: calculate_ma_status()의 결과
    
    Returns:
        str: 아이콘 문자열
    """
    if ma_status['status'] != 'success':
        return '❓'  # 데이터 없음
    
    if ma_status['all_conditions_met']:
        return '✅'  # 모든 조건 만족
    
    # 부분 만족 체크
    conditions_met = sum([
        ma_status['above_ma60'],
        ma_status['above_ma120'],
        ma_status['ma60_above_ma120']
    ])
    
    if conditions_met >= 1:
        return '⚠️'  # 부분 만족
    
    return '❌'  # 조건 미달

def format_technical_detail(ticker, ma_status):
    """
    기술적 분석 상세 정보를 텍스트로 포맷팅
    
    Args:
        ticker: 종목 티커
        ma_status: calculate_ma_status()의 결과
    
    Returns:
        str: 포맷된 텍스트
    """
    if ma_status['status'] != 'success':
        return f"{ticker}: 데이터 없음"
    
    text = f"{ticker}:\n"
    text += f"  • 현재가: ${ma_status['price']:.2f}\n"
    text += f"  • 60일선: ${ma_status['ma60']:.2f} {'✅' if ma_status['above_ma60'] else '❌'}\n"
    text += f"  • 120일선: ${ma_status['ma120']:.2f} {'✅' if ma_status['above_ma120'] else '❌'}\n"
    text += f"  • 60일선 > 120일선: {'✅' if ma_status['ma60_above_ma120'] else '❌'}\n"
    
    return text

def detect_ma60_breaks(current_technical, previous_technical):
    """
    MA60 이탈 종목 감지 (손절 신호)
    
    Args:
        current_technical: 현재 기술적 분석 결과
        previous_technical: 전날 기술적 분석 결과
    
    Returns:
        list: MA60 이탈한 종목 리스트 [{ticker, current_price, ma60, previous_above}]
    """
    if not current_technical or not previous_technical:
        return []
    
    ma60_breaks = []
    
    for ticker in current_technical:
        current = current_technical[ticker]
        
        # 현재 데이터가 유효한지 확인
        if current['status'] != 'success':
            continue
        
        # 전날 데이터가 있는지 확인
        if ticker not in previous_technical:
            continue
        
        previous = previous_technical[ticker]
        if previous['status'] != 'success':
            continue
        
        # 전날에는 MA60 위, 오늘은 MA60 아래 → 손절 신호
        if previous['above_ma60'] and not current['above_ma60']:
            ma60_breaks.append({
                'ticker': ticker,
                'current_price': current['price'],
                'ma60': current['ma60'],
                'distance': ((current['price'] - current['ma60']) / current['ma60']) * 100,
                'previous_above': previous['above_ma60']
            })
            logger.warning(f"⚠️ {ticker} MA60 이탈 감지! 현재가=${current['price']:.2f}, MA60=${current['ma60']:.2f}")
    
    return ma60_breaks

def detect_trailing_stops(current_technical, previous_technical):
    """
    트레일링 스탑 신호 감지 (개선된 조건)
    
    조건: 버퍼(min 1% or 0.5×ATR/가격) + 2일 연속 + MA20 기울기 ≤ 0
    
    Args:
        current_technical: 현재 기술적 분석 결과
        previous_technical: 전날 기술적 분석 결과
    
    Returns:
        list: 트레일링 스탑 조건을 만족하는 종목 리스트
    """
    if not current_technical or not previous_technical:
        logger.warning("트레일링 스탑 감지: 현재 또는 전날 데이터 없음")
        return []
    
    trailing_stops = []
    
    logger.info("=== 트레일링 스탑 감지 (버퍼 + 2일 연속 + MA20 기울기) ===")
    
    for ticker in current_technical:
        current = current_technical[ticker]
        
        # 현재 데이터가 유효한지 확인
        if current['status'] != 'success':
            continue
        
        # 전날 데이터가 있는지 확인
        if ticker not in previous_technical:
            continue
        
        previous = previous_technical[ticker]
        if previous['status'] != 'success':
            continue
        
        current_price = current['price']
        ma20 = current['ma20']
        
        # 1. ATR 기반 버퍼 계산
        atr_info = calculate_atr(ticker)
        if atr_info:
            # 버퍼 = max(1%, 0.5 × ATR%)
            atr_buffer = 0.5 * atr_info['atr_pct']
            buffer_pct = max(1.0, atr_buffer)
        else:
            # ATR 계산 실패 시 기본 1%
            buffer_pct = 1.0
            atr_info = {'atr': 0, 'atr_pct': 0}
        
        # MA20에서 버퍼만큼 뺀 값
        ma20_with_buffer = ma20 * (1 - buffer_pct / 100)
        
        # 2. 2일 연속 조건 체크 (현재가 < MA20 - 버퍼)
        current_below_buffer = current_price < ma20_with_buffer
        previous_below_buffer = previous['price'] < (previous['ma20'] * (1 - buffer_pct / 100))
        
        if not (current_below_buffer and previous_below_buffer):
            logger.debug(f"{ticker}: 버퍼 조건 미충족 (현재={current_below_buffer}, 전날={previous_below_buffer})")
            continue
        
        # 3. MA20 기울기 체크
        ma20_slope_info = calculate_ma20_slope(ticker)
        if not ma20_slope_info:
            logger.debug(f"{ticker}: MA20 기울기 계산 실패")
            continue
        
        if not ma20_slope_info['is_declining']:
            logger.debug(f"{ticker}: MA20 기울기 양수 (기울기={ma20_slope_info['slope']:.3f}%)")
            continue
        
        # 모든 조건 충족 → 트레일링 스탑 신호
        distance = ((current_price - ma20) / ma20) * 100
        
        trailing_stops.append({
            'ticker': ticker,
            'current_price': current_price,
            'ma20': ma20,
            'ma20_with_buffer': ma20_with_buffer,
            'buffer_pct': round(buffer_pct, 2),
            'atr': round(atr_info['atr'], 2),
            'atr_pct': round(atr_info['atr_pct'], 2),
            'ma20_slope': round(ma20_slope_info['slope'], 3),
            'distance': round(distance, 2),
            'days_below': 2  # 최소 2일
        })
        logger.warning(f"🔴 {ticker} 트레일링 스탑! 가격=${current_price:.2f}, MA20=${ma20:.2f}, "
                      f"버퍼={buffer_pct:.2f}%, MA20기울기={ma20_slope_info['slope']:.3f}%")
    
    if not trailing_stops:
        logger.info("트레일링 스탑 조건을 만족하는 종목이 없습니다.")
    
    return trailing_stops

def detect_breakout_highs(df):
    """
    3개월 신고가 돌파 종목 감지 (매수 신호)
    
    Args:
        df: 현재 DataFrame (상위 10개 종목)
    
    Returns:
        list: 신고가를 돌파한 종목 리스트
    """
    breakout_highs = []
    top10 = df.head(5)
    
    logger.info("=== 3개월 신고가 돌파 감지 ===")
    
    for i, row in top10.iterrows():
        ticker = row['Ticker']
        
        try:
            # 3개월 가격 데이터 가져오기
            hist = get_moving_averages(ticker, period="3mo")
            
            if hist is None or len(hist) < 10:
                logger.debug(f"{ticker}: 신고가 분석을 위한 데이터 부족")
                continue
            
            # 현재가 (가장 최근 종가)
            current_price = hist['Close'].iloc[-1]
            
            # 전날까지의 3개월 최고가
            previous_high = hist['High'].iloc[:-1].max() if len(hist) > 1 else hist['High'].max()
            
            # 오늘 최고가
            today_high = hist['High'].iloc[-1]
            
            # 신고가 돌파 조건: 현재가가 전날까지의 최고가보다 높음
            if current_price > previous_high:
                breakout_percent = ((current_price - previous_high) / previous_high) * 100
                
                breakout_highs.append({
                    'ticker': ticker,
                    'current_price': round(current_price, 2),
                    'previous_high': round(previous_high, 2),
                    'today_high': round(today_high, 2),
                    'breakout_percent': round(breakout_percent, 2)
                })
                logger.info(f"🚀 {ticker} 신고가 돌파! 현재가=${current_price:.2f}, 전 최고가=${previous_high:.2f}, 돌파율={breakout_percent:.1f}%")
            else:
                logger.debug(f"{ticker}: 현재가=${current_price:.2f}, 최고가=${previous_high:.2f}, 차이={((current_price - previous_high) / previous_high) * 100:.1f}%")
        
        except Exception as e:
            logger.error(f"{ticker}: 신고가 분석 실패 - {e}")
            continue
    
    if breakout_highs:
        logger.info(f"🚀 신고가 돌파 종목 {len(breakout_highs)}개 감지!")
    else:
        logger.info("신고가 돌파 종목 없음")
    
    return breakout_highs

