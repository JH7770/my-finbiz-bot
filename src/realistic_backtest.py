#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
개선된 백테스팅 모듈 - Look-Ahead Bias 제거 및 거래 비용 반영

주요 개선사항:
1. Look-Ahead Bias 제거: 선정 시점 이전 데이터만 사용
2. 거래 비용 반영: 수수료 0.2% + 슬리피지 0.1%
3. 현실적인 리밸런싱: 주간/월간 리밸런싱
4. 생존편향 완화: 현재 시점이 아닌 과거 시점 기준
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import json
from logger import get_logger
from finviz_scraper import scrape_all_tickers_with_pagination
from config import DATA_DIR, RISK_FREE_RATE

logger = get_logger()

# 거래 비용 설정
TRANSACTION_FEE = 0.002  # 0.2% 수수료
SLIPPAGE = 0.001  # 0.1% 슬리피지
TOTAL_TRANSACTION_COST = TRANSACTION_FEE + SLIPPAGE  # 0.3% 총 거래비용


def get_top_performers_no_lookahead(screener_type="large", selection_date=None, 
                                     lookback_months=3, lag_months=1):
    """
    Look-Ahead Bias 없이 상위 종목 선정
    
    선정 방식:
    - selection_date에 종목을 선정한다면
    - (selection_date - lag_months) 이전의 lookback_months 수익률 사용
    
    예시: 2023-01-01에 선정
    - lag_months=1: 2022-12-01 이전 데이터만 사용
    - lookback_months=3: 2022-09-01 ~ 2022-12-01 수익률로 평가
    
    Args:
        screener_type: 'large' 또는 'mega'
        selection_date: 종목 선정 날짜 (datetime)
        lookback_months: 수익률 평가 기간 (개월)
        lag_months: 지연 기간 (개월) - 미래 정보 방지
    
    Returns:
        상위 10개 종목 정보
    """
    if selection_date is None:
        selection_date = datetime.now()
    
    # 평가 종료일: 선정일로부터 lag_months 전
    evaluation_end = selection_date - timedelta(days=lag_months * 30)
    # 평가 시작일: 평가 종료일로부터 lookback_months 전
    evaluation_start = evaluation_end - timedelta(days=lookback_months * 30 + 10)  # 여유
    
    logger.info(f"=== Look-Ahead Bias 없는 종목 선정 ===")
    logger.info(f"선정일: {selection_date.strftime('%Y-%m-%d')}")
    logger.info(f"평가 기간: {evaluation_start.strftime('%Y-%m-%d')} ~ {evaluation_end.strftime('%Y-%m-%d')}")
    logger.info(f"(선정 시점에서 {lag_months}개월 이전 데이터 사용)")
    
    # 1. 전체 티커 리스트
    all_tickers_df = scrape_all_tickers_with_pagination(screener_type)
    
    if all_tickers_df is None or len(all_tickers_df) == 0:
        logger.error("티커 리스트를 가져올 수 없습니다.")
        return None
    
    ticker_column = None
    for col in all_tickers_df.columns:
        if 'Ticker' in col or 'ticker' in col.lower():
            ticker_column = col
            break
    
    if ticker_column is None:
        logger.error("Ticker 컬럼을 찾을 수 없습니다.")
        return None
    
    tickers = all_tickers_df[ticker_column].tolist()
    logger.info(f"총 {len(tickers)}개 티커 분석")
    
    # 2. 각 종목의 과거 수익률 계산 (Look-Ahead Bias 없음)
    performance_data = []
    
    for i, ticker in enumerate(tickers):
        try:
            if (i + 1) % 50 == 0:
                logger.info(f"진행률: {i+1}/{len(tickers)} ({(i+1)/len(tickers)*100:.1f}%)")
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=evaluation_start, end=evaluation_end + timedelta(days=1))
            
            if hist.empty or len(hist) < 30:  # 최소 30일 데이터 필요
                logger.debug(f"{ticker}: 충분한 데이터 없음")
                continue
            
            # 평가 기간의 수익률 계산
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            
            if start_price == 0:
                continue
            
            performance = ((end_price - start_price) / start_price) * 100
            
            performance_data.append({
                'ticker': ticker,
                'performance': performance,
                'start_price': start_price,
                'end_price': end_price,
                'evaluation_start': hist.index[0].strftime('%Y-%m-%d'),
                'evaluation_end': hist.index[-1].strftime('%Y-%m-%d')
            })
            
            logger.debug(f"{ticker}: {performance:.2f}%")
            
        except Exception as e:
            logger.debug(f"{ticker}: 실패 - {e}")
            continue
    
    if len(performance_data) == 0:
        logger.error("수익률 데이터를 계산할 수 없습니다.")
        return None
    
    # 3. 수익률 기준 상위 10개 선정
    performance_df = pd.DataFrame(performance_data)
    performance_df = performance_df.sort_values('performance', ascending=False)
    
    top10 = performance_df.head(10)
    
    logger.info(f"\n=== 상위 10개 종목 (No Look-Ahead Bias) ===")
    for idx, row in top10.iterrows():
        logger.info(f"{row['ticker']}: {row['performance']:.2f}%")
    
    return {
        'tickers': top10['ticker'].tolist(),
        'top10_data': top10.to_dict('records'),
        'selection_date': selection_date.strftime('%Y-%m-%d'),
        'evaluation_period': f"{evaluation_start.strftime('%Y-%m-%d')} ~ {evaluation_end.strftime('%Y-%m-%d')}",
        'screener_type': screener_type
    }


def simulate_realistic_portfolio(tickers, start_date, end_date, initial_capital=10000,
                                  rebalance_frequency='monthly'):
    """
    현실적인 포트폴리오 시뮬레이션
    
    - 거래 비용 반영 (수수료 + 슬리피지)
    - 주간/월간 리밸런싱
    - 실제 가격 데이터 사용
    
    Args:
        tickers: 종목 리스트
        start_date: 시작일 (datetime)
        end_date: 종료일 (datetime)
        initial_capital: 초기 자본
        rebalance_frequency: 'weekly' 또는 'monthly'
    
    Returns:
        시뮬레이션 결과
    """
    logger.info(f"=== 현실적인 백테스팅 시작 ===")
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.2f}")
    logger.info(f"거래 비용: {TOTAL_TRANSACTION_COST*100:.1f}% (수수료 {TRANSACTION_FEE*100:.1f}% + 슬리피지 {SLIPPAGE*100:.1f}%)")
    logger.info(f"리밸런싱: {rebalance_frequency}")
    
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
                logger.warning(f"{ticker}: 데이터 없음")
        except Exception as e:
            logger.error(f"{ticker}: 데이터 가져오기 실패 - {e}")
    
    if len(price_data) == 0:
        logger.error("가격 데이터를 가져올 수 없습니다.")
        return None
    
    # 공통 거래일 찾기
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
    
    # 시뮬레이션 변수
    portfolio_value = initial_capital
    cash = initial_capital
    positions = {}  # {ticker: shares}
    portfolio_history = []
    daily_returns = []
    trade_log = []
    total_transaction_costs = 0
    
    last_rebalance_date = None
    
    # 매일 시뮬레이션
    for i, current_date in enumerate(common_dates):
        day_start_value = portfolio_value
        
        # 리밸런싱 체크
        should_rebalance = False
        if i == 0:  # 첫날은 무조건 매수
            should_rebalance = True
        elif rebalance_frequency == 'monthly':
            # 매월 첫 거래일
            if last_rebalance_date is None or (current_date - last_rebalance_date).days >= 25:
                should_rebalance = True
        elif rebalance_frequency == 'weekly':
            # 매주 첫 거래일
            if last_rebalance_date is None or (current_date - last_rebalance_date).days >= 6:
                should_rebalance = True
        
        # 리밸런싱 실행
        if should_rebalance:
            logger.info(f"\n{current_date.strftime('%Y-%m-%d')}: 리밸런싱")
            
            # 기존 포지션 청산 (매도)
            if positions:
                for ticker, shares in positions.items():
                    if ticker in price_data:
                        sell_price = price_data[ticker].loc[current_date]
                        # 슬리피지 적용 (매도 시 불리하게)
                        actual_sell_price = sell_price * (1 - SLIPPAGE)
                        sell_value = shares * actual_sell_price
                        # 수수료 차감
                        sell_value_after_fee = sell_value * (1 - TRANSACTION_FEE)
                        
                        cash += sell_value_after_fee
                        transaction_cost = shares * sell_price - sell_value_after_fee
                        total_transaction_costs += transaction_cost
                        
                        trade_log.append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'action': 'SELL',
                            'ticker': ticker,
                            'shares': shares,
                            'price': sell_price,
                            'cost': transaction_cost
                        })
                        
                        logger.debug(f"  매도: {ticker} {shares:.4f}주 @ ${sell_price:.2f} (비용: ${transaction_cost:.2f})")
            
            positions = {}
            
            # 새로운 포지션 매수
            num_stocks = len([t for t in tickers if t in price_data])
            if num_stocks > 0:
                allocation_per_stock = cash / num_stocks
                
                for ticker in tickers:
                    if ticker in price_data and allocation_per_stock > 10:  # 최소 $10 이상
                        buy_price = price_data[ticker].loc[current_date]
                        # 슬리피지 적용 (매수 시 불리하게)
                        actual_buy_price = buy_price * (1 + SLIPPAGE)
                        # 수수료 포함 매수
                        shares = allocation_per_stock / (actual_buy_price * (1 + TRANSACTION_FEE))
                        buy_cost = shares * actual_buy_price * (1 + TRANSACTION_FEE)
                        
                        if buy_cost <= cash:
                            positions[ticker] = shares
                            cash -= buy_cost
                            transaction_cost = buy_cost - (shares * buy_price)
                            total_transaction_costs += transaction_cost
                            
                            trade_log.append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'action': 'BUY',
                                'ticker': ticker,
                                'shares': shares,
                                'price': buy_price,
                                'cost': transaction_cost
                            })
                            
                            logger.debug(f"  매수: {ticker} {shares:.4f}주 @ ${buy_price:.2f} (비용: ${transaction_cost:.2f})")
            
            last_rebalance_date = current_date
        
        # 포트폴리오 가치 계산
        position_value = 0
        for ticker, shares in positions.items():
            if ticker in price_data:
                current_price = price_data[ticker].loc[current_date]
                position_value += shares * current_price
        
        portfolio_value = cash + position_value
        day_return = ((portfolio_value - day_start_value) / day_start_value) * 100 if day_start_value > 0 else 0
        
        portfolio_history.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'value': portfolio_value,
            'cash': cash,
            'positions': len(positions)
        })
        
        daily_returns.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'return': day_return,
            'value': portfolio_value
        })
    
    # 성과 지표 계산
    final_value = portfolio_value
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    days = (common_dates[-1] - common_dates[0]).days
    if days > 0:
        annualized_return = ((final_value / initial_capital) ** (365 / days) - 1) * 100
    else:
        annualized_return = 0
    
    # MDD, 샤프비율, 승률 계산
    mdd = calculate_mdd([h['value'] for h in portfolio_history])
    returns = [r['return'] for r in daily_returns]
    sharpe_ratio = calculate_sharpe_ratio(returns, RISK_FREE_RATE)
    win_rate = calculate_win_rate(daily_returns)
    
    if daily_returns:
        best_day = max(daily_returns, key=lambda x: x['return'])
        worst_day = min(daily_returns, key=lambda x: x['return'])
    else:
        best_day = {'date': '-', 'return': 0}
        worst_day = {'date': '-', 'return': 0}
    
    # 거래 통계
    buy_trades = [t for t in trade_log if t['action'] == 'BUY']
    sell_trades = [t for t in trade_log if t['action'] == 'SELL']
    
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
        'trading_days': len(common_dates),
        'best_day': best_day,
        'worst_day': worst_day,
        'portfolio_history': portfolio_history,
        'daily_returns': daily_returns,
        'trade_log': trade_log,
        'total_trades': len(trade_log),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'total_transaction_costs': total_transaction_costs,
        'transaction_cost_pct': (total_transaction_costs / initial_capital) * 100,
        'rebalance_frequency': rebalance_frequency,
        'transaction_fee': TRANSACTION_FEE,
        'slippage': SLIPPAGE
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
    
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1
    daily_rf_pct = daily_rf * 100
    
    sharpe = ((avg_return - daily_rf_pct) / std_dev) * (252 ** 0.5)
    
    return sharpe


def calculate_win_rate(daily_returns):
    """승률 계산"""
    if not daily_returns:
        return 0.0
    
    wins = sum(1 for r in daily_returns if r['return'] > 0)
    total = len(daily_returns)
    
    return (wins / total) * 100 if total > 0 else 0.0


def run_realistic_backtest(screener_type="large", initial_capital=10000,
                           test_period_months=3, lookback_months=3, lag_months=1,
                           rebalance_frequency='monthly'):
    """
    현실적인 백테스팅 메인 함수
    
    Args:
        screener_type: 'large' 또는 'mega'
        initial_capital: 초기 자본
        test_period_months: 테스트 기간 (개월)
        lookback_months: 종목 선정 시 수익률 평가 기간 (개월)
        lag_months: 종목 선정 시 지연 기간 (개월) - Look-Ahead Bias 방지
        rebalance_frequency: 'weekly' 또는 'monthly'
    
    Returns:
        백테스팅 결과
    """
    logger.info("="*60)
    logger.info("현실적인 백테스팅 (Look-Ahead Bias 제거 + 거래비용)")
    logger.info("="*60)
    
    # 날짜 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=test_period_months * 30)
    
    # 종목 선정 (Look-Ahead Bias 없음)
    top_stocks = get_top_performers_no_lookahead(
        screener_type=screener_type,
        selection_date=start_date,
        lookback_months=lookback_months,
        lag_months=lag_months
    )
    
    if top_stocks is None:
        logger.error("종목 선정 실패")
        return None
    
    tickers = top_stocks['tickers']
    
    # 포트폴리오 시뮬레이션
    result = simulate_realistic_portfolio(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        rebalance_frequency=rebalance_frequency
    )
    
    if result is None:
        logger.error("시뮬레이션 실패")
        return None
    
    # 결과 통합
    full_result = {
        'screener_type': screener_type,
        'selection': top_stocks,
        'simulation': result,
        'parameters': {
            'test_period_months': test_period_months,
            'lookback_months': lookback_months,
            'lag_months': lag_months,
            'rebalance_frequency': rebalance_frequency,
            'transaction_fee': TRANSACTION_FEE,
            'slippage': SLIPPAGE
        },
        'run_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 결과 로깅
    logger.info("\n" + "="*60)
    logger.info("백테스팅 결과 (현실적 버전)")
    logger.info("="*60)
    logger.info(f"\n[선정된 종목]")
    logger.info(f"평가 기간: {top_stocks['evaluation_period']}")
    logger.info(f"선정된 종목: {', '.join(tickers)}")
    
    logger.info(f"\n[시뮬레이션 결과]")
    logger.info(f"기간: {result['start_date']} ~ {result['end_date']}")
    logger.info(f"초기 자본: ${result['initial_capital']:,.0f}")
    logger.info(f"최종 가치: ${result['final_value']:,.0f}")
    logger.info(f"총 수익률: {result['total_return']:+.2f}%")
    logger.info(f"연환산 수익률: {result['annualized_return']:+.2f}%")
    logger.info(f"최대낙폭 (MDD): {result['mdd']:.2f}%")
    logger.info(f"샤프비율: {result['sharpe_ratio']:.2f}")
    logger.info(f"승률: {result['win_rate']:.2f}%")
    
    logger.info(f"\n[거래 비용 분석]")
    logger.info(f"총 거래 비용: ${result['total_transaction_costs']:.2f}")
    logger.info(f"비용 비율: {result['transaction_cost_pct']:.2f}% (초기 자본 대비)")
    logger.info(f"총 거래 횟수: {result['total_trades']}회")
    logger.info(f"  - 매수: {result['buy_count']}회")
    logger.info(f"  - 매도: {result['sell_count']}회")
    
    return full_result


if __name__ == "__main__":
    # 테스트 실행
    result = run_realistic_backtest(
        screener_type="large",
        initial_capital=10000,
        test_period_months=3,
        lookback_months=3,
        lag_months=1,
        rebalance_frequency='monthly'
    )
    
    if result:
        # JSON 저장
        output_path = Path(DATA_DIR) / 'realistic_backtest_result.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"\n결과 저장: {output_path}")

