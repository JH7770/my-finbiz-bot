# 포트폴리오 백테스팅 모듈
import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from logger import get_logger
from config import DATA_DIR, BACKTEST_WEEKS, BACKTEST_INITIAL_CAPITAL, RISK_FREE_RATE, ENABLE_MARKET_FILTER, VIX_THRESHOLD

logger = get_logger()

def load_historical_portfolio_data(screener_type="large"):
    """daily_data 폴더에서 역사적 CSV 파일들을 로드
    
    Args:
        screener_type: 'large' 또는 'mega'
    """
    data_path = Path(DATA_DIR)
    # 파일명 패턴: finviz_data_large_2025-10-27.csv 또는 finviz_data_mega_2025-10-27.csv
    csv_files = sorted(data_path.glob(f'finviz_data_{screener_type}_*.csv'))
    
    historical_data = {}
    for csv_file in csv_files:
        try:
            # 파일명에서 날짜 추출 (finviz_data_large_2025-10-27.csv)
            date_str = csv_file.stem.replace(f'finviz_data_{screener_type}_', '')
            
            # CSV 읽기
            df = pd.read_csv(csv_file)
            
            # 상위 10개 종목만 저장
            top10 = df.head(10)
            historical_data[date_str] = top10
            
            logger.debug(f"{date_str}: {len(top10)}개 종목 로드")
        except Exception as e:
            logger.warning(f"{csv_file} 로드 실패: {e}")
    
    logger.info(f"총 {len(historical_data)}일치 역사적 데이터 로드")
    return historical_data

def get_daily_rebalance_dates(start_date, end_date, available_dates):
    """시작일과 종료일 사이의 매일 날짜 리스트 생성 (실제 데이터가 있는 날만)"""
    dates = []
    current = start_date
    
    # 사용 가능한 날짜를 datetime으로 변환
    available_dt = [datetime.strptime(d, '%Y-%m-%d') for d in available_dates]
    
    # 시작일부터 종료일까지 매일 체크
    while current <= end_date:
        # 실제 데이터가 있는 날짜만 포함
        if current in available_dt:
            dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates

def get_closest_date(target_date, available_dates):
    """사용 가능한 날짜 중 target_date에 가장 가까운 날짜 찾기"""
    target = datetime.strptime(target_date, '%Y-%m-%d')
    available = [datetime.strptime(d, '%Y-%m-%d') for d in available_dates]
    
    if not available:
        return None
    
    # 가장 가까운 날짜 찾기 (과거 우선)
    past_dates = [d for d in available if d <= target]
    if past_dates:
        return max(past_dates).strftime('%Y-%m-%d')
    else:
        # 과거 날짜가 없으면 미래 날짜 중 가장 가까운 것
        return min(available).strftime('%Y-%m-%d')

def get_price_data(tickers, start_date, end_date):
    """yfinance로 여러 종목의 가격 데이터 가져오기"""
    price_data = {}
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if not hist.empty:
                price_data[ticker] = hist['Close']
                logger.debug(f"{ticker}: {len(hist)}일치 가격 데이터")
            else:
                logger.warning(f"{ticker}: 가격 데이터 없음")
        except Exception as e:
            logger.error(f"{ticker}: 가격 데이터 가져오기 실패 - {e}")
    
    return price_data

def simulate_portfolio_flexible(historical_data, params=None):
    """
    파라미터화된 포트폴리오 백테스팅 시뮬레이션
    
    Args:
        historical_data: load_historical_portfolio_data()의 결과
        params: 백테스팅 파라미터 딕셔너리
            - weeks: 백테스팅 기간 (주)
            - initial_capital: 초기 자본금
            - num_stocks: 포트폴리오 종목 수 (5, 10, 15)
            - rebalance_frequency: 'daily' 또는 'weekly'
            - weight_method: 'equal', 'market_cap', 'momentum'
            - enable_market_filter: True/False
            - start_date: 시작 날짜 (옵션, YYYY-MM-DD)
            - end_date: 종료 날짜 (옵션, YYYY-MM-DD)
    
    Returns:
        백테스팅 결과 딕셔너리 (portfolio_history, daily_returns 포함)
    """
    # 기본 파라미터
    default_params = {
        'weeks': 4,
        'initial_capital': 10000,
        'num_stocks': 5,
        'rebalance_frequency': 'daily',
        'weight_method': 'equal',
        'enable_market_filter': ENABLE_MARKET_FILTER,
        'start_date': None,
        'end_date': None
    }
    
    if params:
        default_params.update(params)
    
    params = default_params
    
    if not historical_data:
        logger.warning("역사적 데이터가 없습니다.")
        return None
    
    # 날짜 정렬
    dates = sorted(historical_data.keys())
    
    if len(dates) < 2:
        logger.warning("백테스팅을 위한 충분한 데이터가 없습니다.")
        return None
    
    # 기간 설정
    if params['end_date']:
        end_date = datetime.strptime(params['end_date'], '%Y-%m-%d')
    else:
        end_date = datetime.strptime(dates[-1], '%Y-%m-%d')
    
    if params['start_date']:
        start_date = datetime.strptime(params['start_date'], '%Y-%m-%d')
    else:
        start_date = end_date - timedelta(weeks=params['weeks'])
    
    # 리밸런싱 날짜 생성
    if params['rebalance_frequency'] == 'daily':
        rebalance_dates = get_daily_rebalance_dates(start_date, end_date, dates)
    else:  # weekly
        rebalance_dates = get_weekly_rebalance_dates(start_date, end_date, dates)
    
    if len(rebalance_dates) < 2:
        logger.warning("백테스팅을 위한 충분한 리밸런싱 날짜가 없습니다.")
        return None
    
    logger.info(f"백테스팅 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"리밸런싱 주기: {params['rebalance_frequency']}, 날짜 수: {len(rebalance_dates)}일")
    logger.info(f"종목 수: {params['num_stocks']}, 비중 방식: {params['weight_method']}")
    
    # 시장 필터 활성화 여부
    if params['enable_market_filter']:
        logger.info("시장 필터 활성화 - 약세장 시 현금 보유")
    
    # 포트폴리오 시뮬레이션
    portfolio_value = params['initial_capital']
    portfolio_history = []
    daily_returns = []
    cash_holding_days = 0
    
    for i in range(len(rebalance_dates) - 1):
        rebalance_date = rebalance_dates[i]
        next_rebalance_date = rebalance_dates[i + 1]
        
        # 시장 필터 체크
        hold_cash = False
        if params['enable_market_filter']:
            from market_filter import get_historical_market_regime
            market_regime = get_historical_market_regime(rebalance_date, VIX_THRESHOLD)
            if market_regime and market_regime.get('hold_cash', False):
                hold_cash = True
                cash_holding_days += 1
                logger.debug(f"{rebalance_date}: 약세장 - 현금 보유 ({market_regime.get('reason', '')})")
        
        # 약세장일 때는 현금 보유
        if hold_cash:
            portfolio_history.append(portfolio_value)
            daily_returns.append({
                'date': rebalance_date,
                'return': 0.0,
                'value': portfolio_value
            })
            continue
        
        # 해당 날짜의 종목 데이터
        if rebalance_date not in historical_data:
            logger.warning(f"{rebalance_date}: 데이터 없음, 스킵")
            continue
        
        df = historical_data[rebalance_date]
        top_stocks = df.head(params['num_stocks'])
        tickers = top_stocks['Ticker'].tolist()
        
        logger.debug(f"{rebalance_date} 리밸런싱: {', '.join(tickers[:3])}...")
        
        # 비중 계산
        weights = calculate_weights(top_stocks, params['weight_method'])
        
        # 다음 날까지의 수익률 계산
        try:
            next_date = datetime.strptime(next_rebalance_date, '%Y-%m-%d')
            extended_end = (next_date + timedelta(days=2)).strftime('%Y-%m-%d')
            
            price_data = get_price_data(tickers, start_date=rebalance_date, end_date=extended_end)
            
            if not price_data:
                logger.warning(f"{rebalance_date}: 가격 데이터 없음")
                continue
            
            # 각 종목의 수익률 계산
            day_return = 0
            for idx, ticker in enumerate(tickers):
                if ticker not in price_data or len(price_data[ticker]) < 2:
                    continue
                
                buy_price = price_data[ticker].iloc[0]
                sell_price = price_data[ticker].iloc[1] if len(price_data[ticker]) > 1 else price_data[ticker].iloc[0]
                
                stock_return = (sell_price - buy_price) / buy_price if buy_price != 0 else 0
                day_return += stock_return * weights[idx]
            
            # 포트폴리오 가치 업데이트
            new_value = portfolio_value * (1 + day_return)
            daily_returns.append({
                'date': rebalance_date,
                'return': day_return * 100,
                'value': new_value
            })
            
            logger.debug(f"{rebalance_date}: 수익률 {day_return*100:.2f}%, 가치 ${portfolio_value:.2f} → ${new_value:.2f}")
            
            portfolio_history.append(portfolio_value)
            portfolio_value = new_value
            
        except Exception as e:
            logger.error(f"{rebalance_date}: 수익률 계산 실패 - {e}")
            continue
    
    # 최종 포트폴리오 가치
    portfolio_history.append(portfolio_value)
    
    if len(portfolio_history) < 2:
        logger.warning("백테스팅 결과가 충분하지 않습니다.")
        return None
    
    # 성과 지표 계산
    result = calculate_performance_metrics(
        initial_capital=params['initial_capital'],
        final_value=portfolio_value,
        portfolio_history=portfolio_history,
        daily_returns=daily_returns,
        start_date=rebalance_dates[0],
        end_date=rebalance_dates[-1],
        num_rebalances=len(rebalance_dates) - 1,
        cash_holding_days=cash_holding_days
    )
    
    # 상세 데이터 추가
    result['portfolio_history'] = portfolio_history
    result['daily_returns'] = daily_returns
    result['params'] = params
    
    return result


def calculate_weights(df, weight_method='equal'):
    """
    종목 비중 계산
    
    Args:
        df: 종목 데이터프레임
        weight_method: 'equal', 'market_cap', 'momentum'
    
    Returns:
        list: 비중 리스트 (합계 1.0)
    """
    num_stocks = len(df)
    
    if weight_method == 'equal':
        # 동일 비중
        return [1.0 / num_stocks] * num_stocks
    
    elif weight_method == 'market_cap':
        # 시가총액 가중 (Market Cap 컬럼 사용)
        if 'Market Cap' not in df.columns:
            logger.warning("Market Cap 컬럼이 없습니다. 동일 비중 사용")
            return [1.0 / num_stocks] * num_stocks
        
        # Market Cap 파싱 (예: 125.5B -> 125.5e9)
        market_caps = []
        for cap_str in df['Market Cap']:
            try:
                cap_str = str(cap_str).strip()
                if cap_str.endswith('B'):
                    cap = float(cap_str[:-1]) * 1e9
                elif cap_str.endswith('M'):
                    cap = float(cap_str[:-1]) * 1e6
                else:
                    cap = float(cap_str)
                market_caps.append(cap)
            except:
                market_caps.append(1.0)
        
        total_cap = sum(market_caps)
        if total_cap == 0:
            return [1.0 / num_stocks] * num_stocks
        
        weights = [cap / total_cap for cap in market_caps]
        return weights
    
    elif weight_method == 'momentum':
        # 모멘텀 가중 (Perf Quart 컬럼 사용)
        if 'Perf Quart' not in df.columns:
            logger.warning("Perf Quart 컬럼이 없습니다. 동일 비중 사용")
            return [1.0 / num_stocks] * num_stocks
        
        # 성과 파싱
        perfs = []
        for perf_str in df['Perf Quart']:
            try:
                perf = float(str(perf_str).replace('%', '').strip())
                # 음수 성과는 0으로 처리
                perfs.append(max(0, perf))
            except:
                perfs.append(0)
        
        total_perf = sum(perfs)
        if total_perf == 0:
            return [1.0 / num_stocks] * num_stocks
        
        weights = [perf / total_perf for perf in perfs]
        return weights
    
    else:
        return [1.0 / num_stocks] * num_stocks


def get_weekly_rebalance_dates(start_date, end_date, available_dates):
    """주간 리밸런싱 날짜 생성 (매주 첫 거래일)"""
    dates = []
    available_dt = [datetime.strptime(d, '%Y-%m-%d') for d in available_dates]
    
    current = start_date
    while current <= end_date:
        # 해당 주의 첫 거래일 찾기
        week_start = current
        week_end = current + timedelta(days=7)
        
        # 해당 주에 사용 가능한 날짜 찾기
        week_dates = [d for d in available_dt if week_start <= d < week_end]
        if week_dates:
            dates.append(week_dates[0].strftime('%Y-%m-%d'))
        
        current = week_end
    
    return dates


def simulate_portfolio(historical_data, weeks=4, initial_capital=10000):
    """
    포트폴리오 백테스팅 시뮬레이션 (매일 리밸런싱)
    레거시 호환성을 위한 래퍼 함수
    
    Args:
        historical_data: load_historical_portfolio_data()의 결과
        weeks: 백테스팅 기간 (주)
        initial_capital: 초기 자본금
    
    Returns:
        백테스팅 결과 딕셔너리
    """
    params = {
        'weeks': weeks,
        'initial_capital': initial_capital,
        'num_stocks': 5,
        'rebalance_frequency': 'daily',
        'weight_method': 'equal',
        'enable_market_filter': ENABLE_MARKET_FILTER
    }
    return simulate_portfolio_flexible(historical_data, params)

def calculate_performance_metrics(initial_capital, final_value, portfolio_history, 
                                  daily_returns, start_date, end_date, num_rebalances,
                                  cash_holding_days=0):
    """성과 지표 계산"""
    
    # 총 수익률
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    # 기간 계산 (일수)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end - start).days
    
    # 연환산 수익률
    if days > 0:
        annualized_return = ((final_value / initial_capital) ** (365 / days) - 1) * 100
    else:
        annualized_return = 0
    
    # 최대낙폭 (MDD) 계산
    mdd = calculate_mdd(portfolio_history)
    
    # 샤프비율 계산
    returns = [r['return'] for r in daily_returns]
    sharpe_ratio = calculate_sharpe_ratio(returns, RISK_FREE_RATE)
    
    # 승률 계산
    win_rate = calculate_win_rate(daily_returns)
    
    # 최고/최악의 날
    if daily_returns:
        best_day = max(daily_returns, key=lambda x: x['return'])
        worst_day = min(daily_returns, key=lambda x: x['return'])
    else:
        best_day = {'date': '-', 'return': 0}
        worst_day = {'date': '-', 'return': 0}
    
    result = {
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'mdd': mdd,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'num_rebalances': num_rebalances,
        'best_day': best_day,
        'worst_day': worst_day,
        'cash_holding_days': cash_holding_days,
        'cash_holding_ratio': (cash_holding_days / num_rebalances * 100) if num_rebalances > 0 else 0
    }
    
    return result

def calculate_mdd(portfolio_values):
    """최대낙폭 (Maximum Drawdown) 계산"""
    if len(portfolio_values) < 2:
        return 0.0
    
    peak = portfolio_values[0]
    max_drawdown = 0
    
    for value in portfolio_values:
        if value > peak:
            peak = value
        
        drawdown = ((value - peak) / peak) * 100
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown

def calculate_sharpe_ratio(returns, risk_free_rate=0.05):
    """샤프비율 계산"""
    if not returns or len(returns) < 2:
        return 0.0
    
    # 일일 수익률 평균
    avg_return = sum(returns) / len(returns)
    
    # 일일 수익률 표준편차
    variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    # 일일 무위험 수익률
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1
    daily_rf_pct = daily_rf * 100
    
    # 샤프비율 (연환산)
    sharpe = ((avg_return - daily_rf_pct) / std_dev) * (252 ** 0.5)
    
    return sharpe

def calculate_win_rate(daily_returns):
    """승률 계산 (수익 거래 / 전체 거래)"""
    if not daily_returns:
        return 0.0
    
    wins = sum(1 for r in daily_returns if r['return'] > 0)
    total = len(daily_returns)
    
    return (wins / total) * 100 if total > 0 else 0.0

def run_backtest(weeks=None, initial_capital=None, screener_type="large"):
    """
    백테스팅 실행 (메인 함수)
    
    Args:
        weeks: 백테스팅 기간 (주), None이면 config에서 가져옴
        initial_capital: 초기 자본금, None이면 config에서 가져옴
        screener_type: 'large' 또는 'mega'
    
    Returns:
        백테스팅 결과 딕셔너리
    """
    if weeks is None:
        weeks = BACKTEST_WEEKS
    if initial_capital is None:
        initial_capital = BACKTEST_INITIAL_CAPITAL
    
    screener_name = "대형주" if screener_type == "large" else "초대형주"
    logger.info(f"=== 백테스팅 시작: {screener_name}, {weeks}주, 초기자본 ${initial_capital} ===")
    
    # 캐시 확인
    cache_file = Path(DATA_DIR) / 'backtest_cache.json'
    cache_key = f"{screener_type}_{weeks}weeks_{initial_capital}"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if cache_key in cache:
                    cached_result = cache[cache_key]
                    # 오늘 날짜의 캐시인지 확인
                    if cached_result.get('cache_date') == datetime.now().strftime('%Y-%m-%d'):
                        logger.info("캐시된 백테스팅 결과 사용")
                        return cached_result['result']
        except Exception as e:
            logger.warning(f"캐시 읽기 실패: {e}")
    
    # 역사적 데이터 로드
    historical_data = load_historical_portfolio_data(screener_type)
    
    if not historical_data:
        logger.error("역사적 데이터를 로드할 수 없습니다.")
        return None
    
    # 백테스팅 실행
    result = simulate_portfolio(historical_data, weeks, initial_capital)
    
    if result:
        logger.info("=== 백테스팅 완료 ===")
        logger.info(f"총 수익률: {result['total_return']:.2f}%")
        logger.info(f"연환산 수익률: {result['annualized_return']:.2f}%")
        logger.info(f"최대낙폭: {result['mdd']:.2f}%")
        logger.info(f"샤프비율: {result['sharpe_ratio']:.2f}")
        logger.info(f"승률: {result['win_rate']:.2f}%")
        
        # 결과 캐싱
        try:
            cache = {}
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            
            cache[cache_key] = {
                'cache_date': datetime.now().strftime('%Y-%m-%d'),
                'result': result
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            logger.info("백테스팅 결과 캐시 저장")
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")
    
    return result

