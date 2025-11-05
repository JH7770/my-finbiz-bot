#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2022년 한 해 백테스팅 스크립트
2022년 1월 초 ~ 2022년 12월 말
"""

import sys
from pathlib import Path
from datetime import datetime

# src 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from historical_backtest import (
    get_historical_top_performers, 
    simulate_daily_rebalancing
)
from telegram_notifier import send_historical_backtest_result
from logger import get_logger
import json

logger = get_logger()

def main():
    """2022년 백테스팅 메인 함수"""
    
    # 2022년 날짜 설정
    start_date = datetime(2022, 1, 3)  # 2022년 1월 첫 거래일
    end_date = datetime(2022, 12, 30)  # 2022년 12월 마지막 거래일
    initial_capital = 10000
    
    logger.info("=" * 60)
    logger.info("2022년 백테스팅 시작")
    logger.info("=" * 60)
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.0f}")
    
    # 1. 대형주 상위 5개 선정 (2022년 1월 초 기준)
    logger.info(f"\n[1/3] 대형주 상위 5개 종목 선정 중...")
    large_result = get_historical_top_performers(
        screener_type="large",
        lookback_date=start_date,
        performance_period_days=90
    )
    
    if large_result is None:
        logger.error("대형주 종목 선정 실패")
        return None
    
    large_tickers = large_result['tickers'][:5]
    large_data = large_result['top10_data'][:5]
    logger.info(f"대형주 선정: {', '.join(large_tickers)}")
    
    # 2. 초대형주 상위 5개 선정 (2022년 1월 초 기준)
    logger.info(f"\n[2/3] 초대형주 상위 5개 종목 선정 중...")
    mega_result = get_historical_top_performers(
        screener_type="mega",
        lookback_date=start_date,
        performance_period_days=90
    )
    
    if mega_result is None:
        logger.error("초대형주 종목 선정 실패")
        return None
    
    mega_tickers = mega_result['tickers'][:5]
    mega_data = mega_result['top10_data'][:5]
    logger.info(f"초대형주 선정: {', '.join(mega_tickers)}")
    
    # 3. 결합 포트폴리오 시뮬레이션 (2022년 한 해)
    combined_tickers = large_tickers + mega_tickers
    logger.info(f"\n[3/3] 결합 포트폴리오 시뮬레이션 (2022년 한 해)")
    logger.info(f"종목: {', '.join(combined_tickers)}")
    
    # simulate_daily_rebalancing 함수를 사용하되 날짜를 2022년으로 제한
    simulation_result = simulate_daily_rebalancing_custom(
        tickers=combined_tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    if simulation_result is None:
        logger.error("시뮬레이션 실패")
        return None
    
    # 결과 구성
    result = {
        'screener_type': 'combined_2022',
        'large_top_n': 5,
        'mega_top_n': 5,
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
        'period': '2022년 한 해',
        'run_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 결과 출력
    logger.info("\n" + "="*60)
    logger.info("2022년 백테스팅 결과")
    logger.info("="*60)
    logger.info(f"대형주 5개: {', '.join(large_tickers)}")
    logger.info(f"초대형주 5개: {', '.join(mega_tickers)}")
    logger.info(f"\n[시뮬레이션 결과]")
    logger.info(f"기간: {simulation_result['start_date']} ~ {simulation_result['end_date']}")
    logger.info(f"초기 자본: ${simulation_result['initial_capital']:,.0f}")
    logger.info(f"최종 가치: ${simulation_result['final_value']:,.0f}")
    logger.info(f"총 수익률: {simulation_result['total_return']:+.2f}%")
    logger.info(f"연환산 수익률: {simulation_result['annualized_return']:+.2f}%")
    logger.info(f"최대낙폭 (MDD): {simulation_result['mdd']:.2f}%")
    logger.info(f"샤프비율: {simulation_result['sharpe_ratio']:.2f}")
    logger.info(f"승률: {simulation_result['win_rate']:.2f}%")
    logger.info(f"거래일수: {simulation_result['trading_days']}일")
    
    logger.info(f"\n[최고/최악의 날]")
    logger.info(f"최고 수익일: {simulation_result['best_day']['date']} ({simulation_result['best_day']['return']:+.2f}%)")
    logger.info(f"최악 수익일: {simulation_result['worst_day']['date']} ({simulation_result['worst_day']['return']:+.2f}%)")
    
    # Buy & Hold 수익률
    if 'buy_hold_returns' in simulation_result and simulation_result['buy_hold_returns']:
        logger.info(f"\n[개별 종목 Buy & Hold 수익률 (2022년)]")
        logger.info(f"매수일: {simulation_result['start_date']}, 매도일: {simulation_result['end_date']}")
        for i, stock in enumerate(simulation_result['buy_hold_returns'], 1):
            logger.info(f"{i:2d}. {stock['ticker']:6s}: ${stock['buy_price']:8.2f} → ${stock['current_price']:8.2f} ({stock['return_pct']:+7.2f}%)")
        avg_return = sum(s['return_pct'] for s in simulation_result['buy_hold_returns']) / len(simulation_result['buy_hold_returns'])
        logger.info(f"평균 수익률: {avg_return:+.2f}%")
    
    # Telegram 전송
    logger.info(f"\nTelegram으로 결과 전송 중...")
    success = send_historical_backtest_result(result)
    if success:
        logger.info("✅ Telegram 전송 성공!")
    else:
        logger.warning("⚠️ Telegram 전송 실패")
    
    # JSON 저장
    save_path = Path('daily_data') / 'backtest_2022.json'
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info(f"\n결과 저장: {save_path}")
    
    logger.info("\n" + "="*60)
    logger.info("2022년 백테스팅 완료")
    logger.info("="*60)
    
    return result


def simulate_daily_rebalancing_custom(tickers, start_date, end_date, initial_capital=10000):
    """
    매일 리밸런싱 시뮬레이션 (날짜 범위 커스텀)
    """
    import yfinance as yf
    from datetime import timedelta
    from config import RISK_FREE_RATE
    from historical_backtest import (
        calculate_mdd, 
        calculate_sharpe_ratio, 
        calculate_win_rate,
        calculate_buy_and_hold_returns
    )
    
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
    
    # 공통 날짜 찾기
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
                day_return += stock_return * (1 / num_stocks)
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


if __name__ == "__main__":
    try:
        result = main()
        
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        sys.exit(1)

