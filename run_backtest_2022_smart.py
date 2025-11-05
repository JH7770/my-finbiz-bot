#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2022년 스마트 백테스팅 - 매매 신호 반영
트레일링 스탑, MA60 손절, 기술적 분석 신호를 모두 고려
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# src 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from historical_backtest import (
    get_historical_top_performers,
    calculate_mdd,
    calculate_sharpe_ratio,
    calculate_win_rate
)
from telegram_notifier import send_to_telegram
from logger import get_logger
from config import RISK_FREE_RATE
import json

logger = get_logger()


def calculate_moving_averages(prices, periods=[20, 60, 120]):
    """이동평균선 계산"""
    ma_data = {}
    for period in periods:
        if len(prices) >= period:
            ma_data[f'MA{period}'] = prices.rolling(window=period).mean()
        else:
            ma_data[f'MA{period}'] = pd.Series([None] * len(prices), index=prices.index)
    return ma_data


def check_trailing_stop(ticker, current_price, ma20, prev_below_ma20):
    """
    트레일링 스탑 체크: MA20을 2일 이상 하향 이탈 시 매도
    
    Returns:
        (should_sell, days_below): 매도 여부, 이탈 일수
    """
    below_ma20 = current_price < ma20 if pd.notna(ma20) else False
    
    if below_ma20:
        days_below = prev_below_ma20.get(ticker, 0) + 1
        if days_below >= 2:
            return True, days_below
        return False, days_below
    else:
        return False, 0


def check_ma60_stop_loss(current_price, prev_price, ma60, prev_ma60):
    """
    MA60 손절: 전날 MA60 위 → 오늘 MA60 아래로 떨어지면 손절
    
    Returns:
        should_sell: 손절 여부
    """
    if pd.notna(ma60) and pd.notna(prev_ma60):
        was_above = prev_price >= prev_ma60
        now_below = current_price < ma60
        return was_above and now_below
    return False


def simulate_smart_strategy(tickers, start_date, end_date, initial_capital=10000):
    """
    스마트 전략 시뮬레이션: 매매 신호를 반영한 백테스팅
    
    매매 규칙:
    1. 트레일링 스탑: MA20을 2일 이상 하향 이탈 시 매도 → 현금 보유
    2. MA60 손절: MA60 하향 돌파 시 즉시 매도 → 현금 보유
    3. 매도 후 현금은 남은 종목들에 재분배
    4. 매도된 종목은 다시 매수하지 않음 (원칙)
    """
    logger.info(f"=== 스마트 전략 시뮬레이션 시작 ===")
    logger.info(f"종목: {', '.join(tickers)}")
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.2f}")
    
    # 모든 종목의 가격 데이터 가져오기
    price_data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            # 이동평균선 계산을 위해 충분한 기간의 데이터 가져오기
            hist_start = start_date - timedelta(days=180)
            hist = stock.history(start=hist_start, end=end_date + timedelta(days=1))
            
            if not hist.empty:
                price_data[ticker] = hist
                logger.info(f"{ticker}: {len(hist)}일 데이터")
            else:
                logger.warning(f"{ticker}: 가격 데이터 없음")
        except Exception as e:
            logger.error(f"{ticker}: 가격 데이터 가져오기 실패 - {e}")
    
    if len(price_data) == 0:
        logger.error("가격 데이터를 가져올 수 없습니다.")
        return None
    
    # 공통 날짜 찾기 (타임존 제거)
    common_dates = None
    for ticker, hist in price_data.items():
        # 타임존 제거
        hist.index = hist.index.tz_localize(None)
        dates_in_range = hist[hist.index >= start_date].index
        if common_dates is None:
            common_dates = set(dates_in_range)
        else:
            common_dates = common_dates.intersection(set(dates_in_range))
    
    common_dates = sorted(list(common_dates))
    logger.info(f"공통 거래일: {len(common_dates)}일")
    
    if len(common_dates) < 2:
        logger.error("충분한 공통 거래일이 없습니다.")
        return None
    
    # 이동평균선 계산
    ma_data = {}
    for ticker, hist in price_data.items():
        ma_data[ticker] = calculate_moving_averages(hist['Close'], [20, 60, 120])
    
    # 시뮬레이션 초기화
    portfolio_value = initial_capital
    cash = 0  # 매도한 현금
    active_positions = {ticker: True for ticker in tickers}  # 보유 중인 종목
    position_values = {ticker: initial_capital / len(tickers) for ticker in tickers}  # 각 종목 가치
    
    portfolio_history = [{'date': common_dates[0].strftime('%Y-%m-%d'), 'value': initial_capital}]
    daily_returns = []
    trade_log = []
    prev_below_ma20 = {ticker: 0 for ticker in tickers}
    prev_prices = {}
    
    # 초기 매수 기록
    for ticker in tickers:
        first_price = price_data[ticker].loc[common_dates[0]]['Close']
        trade_log.append({
            'date': common_dates[0].strftime('%Y-%m-%d'),
            'ticker': ticker,
            'action': 'BUY',
            'price': first_price,
            'reason': '초기 매수',
            'position_value': position_values[ticker]
        })
        prev_prices[ticker] = first_price
    
    # 매일 시뮬레이션
    for i in range(len(common_dates) - 1):
        current_date = common_dates[i]
        next_date = common_dates[i + 1]
        
        day_start_value = portfolio_value
        sells_today = []
        
        # 각 종목 체크
        for ticker in tickers:
            if not active_positions[ticker]:
                continue
            
            try:
                hist = price_data[ticker]
                current_price = hist.loc[current_date]['Close']
                next_price = hist.loc[next_date]['Close']
                
                ma20 = ma_data[ticker]['MA20'].loc[current_date]
                ma60 = ma_data[ticker]['MA60'].loc[current_date]
                
                should_sell = False
                sell_reason = ""
                
                # 1. 트레일링 스탑 체크
                trailing_stop, days_below = check_trailing_stop(
                    ticker, current_price, ma20, prev_below_ma20
                )
                prev_below_ma20[ticker] = days_below
                
                if trailing_stop:
                    should_sell = True
                    sell_reason = f"트레일링 스탑 (MA20 {days_below}일 이탈)"
                
                # 2. MA60 손절 체크
                if not should_sell and ticker in prev_prices:
                    prev_price = prev_prices[ticker]
                    prev_ma60 = ma_data[ticker]['MA60'].loc[current_date - timedelta(days=1)] if current_date - timedelta(days=1) in ma_data[ticker]['MA60'].index else None
                    
                    if check_ma60_stop_loss(current_price, prev_price, ma60, prev_ma60):
                        should_sell = True
                        sell_reason = "MA60 손절"
                
                # 매도 처리
                if should_sell:
                    sell_value = position_values[ticker]
                    cash += sell_value
                    active_positions[ticker] = False
                    
                    trade_log.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'ticker': ticker,
                        'action': 'SELL',
                        'price': current_price,
                        'reason': sell_reason,
                        'position_value': sell_value
                    })
                    
                    sells_today.append({
                        'ticker': ticker,
                        'reason': sell_reason,
                        'price': current_price,
                        'value': sell_value
                    })
                    
                    logger.info(f"{current_date.strftime('%Y-%m-%d')}: {ticker} 매도 (${current_price:.2f}) - {sell_reason}")
                    
                    position_values[ticker] = 0
                    prev_below_ma20[ticker] = 0
                else:
                    # 보유 중인 종목의 가치 업데이트
                    stock_return = (next_price - current_price) / current_price
                    position_values[ticker] = position_values[ticker] * (1 + stock_return)
                    prev_prices[ticker] = next_price
                
            except KeyError as e:
                logger.debug(f"{ticker}: {current_date} 데이터 누락 - {e}")
                continue
        
        # 매도로 생긴 현금을 남은 종목에 재분배
        if sells_today and cash > 0:
            active_tickers = [t for t in tickers if active_positions[t]]
            if active_tickers:
                cash_per_stock = cash / len(active_tickers)
                for ticker in active_tickers:
                    position_values[ticker] += cash_per_stock
                    
                logger.info(f"  → 현금 ${cash:.2f}를 {len(active_tickers)}개 종목에 재분배")
                cash = 0
        
        # 포트폴리오 가치 계산
        portfolio_value = sum(position_values.values()) + cash
        day_return = ((portfolio_value - day_start_value) / day_start_value) * 100
        
        daily_returns.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'return': day_return,
            'value': portfolio_value,
            'active_positions': sum(1 for p in active_positions.values() if p),
            'cash': cash
        })
        
        portfolio_history.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'value': portfolio_value
        })
        
        if sells_today:
            logger.info(f"{next_date.strftime('%Y-%m-%d')}: 포트폴리오 ${portfolio_value:,.2f} (보유: {sum(1 for p in active_positions.values() if p)}개)")
    
    # 최종 매도 (시뮬레이션 종료)
    final_sales = []
    for ticker in tickers:
        if active_positions[ticker] and position_values[ticker] > 0:
            final_price = price_data[ticker].loc[common_dates[-1]]['Close']
            initial_price = price_data[ticker].loc[common_dates[0]]['Close']
            return_pct = ((final_price - initial_price) / initial_price) * 100
            
            final_sales.append({
                'ticker': ticker,
                'buy_price': initial_price,
                'sell_price': final_price,
                'return_pct': return_pct,
                'held_days': len(common_dates)
            })
    
    # 성과 지표 계산
    final_value = portfolio_value
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    days = (common_dates[-1] - common_dates[0]).days
    if days > 0:
        annualized_return = ((final_value / initial_capital) ** (365 / days) - 1) * 100
    else:
        annualized_return = 0
    
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
        'trade_log': trade_log,
        'final_sales': final_sales,
        'total_trades': len(trade_log)
    }
    
    return result


def main(year=2022):
    """메인 실행 함수"""
    
    # 날짜 설정
    start_date = datetime(year, 1, 3)
    # 2025년이고 아직 12월 30일이 지나지 않았으면 현재 날짜 사용
    if year == 2025 and datetime.now() < datetime(2025, 12, 30):
        end_date = datetime.now() - timedelta(days=1)  # 어제까지
    else:
        end_date = datetime(year, 12, 30)
    initial_capital = 10000
    
    logger.info("=" * 60)
    logger.info(f"{year}년 스마트 백테스팅 시작 (매매 신호 반영)")
    logger.info("=" * 60)
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.0f}")
    logger.info("\n매매 규칙:")
    logger.info("1. 트레일링 스탑: MA20을 2일 이상 하향 이탈 시 매도")
    logger.info("2. MA60 손절: MA60 하향 돌파 시 즉시 매도")
    logger.info("3. 매도 자금은 남은 종목에 재분배")
    
    # 1. 대형주 상위 5개 선정
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
    logger.info(f"대형주 선정: {', '.join(large_tickers)}")
    
    # 2. 초대형주 상위 5개 선정
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
    logger.info(f"초대형주 선정: {', '.join(mega_tickers)}")
    
    # 3. 스마트 전략 시뮬레이션
    combined_tickers = large_tickers + mega_tickers
    logger.info(f"\n[3/3] 스마트 전략 시뮬레이션 ({year}년)")
    logger.info(f"종목: {', '.join(combined_tickers)}")
    
    simulation_result = simulate_smart_strategy(
        tickers=combined_tickers,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    if simulation_result is None:
        logger.error("시뮬레이션 실패")
        return None
    
    # 결과 출력
    logger.info("\n" + "="*60)
    logger.info(f"{year}년 스마트 백테스팅 결과")
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
    logger.info(f"총 거래 횟수: {simulation_result['total_trades']}회")
    
    logger.info(f"\n[최고/최악의 날]")
    logger.info(f"최고 수익일: {simulation_result['best_day']['date']} ({simulation_result['best_day']['return']:+.2f}%)")
    logger.info(f"최악 수익일: {simulation_result['worst_day']['date']} ({simulation_result['worst_day']['return']:+.2f}%)")
    
    # 거래 내역
    logger.info(f"\n[매도 거래 내역]")
    sell_trades = [t for t in simulation_result['trade_log'] if t['action'] == 'SELL']
    for trade in sell_trades:
        logger.info(f"{trade['date']}: {trade['ticker']:6s} ${trade['price']:8.2f} - {trade['reason']}")
    
    # 기간 보유 종목
    if simulation_result['final_sales']:
        logger.info(f"\n[기간 보유 종목 (최종까지)]")
        for stock in sorted(simulation_result['final_sales'], key=lambda x: x['return_pct'], reverse=True):
            logger.info(f"{stock['ticker']:6s}: ${stock['buy_price']:8.2f} → ${stock['sell_price']:8.2f} ({stock['return_pct']:+7.2f}%)")
    
    # Telegram 전송
    logger.info(f"\nTelegram으로 결과 전송 중...")
    message = create_smart_backtest_message(large_tickers, mega_tickers, simulation_result, year)
    success = send_to_telegram(message)
    if success:
        logger.info("✅ Telegram 전송 성공!")
    else:
        logger.warning("⚠️ Telegram 전송 실패")
    
    # JSON 저장
    result = {
        'strategy': 'smart',
        'period': f'{year}년',
        'large_tickers': large_tickers,
        'mega_tickers': mega_tickers,
        'simulation': simulation_result,
        'run_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    save_path = Path('daily_data') / f'backtest_{year}_smart.json'
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info(f"\n결과 저장: {save_path}")
    
    logger.info("\n" + "="*60)
    logger.info("스마트 백테스팅 완료")
    logger.info("="*60)
    
    return result


def create_smart_backtest_message(large_tickers, mega_tickers, sim, year=2022):
    """Telegram 메시지 생성"""
    message = f"📊 *{year}년 스마트 백테스팅 결과*\n"
    message += "_(매매 신호 반영)_\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "🎯 *선정 종목*\n"
    message += f"대형주 5개: {', '.join(large_tickers)}\n"
    message += f"초대형주 5개: {', '.join(mega_tickers)}\n\n"
    
    message += "📈 *매매 전략*\n"
    message += "• 트레일링 스탑: MA20 2일 이탈 시 매도\n"
    message += "• MA60 손절: MA60 하향 돌파 시 매도\n"
    message += "• 매도 자금은 남은 종목에 재분배\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "💰 *성과 지표*\n"
    message += f"• 기간: {sim['start_date']} ~ {sim['end_date']}\n"
    message += f"• 초기 자본: ${sim['initial_capital']:,.0f}\n"
    message += f"• 최종 가치: ${sim['final_value']:,.0f}\n"
    message += f"• 총 수익률: {sim['total_return']:+.2f}%\n"
    message += f"• 연환산 수익률: {sim['annualized_return']:+.2f}%\n"
    message += f"• 최대낙폭 (MDD): {sim['mdd']:.2f}%\n"
    message += f"• 샤프비율: {sim['sharpe_ratio']:.2f}\n"
    message += f"• 승률: {sim['win_rate']:.2f}%\n"
    message += f"• 총 거래: {sim['total_trades']}회\n\n"
    
    # 매도 거래
    sell_trades = [t for t in sim['trade_log'] if t['action'] == 'SELL']
    if sell_trades:
        message += "🔴 *매도 거래 내역*\n"
        for trade in sell_trades[:10]:  # 최대 10개
            message += f"• {trade['date']}: {trade['ticker']} - {trade['reason']}\n"
        if len(sell_trades) > 10:
            message += f"• ... 외 {len(sell_trades) - 10}건\n"
        message += "\n"
    
    # 기간 보유 종목
    if sim['final_sales']:
        message += "✅ *기간 보유 종목 (최종까지)*\n"
        for stock in sorted(sim['final_sales'], key=lambda x: x['return_pct'], reverse=True):
            message += f"• {stock['ticker']}: {stock['return_pct']:+.2f}%\n"
        message += "\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    message += "📝 무조건 보유 대비:\n"
    message += "• 기존 전략: -46.82%\n"
    message += f"• 스마트 전략: {sim['total_return']:+.2f}%\n"
    improvement = sim['total_return'] - (-46.82)
    message += f"• 개선폭: {improvement:+.2f}%p\n"
    
    return message


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='스마트 백테스팅 (매매 신호 반영)')
    parser.add_argument('--year', type=int, default=2022, 
                       help='백테스팅 연도 (기본: 2022)')
    
    args = parser.parse_args()
    
    try:
        result = main(year=args.year)
        
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

