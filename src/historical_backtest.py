# 3개월 역산 백테스팅 모듈
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import json
from logger import get_logger
from finviz_scraper import scrape_all_tickers_with_pagination
from config import DATA_DIR, RISK_FREE_RATE

logger = get_logger()

def get_historical_top_performers(screener_type="large", lookback_date=None, performance_period_days=90):
    """
    특정 시점(lookback_date)에서 과거 performance_period_days 동안의 수익률 기준으로 
    상위 10개 종목을 선정
    
    Args:
        screener_type: 'large' 또는 'mega'
        lookback_date: 기준 날짜 (datetime 객체, None이면 3개월 전)
        performance_period_days: 수익률 계산 기간 (기본: 90일 = 3개월)
    
    Returns:
        상위 10개 종목의 티커 리스트
    """
    if lookback_date is None:
        lookback_date = datetime.now() - timedelta(days=90)
    
    logger.info(f"=== {lookback_date.strftime('%Y-%m-%d')} 기준 상위 10개 종목 선정 시작 ===")
    
    # 1. 전체 티커 리스트 가져오기
    logger.info(f"{screener_type} 스크리너에서 전체 티커 리스트 수집 중...")
    all_tickers_df = scrape_all_tickers_with_pagination(screener_type)
    
    if all_tickers_df is None or len(all_tickers_df) == 0:
        logger.error("티커 리스트를 가져올 수 없습니다.")
        return None
    
    # Ticker 컬럼 찾기
    ticker_column = None
    for col in all_tickers_df.columns:
        if 'Ticker' in col or 'ticker' in col.lower():
            ticker_column = col
            break
    
    if ticker_column is None:
        logger.error("Ticker 컬럼을 찾을 수 없습니다.")
        return None
    
    tickers = all_tickers_df[ticker_column].tolist()
    logger.info(f"총 {len(tickers)}개 티커 수집 완료")
    
    # 2. 각 종목의 수익률 계산
    start_date = lookback_date - timedelta(days=performance_period_days + 30)  # 여유있게
    end_date = lookback_date
    
    logger.info(f"수익률 계산 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    performance_data = []
    
    for i, ticker in enumerate(tickers):
        try:
            if (i + 1) % 50 == 0:
                logger.info(f"진행률: {i+1}/{len(tickers)} ({(i+1)/len(tickers)*100:.1f}%)")
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 2:
                logger.debug(f"{ticker}: 충분한 가격 데이터 없음")
                continue
            
            # lookback_date에 가장 가까운 날짜의 가격 찾기
            hist_dates = hist.index
            end_idx = -1
            for idx, date in enumerate(hist_dates):
                if date.date() <= end_date.date():
                    end_idx = idx
            
            if end_idx == -1 or end_idx < performance_period_days // 2:
                logger.debug(f"{ticker}: 기준일 데이터 부족")
                continue
            
            # performance_period_days 전 가격 찾기
            start_idx = max(0, end_idx - int(performance_period_days * 0.7))  # 영업일 고려
            
            if start_idx >= end_idx:
                logger.debug(f"{ticker}: 시작/종료 인덱스 문제")
                continue
            
            start_price = hist['Close'].iloc[start_idx]
            end_price = hist['Close'].iloc[end_idx]
            
            if start_price == 0:
                continue
            
            # 수익률 계산
            performance = ((end_price - start_price) / start_price) * 100
            
            performance_data.append({
                'ticker': ticker,
                'performance': performance,
                'start_price': start_price,
                'end_price': end_price,
                'start_date': hist_dates[start_idx].strftime('%Y-%m-%d'),
                'end_date': hist_dates[end_idx].strftime('%Y-%m-%d')
            })
            
            logger.debug(f"{ticker}: {performance:.2f}% ({start_price:.2f} -> {end_price:.2f})")
            
        except Exception as e:
            logger.debug(f"{ticker}: 데이터 가져오기 실패 - {e}")
            continue
    
    if len(performance_data) == 0:
        logger.error("수익률 데이터를 계산할 수 없습니다.")
        return None
    
    # 3. 수익률 기준 상위 10개 선정
    performance_df = pd.DataFrame(performance_data)
    performance_df = performance_df.sort_values('performance', ascending=False)
    
    top10 = performance_df.head(10)
    logger.info(f"\n=== 상위 10개 종목 (수익률 기준) ===")
    for idx, row in top10.iterrows():
        logger.info(f"{row['ticker']}: {row['performance']:.2f}%")
    
    return {
        'tickers': top10['ticker'].tolist(),
        'top10_data': top10.to_dict('records'),
        'selection_date': lookback_date.strftime('%Y-%m-%d'),
        'screener_type': screener_type
    }

def calculate_buy_and_hold_returns(tickers, start_date, end_date):
    """
    각 종목별 Buy & Hold 수익률 계산
    
    Args:
        tickers: 종목 리스트
        start_date: 매수 날짜 (datetime)
        end_date: 현재 날짜 (datetime)
    
    Returns:
        각 종목의 수익률 딕셔너리 리스트
    """
    logger.info(f"\n=== Buy & Hold 수익률 계산 ===")
    logger.info(f"매수일: {start_date.strftime('%Y-%m-%d')}")
    logger.info(f"현재일: {end_date.strftime('%Y-%m-%d')}")
    
    results = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date + timedelta(days=1))
            
            if hist.empty or len(hist) < 2:
                logger.warning(f"{ticker}: 충분한 데이터 없음")
                continue
            
            # 시작가와 종료가
            buy_price = hist['Close'].iloc[0]
            current_price = hist['Close'].iloc[-1]
            
            # 수익률 계산
            return_pct = ((current_price - buy_price) / buy_price) * 100
            
            results.append({
                'ticker': ticker,
                'buy_price': buy_price,
                'current_price': current_price,
                'return_pct': return_pct,
                'buy_date': hist.index[0].strftime('%Y-%m-%d'),
                'current_date': hist.index[-1].strftime('%Y-%m-%d')
            })
            
            logger.info(f"{ticker}: ${buy_price:.2f} → ${current_price:.2f} ({return_pct:+.2f}%)")
            
        except Exception as e:
            logger.error(f"{ticker}: Buy & Hold 계산 실패 - {e}")
            continue
    
    # 수익률 기준 정렬
    results.sort(key=lambda x: x['return_pct'], reverse=True)
    
    return results

def simulate_daily_rebalancing(tickers, start_date, end_date, initial_capital=10000):
    """
    매일 리밸런싱 전략으로 포트폴리오 시뮬레이션
    
    Args:
        tickers: 종목 리스트
        start_date: 시작 날짜 (datetime)
        end_date: 종료 날짜 (datetime)
        initial_capital: 초기 자본금
    
    Returns:
        시뮬레이션 결과 딕셔너리
    """
    logger.info(f"=== 매일 리밸런싱 시뮬레이션 시작 ===")
    logger.info(f"종목: {', '.join(tickers)}")
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.2f}")
    
    # Buy & Hold 수익률 계산
    buy_hold_returns = calculate_buy_and_hold_returns(tickers, start_date, end_date)
    
    # 모든 종목의 가격 데이터 가져오기
    price_data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date + timedelta(days=1))
            
            if not hist.empty:
                price_data[ticker] = hist['Close']
                logger.debug(f"{ticker}: {len(hist)}일 데이터")
            else:
                logger.warning(f"{ticker}: 가격 데이터 없음")
        except Exception as e:
            logger.error(f"{ticker}: 가격 데이터 가져오기 실패 - {e}")
    
    if len(price_data) == 0:
        logger.error("가격 데이터를 가져올 수 없습니다.")
        return None
    
    # 공통 날짜 찾기 (모든 종목이 거래된 날)
    common_dates = None
    for ticker, prices in price_data.items():
        if common_dates is None:
            common_dates = set(prices.index)
        else:
            common_dates = common_dates.intersection(set(prices.index))
    
    common_dates = sorted(list(common_dates))
    logger.info(f"공통 거래일: {len(common_dates)}일")
    
    if len(common_dates) < 2:
        logger.error("충분한 공통 거래일이 없습니다.")
        return None
    
    # 매일 리밸런싱 시뮬레이션
    portfolio_value = initial_capital
    portfolio_history = [{'date': common_dates[0].strftime('%Y-%m-%d'), 'value': initial_capital}]
    daily_returns = []
    
    for i in range(len(common_dates) - 1):
        current_date = common_dates[i]
        next_date = common_dates[i + 1]
        
        # 각 종목에 동일 비중 할당
        num_stocks = len(price_data)
        allocation_per_stock = portfolio_value / num_stocks
        
        # 당일 수익률 계산
        day_return = 0
        successful_stocks = 0
        
        for ticker, prices in price_data.items():
            try:
                current_price = prices.loc[current_date]
                next_price = prices.loc[next_date]
                
                stock_return = (next_price - current_price) / current_price
                day_return += stock_return * (1 / num_stocks)  # 균등 비중
                successful_stocks += 1
            except KeyError:
                logger.debug(f"{ticker}: {current_date} 또는 {next_date} 데이터 없음")
                continue
        
        # 포트폴리오 가치 업데이트
        new_value = portfolio_value * (1 + day_return)
        
        daily_returns.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'return': day_return * 100,
            'value': new_value
        })
        
        portfolio_history.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'value': new_value
        })
        
        logger.debug(f"{next_date.strftime('%Y-%m-%d')}: 수익률 {day_return*100:.2f}%, 가치 ${new_value:,.2f}")
        
        portfolio_value = new_value
    
    # 성과 지표 계산
    final_value = portfolio_value
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    # 기간 계산
    days = (common_dates[-1] - common_dates[0]).days
    if days > 0:
        annualized_return = ((final_value / initial_capital) ** (365 / days) - 1) * 100
    else:
        annualized_return = 0
    
    # MDD 계산
    mdd = calculate_mdd([h['value'] for h in portfolio_history])
    
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
        'tickers': tickers,
        'start_date': common_dates[0].strftime('%Y-%m-%d'),
        'end_date': common_dates[-1].strftime('%Y-%m-%d'),
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'mdd': mdd,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'trading_days': len(common_dates) - 1,
        'best_day': best_day,
        'worst_day': worst_day,
        'portfolio_history': portfolio_history,
        'daily_returns': daily_returns,
        'buy_hold_returns': buy_hold_returns
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

def run_historical_backtest(screener_type="large", initial_capital=10000, 
                           lookback_days=90, cache_file=None, top_n=10):
    """
    3개월 역산 백테스팅 메인 함수
    
    Args:
        screener_type: 'large' 또는 'mega'
        initial_capital: 초기 자본금
        lookback_days: 역산 기간 (기본: 90일 = 3개월)
        cache_file: 캐시 파일 경로 (None이면 기본 경로 사용)
        top_n: 상위 N개 종목 선정 (기본: 10)
    
    Returns:
        백테스팅 결과 딕셔너리
    """
    if cache_file is None:
        cache_file = Path(DATA_DIR) / f'historical_backtest_{screener_type}_top{top_n}.json'
    
    # 캐시 확인
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                cache_date = cached.get('cache_date')
                if cache_date == datetime.now().strftime('%Y-%m-%d'):
                    logger.info("캐시된 백테스팅 결과 사용")
                    return cached['result']
        except Exception as e:
            logger.warning(f"캐시 읽기 실패: {e}")
    
    # 날짜 설정
    end_date = datetime.now()
    lookback_date = end_date - timedelta(days=lookback_days)
    
    logger.info(f"=== 3개월 역산 백테스팅 시작 ({screener_type}, 상위 {top_n}개) ===")
    logger.info(f"현재: {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"3개월 전: {lookback_date.strftime('%Y-%m-%d')}")
    
    # 1. 3개월 전 상위 N개 종목 선정
    top10_result = get_historical_top_performers(
        screener_type=screener_type,
        lookback_date=lookback_date,
        performance_period_days=90
    )
    
    if top10_result is None:
        logger.error(f"상위 {top_n}개 종목 선정 실패")
        return None
    
    # 상위 N개만 선택
    top10_result['tickers'] = top10_result['tickers'][:top_n]
    top10_result['top10_data'] = top10_result['top10_data'][:top_n]
    
    tickers = top10_result['tickers']
    
    # 2. 매일 리밸런싱 시뮬레이션
    simulation_result = simulate_daily_rebalancing(
        tickers=tickers,
        start_date=lookback_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    if simulation_result is None:
        logger.error("시뮬레이션 실패")
        return None
    
    # 결과 합치기
    result = {
        'screener_type': screener_type,
        'top_n': top_n,
        'selection': top10_result,
        'simulation': simulation_result,
        'lookback_days': lookback_days,
        'run_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 결과 로깅
    logger.info(f"\n=== 백테스팅 결과 요약 (상위 {top_n}개) ===")
    logger.info(f"선정된 종목: {', '.join(tickers)}")
    logger.info(f"총 수익률: {simulation_result['total_return']:.2f}%")
    logger.info(f"연환산 수익률: {simulation_result['annualized_return']:.2f}%")
    logger.info(f"최대낙폭: {simulation_result['mdd']:.2f}%")
    logger.info(f"샤프비율: {simulation_result['sharpe_ratio']:.2f}")
    logger.info(f"승률: {simulation_result['win_rate']:.2f}%")
    
    # 캐시 저장
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'cache_date': datetime.now().strftime('%Y-%m-%d'),
                'result': result
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"결과 캐시 저장: {cache_file}")
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")
    
    return result

def run_combined_backtest(initial_capital=10000, lookback_days=90, 
                         large_top_n=5, mega_top_n=5):
    """
    대형주 + 초대형주 결합 백테스팅
    
    Args:
        initial_capital: 초기 자본금
        lookback_days: 역산 기간 (기본: 90일 = 3개월)
        large_top_n: 대형주에서 선정할 종목 수 (기본: 5)
        mega_top_n: 초대형주에서 선정할 종목 수 (기본: 5)
    
    Returns:
        백테스팅 결과 딕셔너리
    """
    cache_file = Path(DATA_DIR) / f'historical_backtest_combined_L{large_top_n}_M{mega_top_n}.json'
    
    # 캐시 확인
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                cache_date = cached.get('cache_date')
                if cache_date == datetime.now().strftime('%Y-%m-%d'):
                    logger.info("캐시된 결합 백테스팅 결과 사용")
                    return cached['result']
        except Exception as e:
            logger.warning(f"캐시 읽기 실패: {e}")
    
    # 날짜 설정
    end_date = datetime.now()
    lookback_date = end_date - timedelta(days=lookback_days)
    
    logger.info("="*60)
    logger.info(f"결합 백테스팅 시작: 대형주 상위 {large_top_n}개 + 초대형주 상위 {mega_top_n}개")
    logger.info("="*60)
    logger.info(f"현재: {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"3개월 전: {lookback_date.strftime('%Y-%m-%d')}")
    
    # 1. 대형주 상위 N개 선정
    logger.info(f"\n[1/3] 대형주 상위 {large_top_n}개 종목 선정 중...")
    large_result = get_historical_top_performers(
        screener_type="large",
        lookback_date=lookback_date,
        performance_period_days=90
    )
    
    if large_result is None:
        logger.error("대형주 종목 선정 실패")
        return None
    
    large_tickers = large_result['tickers'][:large_top_n]
    large_data = large_result['top10_data'][:large_top_n]
    
    logger.info(f"대형주 선정: {', '.join(large_tickers)}")
    
    # 2. 초대형주 상위 N개 선정
    logger.info(f"\n[2/3] 초대형주 상위 {mega_top_n}개 종목 선정 중...")
    mega_result = get_historical_top_performers(
        screener_type="mega",
        lookback_date=lookback_date,
        performance_period_days=90
    )
    
    if mega_result is None:
        logger.error("초대형주 종목 선정 실패")
        return None
    
    mega_tickers = mega_result['tickers'][:mega_top_n]
    mega_data = mega_result['top10_data'][:mega_top_n]
    
    logger.info(f"초대형주 선정: {', '.join(mega_tickers)}")
    
    # 3. 결합된 포트폴리오로 시뮬레이션
    combined_tickers = large_tickers + mega_tickers
    logger.info(f"\n[3/3] 결합 포트폴리오 시뮬레이션: 총 {len(combined_tickers)}개 종목")
    logger.info(f"종목: {', '.join(combined_tickers)}")
    
    simulation_result = simulate_daily_rebalancing(
        tickers=combined_tickers,
        start_date=lookback_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    if simulation_result is None:
        logger.error("시뮬레이션 실패")
        return None
    
    # 결과 합치기
    result = {
        'screener_type': 'combined',
        'large_top_n': large_top_n,
        'mega_top_n': mega_top_n,
        'selection': {
            'large': {
                'tickers': large_tickers,
                'data': large_data
            },
            'mega': {
                'tickers': mega_tickers,
                'data': mega_data
            },
            'combined_tickers': combined_tickers
        },
        'simulation': simulation_result,
        'lookback_days': lookback_days,
        'run_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 결과 로깅
    logger.info("\n" + "="*60)
    logger.info("결합 백테스팅 결과 요약")
    logger.info("="*60)
    logger.info(f"대형주 {large_top_n}개: {', '.join(large_tickers)}")
    logger.info(f"초대형주 {mega_top_n}개: {', '.join(mega_tickers)}")
    logger.info(f"총 수익률: {simulation_result['total_return']:.2f}%")
    logger.info(f"연환산 수익률: {simulation_result['annualized_return']:.2f}%")
    logger.info(f"최대낙폭: {simulation_result['mdd']:.2f}%")
    logger.info(f"샤프비율: {simulation_result['sharpe_ratio']:.2f}")
    logger.info(f"승률: {simulation_result['win_rate']:.2f}%")
    
    # 캐시 저장
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'cache_date': datetime.now().strftime('%Y-%m-%d'),
                'result': result
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"결과 캐시 저장: {cache_file}")
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")
    
    return result

