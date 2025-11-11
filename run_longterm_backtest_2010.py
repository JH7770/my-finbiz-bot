#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2010년부터 현재까지 장기 백테스팅 스크립트

- 기간: 2010년 1월 ~ 현재
- 리밸런싱: 매월 1회
- 종목 선정: 대형주 5개 + 초대형주 5개 (총 10개)
- 거래 비용: 수수료 0.2% + 슬리피지 0.1%
- Look-Ahead Bias: 제거
"""

import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import json
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from logger import get_logger
from config import DATA_DIR, RISK_FREE_RATE

logger = get_logger()

# 거래 비용 설정
TRANSACTION_FEE = 0.002  # 0.2% 수수료
SLIPPAGE = 0.001  # 0.1% 슬리피지
TOTAL_TRANSACTION_COST = TRANSACTION_FEE + SLIPPAGE  # 0.3%

# S&P 500 구성 종목 (간소화 버전 - 주요 종목들)
# 실제로는 각 시점의 Large/Mega Cap을 정확히 구하기 어려우므로
# 주요 종목들을 기반으로 시뮬레이션
SP500_TICKERS = [
    # 기술주
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 
    'AMD', 'INTC', 'CSCO', 'ORCL', 'IBM', 'CRM', 'ADBE', 'NFLX',
    # 금융
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP',
    # 헬스케어
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'LLY', 'ABT', 'CVS',
    # 소비재
    'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'COST', 'PG',
    # 에너지
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD',
    # 산업
    'BA', 'HON', 'UPS', 'CAT', 'GE', 'MMM', 'LMT', 'RTX',
    # 통신
    'VZ', 'T', 'TMUS', 'CMCSA',
    # 기타
    'TSMC', 'BRK-B', 'V', 'MA', 'DIS', 'PYPL'
]


def get_top_performers_at_date(tickers_pool, selection_date, lookback_months=3, top_n=10):
    """
    특정 시점에서 과거 N개월 수익률 기준 상위 종목 선정
    Look-Ahead Bias 없음 - selection_date 이전 데이터만 사용
    
    Args:
        tickers_pool: 티커 풀 리스트
        selection_date: 종목 선정 날짜
        lookback_months: 수익률 평가 기간 (개월)
        top_n: 선정할 종목 수
    
    Returns:
        상위 N개 티커 리스트
    """
    evaluation_end = selection_date
    evaluation_start = selection_date - timedelta(days=lookback_months * 30 + 30)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"종목 선정: {selection_date.strftime('%Y-%m-%d')}")
    logger.info(f"평가 기간: {evaluation_start.strftime('%Y-%m-%d')} ~ {evaluation_end.strftime('%Y-%m-%d')}")
    logger.info(f"{'='*60}")
    
    performance_data = []
    
    for i, ticker in enumerate(tickers_pool):
        try:
            if (i + 1) % 20 == 0:
                logger.info(f"진행률: {i+1}/{len(tickers_pool)} ({(i+1)/len(tickers_pool)*100:.1f}%)")
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=evaluation_start, end=evaluation_end + timedelta(days=1))
            
            if hist.empty or len(hist) < 30:
                logger.debug(f"{ticker}: 데이터 부족")
                continue
            
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            
            if start_price == 0:
                continue
            
            performance = ((end_price - start_price) / start_price) * 100
            
            performance_data.append({
                'ticker': ticker,
                'performance': performance,
                'start_price': start_price,
                'end_price': end_price
            })
            
            logger.debug(f"{ticker}: {performance:+.2f}%")
            
        except Exception as e:
            logger.debug(f"{ticker}: 실패 - {e}")
            continue
    
    if len(performance_data) == 0:
        logger.error("수익률 데이터 없음")
        return []
    
    # 수익률 기준 상위 N개
    performance_df = pd.DataFrame(performance_data)
    performance_df = performance_df.sort_values('performance', ascending=False)
    top_stocks = performance_df.head(top_n)
    
    logger.info(f"\n상위 {top_n}개 종목:")
    for idx, row in top_stocks.iterrows():
        logger.info(f"  {row['ticker']}: {row['performance']:+.2f}%")
    
    return top_stocks['ticker'].tolist()


def simulate_longterm_portfolio(start_date, end_date, tickers_pool, 
                                 initial_capital=10000, rebalance_frequency='monthly',
                                 lookback_months=3, top_n=10):
    """
    장기 포트폴리오 시뮬레이션
    
    Args:
        start_date: 시작일
        end_date: 종료일
        tickers_pool: 티커 풀
        initial_capital: 초기 자본
        rebalance_frequency: 리밸런싱 빈도 ('monthly' 또는 'quarterly')
        lookback_months: 종목 선정 시 평가 기간
        top_n: 선정할 종목 수
    
    Returns:
        시뮬레이션 결과
    """
    logger.info("\n" + "="*80)
    logger.info("장기 백테스팅 시작")
    logger.info("="*80)
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.0f}")
    logger.info(f"리밸런싱: {rebalance_frequency}")
    logger.info(f"거래 비용: {TOTAL_TRANSACTION_COST*100:.1f}% (수수료 {TRANSACTION_FEE*100:.1f}% + 슬리피지 {SLIPPAGE*100:.1f}%)")
    logger.info(f"종목 선정: 상위 {top_n}개")
    
    # 변수 초기화
    portfolio_value = initial_capital
    cash = initial_capital
    positions = {}  # {ticker: shares}
    current_tickers = []
    
    portfolio_history = []
    monthly_returns = []
    trade_log = []
    rebalance_dates = []
    
    total_transaction_costs = 0
    
    # 월별로 순회
    current_date = start_date
    last_rebalance_date = None
    month_count = 0
    
    while current_date <= end_date:
        # 리밸런싱 체크
        should_rebalance = False
        
        if last_rebalance_date is None:
            # 첫 날
            should_rebalance = True
        elif rebalance_frequency == 'weekly':
            # 매주 (7일마다)
            if (current_date - last_rebalance_date).days >= 7:
                should_rebalance = True
        elif rebalance_frequency == 'monthly':
            # 매월 1일 또는 첫 영업일
            if current_date.month != last_rebalance_date.month:
                should_rebalance = True
        elif rebalance_frequency == 'quarterly':
            # 분기별 (3개월마다)
            months_diff = (current_date.year - last_rebalance_date.year) * 12 + \
                          (current_date.month - last_rebalance_date.month)
            if months_diff >= 3:
                should_rebalance = True
        
        if should_rebalance:
            month_count += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"[{month_count}] 리밸런싱 #{len(rebalance_dates)+1}: {current_date.strftime('%Y-%m-%d')}")
            logger.info(f"{'='*80}")
            
            # 기존 포지션 청산
            if positions:
                logger.info("기존 포지션 청산 중...")
                for ticker, shares in positions.items():
                    try:
                        stock = yf.Ticker(ticker)
                        hist = stock.history(start=current_date - timedelta(days=5), 
                                            end=current_date + timedelta(days=1))
                        
                        if hist.empty:
                            logger.warning(f"{ticker}: 매도 가격 데이터 없음")
                            continue
                        
                        sell_price = hist['Close'].iloc[-1]
                        actual_sell_price = sell_price * (1 - SLIPPAGE)
                        sell_value = shares * actual_sell_price
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
                        
                        logger.info(f"  매도: {ticker} {shares:.4f}주 @ ${sell_price:.2f}")
                        
                    except Exception as e:
                        logger.error(f"{ticker} 매도 실패: {e}")
                        continue
            
            positions = {}
            
            # 새로운 종목 선정
            logger.info("\n새로운 종목 선정 중...")
            new_tickers = get_top_performers_at_date(
                tickers_pool=tickers_pool,
                selection_date=current_date,
                lookback_months=lookback_months,
                top_n=top_n
            )
            
            if len(new_tickers) == 0:
                logger.error("종목 선정 실패")
                current_date += timedelta(days=30)
                continue
            
            current_tickers = new_tickers
            rebalance_dates.append(current_date.strftime('%Y-%m-%d'))
            
            # 새로운 포지션 매수
            logger.info(f"\n새로운 포지션 매수 중... (현금: ${cash:,.2f})")
            num_stocks = len(current_tickers)
            allocation_per_stock = cash / num_stocks
            
            for ticker in current_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=current_date - timedelta(days=5),
                                        end=current_date + timedelta(days=1))
                    
                    if hist.empty:
                        logger.warning(f"{ticker}: 매수 가격 데이터 없음")
                        continue
                    
                    buy_price = hist['Close'].iloc[-1]
                    actual_buy_price = buy_price * (1 + SLIPPAGE)
                    shares = allocation_per_stock / (actual_buy_price * (1 + TRANSACTION_FEE))
                    buy_cost = shares * actual_buy_price * (1 + TRANSACTION_FEE)
                    
                    if buy_cost <= cash and buy_cost > 10:
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
                        
                        logger.info(f"  매수: {ticker} {shares:.4f}주 @ ${buy_price:.2f}")
                    
                except Exception as e:
                    logger.error(f"{ticker} 매수 실패: {e}")
                    continue
            
            last_rebalance_date = current_date
            
            # 포트폴리오 가치 계산
            position_value = 0
            for ticker, shares in positions.items():
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=current_date - timedelta(days=5),
                                        end=current_date + timedelta(days=1))
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        position_value += shares * current_price
                except:
                    continue
            
            portfolio_value = cash + position_value
            
            logger.info(f"\n리밸런싱 후 포트폴리오:")
            logger.info(f"  현금: ${cash:,.2f}")
            logger.info(f"  포지션 가치: ${position_value:,.2f}")
            logger.info(f"  총 가치: ${portfolio_value:,.2f}")
            logger.info(f"  누적 거래 비용: ${total_transaction_costs:,.2f}")
        
        # 포트폴리오 가치 기록 (월말)
        is_month_end = False
        next_date = None
        
        if rebalance_frequency == 'weekly':
            next_date = current_date + timedelta(days=7)
            # 월이 바뀌는지 체크
            if next_date.month != current_date.month or next_date > end_date:
                is_month_end = True
        else:  # monthly or quarterly
            # 다음 달로 이동
            if current_date.month == 12:
                next_date = datetime(current_date.year + 1, 1, 1)
            else:
                next_date = datetime(current_date.year, current_date.month + 1, 1)
            is_month_end = True
        
        # 월말이면 가치 기록 및 수익률 계산
        if is_month_end:
            try:
                position_value = 0
                for ticker, shares in positions.items():
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=current_date - timedelta(days=5),
                                        end=current_date + timedelta(days=1))
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        position_value += shares * current_price
                
                portfolio_value = cash + position_value
                
                portfolio_history.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': portfolio_value,
                    'cash': cash,
                    'positions': len(positions),
                    'tickers': list(positions.keys())
                })
                
                # 월별 수익률 계산
                if len(portfolio_history) > 1:
                    prev_value = portfolio_history[-2]['value']
                    monthly_return = ((portfolio_value - prev_value) / prev_value) * 100
                    monthly_returns.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'return': monthly_return,
                        'value': portfolio_value
                    })
                    logger.info(f"{current_date.strftime('%Y-%m')}: ${portfolio_value:,.0f} ({monthly_return:+.2f}%)")
            
            except Exception as e:
                logger.error(f"{current_date} 가치 계산 실패: {e}")
        
        # 다음 기간으로 이동
        current_date = next_date
        if current_date > end_date:
            break
    
    # 최종 성과 계산
    final_value = portfolio_value
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    years = (end_date - start_date).days / 365.25
    if years > 0:
        cagr = ((final_value / initial_capital) ** (1 / years) - 1) * 100
    else:
        cagr = 0
    
    # 지표 계산
    mdd = calculate_mdd([h['value'] for h in portfolio_history])
    returns = [r['return'] for r in monthly_returns]
    sharpe_ratio = calculate_sharpe_ratio(returns, RISK_FREE_RATE, frequency='monthly')
    win_rate = calculate_win_rate(monthly_returns)
    
    if monthly_returns:
        best_month = max(monthly_returns, key=lambda x: x['return'])
        worst_month = min(monthly_returns, key=lambda x: x['return'])
        avg_monthly_return = sum(r['return'] for r in monthly_returns) / len(monthly_returns)
        volatility = np.std([r['return'] for r in monthly_returns])
    else:
        best_month = {'date': '-', 'return': 0}
        worst_month = {'date': '-', 'return': 0}
        avg_monthly_return = 0
        volatility = 0
    
    result = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'cagr': cagr,
        'years': round(years, 2),
        'mdd': mdd,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'avg_monthly_return': avg_monthly_return,
        'volatility': volatility,
        'best_month': best_month,
        'worst_month': worst_month,
        'total_rebalances': len(rebalance_dates),
        'total_trades': len(trade_log),
        'total_transaction_costs': total_transaction_costs,
        'transaction_cost_pct': (total_transaction_costs / initial_capital) * 100,
        'portfolio_history': portfolio_history,
        'monthly_returns': monthly_returns,
        'rebalance_dates': rebalance_dates,
        'parameters': {
            'rebalance_frequency': rebalance_frequency,
            'lookback_months': lookback_months,
            'top_n': top_n,
            'transaction_fee': TRANSACTION_FEE,
            'slippage': SLIPPAGE
        }
    }
    
    return result


def calculate_mdd(portfolio_values):
    """최대낙폭 계산"""
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


def calculate_sharpe_ratio(returns, risk_free_rate=0.05, frequency='monthly'):
    """샤프비율 계산"""
    if not returns or len(returns) < 2:
        return 0.0
    
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    if frequency == 'monthly':
        periods_per_year = 12
        period_rf = (1 + risk_free_rate) ** (1/12) - 1
    else:  # daily
        periods_per_year = 252
        period_rf = (1 + risk_free_rate) ** (1/252) - 1
    
    period_rf_pct = period_rf * 100
    sharpe = ((avg_return - period_rf_pct) / std_dev) * (periods_per_year ** 0.5)
    
    return sharpe


def calculate_win_rate(returns):
    """승률 계산"""
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r['return'] > 0)
    return (wins / len(returns)) * 100 if returns else 0.0


def main():
    """메인 실행 함수"""
    # 백테스팅 기간 설정
    start_date = datetime(2010, 1, 1)
    end_date = datetime.now()
    
    logger.info("="*80)
    logger.info("2010년부터 현재까지 장기 백테스팅")
    logger.info("="*80)
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"약 {(end_date - start_date).days / 365.25:.1f}년")
    logger.info("\n⚠️  이 작업은 오랜 시간이 걸릴 수 있습니다 (30분 ~ 1시간)")
    logger.info("⚠️  중단하려면 Ctrl+C를 누르세요\n")
    
    # 티커 풀 준비
    tickers_pool = SP500_TICKERS
    logger.info(f"티커 풀: {len(tickers_pool)}개 종목")
    
    # 백테스팅 실행
    try:
        result = simulate_longterm_portfolio(
            start_date=start_date,
            end_date=end_date,
            tickers_pool=tickers_pool,
            initial_capital=10000,
            rebalance_frequency='weekly',
            lookback_months=3,
            top_n=10
        )
        
        if result:
            # 결과 출력
            logger.info("\n" + "="*80)
            logger.info("최종 결과")
            logger.info("="*80)
            logger.info(f"\n[기본 정보]")
            logger.info(f"기간: {result['start_date']} ~ {result['end_date']} ({result['years']:.2f}년)")
            logger.info(f"초기 자본: ${result['initial_capital']:,.0f}")
            logger.info(f"최종 가치: ${result['final_value']:,.0f}")
            
            logger.info(f"\n[수익률]")
            logger.info(f"총 수익률: {result['total_return']:+.2f}%")
            logger.info(f"연평균 수익률 (CAGR): {result['cagr']:+.2f}%")
            logger.info(f"월평균 수익률: {result['avg_monthly_return']:+.2f}%")
            
            logger.info(f"\n[리스크]")
            logger.info(f"최대낙폭 (MDD): {result['mdd']:.2f}%")
            logger.info(f"변동성 (월별): {result['volatility']:.2f}%")
            logger.info(f"샤프비율: {result['sharpe_ratio']:.2f}")
            logger.info(f"승률: {result['win_rate']:.2f}%")
            
            logger.info(f"\n[거래 정보]")
            logger.info(f"총 리밸런싱 횟수: {result['total_rebalances']}회")
            logger.info(f"총 거래 횟수: {result['total_trades']}회")
            logger.info(f"총 거래 비용: ${result['total_transaction_costs']:,.2f}")
            logger.info(f"거래 비용 비율: {result['transaction_cost_pct']:.2f}% (초기 자본 대비)")
            
            logger.info(f"\n[최고/최악의 달]")
            logger.info(f"최고 수익월: {result['best_month']['date']} ({result['best_month']['return']:+.2f}%)")
            logger.info(f"최악 수익월: {result['worst_month']['date']} ({result['worst_month']['return']:+.2f}%)")
            
            # 주요 시점 가치 출력
            logger.info(f"\n[주요 시점 포트폴리오 가치]")
            milestones = [2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024]
            for year in milestones:
                year_data = [h for h in result['portfolio_history'] if h['date'].startswith(str(year))]
                if year_data:
                    first_record = year_data[0]
                    value_vs_initial = ((first_record['value'] - result['initial_capital']) / result['initial_capital']) * 100
                    logger.info(f"{year}년: ${first_record['value']:,.0f} ({value_vs_initial:+.1f}%)")
            
            # JSON 저장
            output_path = Path(DATA_DIR) / 'longterm_backtest_2010_2024_weekly.json'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n결과 저장: {output_path}")
            
            # 간단한 통계
            if result['monthly_returns']:
                positive_months = sum(1 for r in result['monthly_returns'] if r['return'] > 0)
                negative_months = sum(1 for r in result['monthly_returns'] if r['return'] < 0)
                logger.info(f"\n[월별 통계]")
                logger.info(f"수익 월: {positive_months}개월 ({positive_months/len(result['monthly_returns'])*100:.1f}%)")
                logger.info(f"손실 월: {negative_months}개월 ({negative_months/len(result['monthly_returns'])*100:.1f}%)")
            
            logger.info("\n" + "="*80)
            logger.info("백테스팅 완료!")
            logger.info("="*80)
            
            # Telegram 전송
            try:
                from telegram_notifier import send_telegram_message
                
                message = f"""
📊 **장기 백테스팅 결과 (2010-2025)**

━━━━━━━━━━━━━━━━━━━━

📅 **기간 정보**
• 기간: {result['start_date']} ~ {result['end_date']}
• 투자 기간: {result['years']:.1f}년
• 리밸런싱: {result['parameters']['rebalance_frequency']}

💰 **수익률**
• 초기 자본: ${result['initial_capital']:,.0f}
• 최종 가치: ${result['final_value']:,.0f}
• 총 수익률: {result['total_return']:+.2f}%
• 연평균 수익률 (CAGR): {result['cagr']:+.2f}%
• 월평균 수익률: {result['avg_monthly_return']:+.2f}%

📉 **리스크 지표**
• 최대낙폭 (MDD): {result['mdd']:.2f}%
• 변동성 (월별): {result['volatility']:.2f}%
• 샤프비율: {result['sharpe_ratio']:.2f}
• 승률: {result['win_rate']:.1f}%

💸 **거래 정보**
• 총 리밸런싱: {result['total_rebalances']:,}회
• 총 거래: {result['total_trades']:,}회
• 총 거래 비용: ${result['total_transaction_costs']:,.2f}
• 비용 비율: {result['transaction_cost_pct']:.2f}%

🎯 **최고/최악의 달**
• 최고: {result['best_month']['date']} ({result['best_month']['return']:+.2f}%)
• 최악: {result['worst_month']['date']} ({result['worst_month']['return']:+.2f}%)

━━━━━━━━━━━━━━━━━━━━

📈 **주요 시점 가치**
"""
                
                # 주요 연도별 가치 추가
                milestones = [2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024]
                for year in milestones:
                    year_data = [h for h in result['portfolio_history'] if h['date'].startswith(str(year))]
                    if year_data:
                        first_record = year_data[0]
                        value_vs_initial = ((first_record['value'] - result['initial_capital']) / result['initial_capital']) * 100
                        message += f"\n• {year}년: ${first_record['value']:,.0f} ({value_vs_initial:+.1f}%)"
                
                message += f"\n\n💡 **분석**"
                message += f"\n• 수익 월: {int(result['win_rate'] * len(result['monthly_returns']) / 100)}개월"
                message += f"\n• 손실 월: {len(result['monthly_returns']) - int(result['win_rate'] * len(result['monthly_returns']) / 100)}개월"
                
                if result['parameters']['rebalance_frequency'] == 'weekly':
                    message += f"\n\n⚠️ 주간 리밸런싱은 거래 비용이 높아 실전에서는 월간 추천!"
                
                logger.info("\nTelegram으로 결과 전송 중...")
                send_telegram_message(message)
                logger.info("✅ Telegram 전송 성공!")
                
            except Exception as e:
                logger.error(f"Telegram 전송 실패: {e}")
            
            return result
        
    except KeyboardInterrupt:
        logger.info("\n\n사용자에 의해 중단되었습니다.")
        return None
    except Exception as e:
        logger.error(f"\n백테스팅 중 오류 발생: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    result = main()
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)

