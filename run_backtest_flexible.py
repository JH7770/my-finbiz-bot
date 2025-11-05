#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
유연한 백테스팅 - 매매 신호 + 종목 교체 반영
- 매도 신호: 트레일링 스탑, MA60 손절
- 매수 신호: 기술적 조건 + 상위 종목
- 종목 수: 0~10개 유연하게
- 주간 리밸런싱: 매주 월요일 상위 종목 재조회
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from finviz_scraper import scrape_all_tickers_with_pagination
from historical_backtest import get_historical_top_performers
from logger import get_logger
from config import RISK_FREE_RATE
from telegram_notifier import send_to_telegram
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


def check_trailing_stop(current_price, ma20, days_below_ma20):
    """트레일링 스탑: MA20을 2일 이상 하향 이탈"""
    if pd.notna(ma20):
        below_ma20 = current_price < ma20
        if below_ma20:
            new_days = days_below_ma20 + 1
            return new_days >= 2, new_days
        else:
            return False, 0
    return False, 0


def check_ma60_stop(current_price, prev_price, ma60, prev_ma60):
    """MA60 손절: 전날 위 → 오늘 아래"""
    if pd.notna(ma60) and pd.notna(prev_ma60):
        was_above = prev_price >= prev_ma60
        now_below = current_price < ma60
        return was_above and now_below
    return False


def check_technical_condition(current_price, ma60, ma120):
    """기술적 조건: 현재가 > MA60 > MA120"""
    if pd.notna(ma60) and pd.notna(ma120):
        return current_price > ma60 and ma60 > ma120
    return False


def get_top_performers_at_date(screener_type, date, top_n=5):
    """특정 날짜의 상위 종목 조회"""
    result = get_historical_top_performers(
        screener_type=screener_type,
        lookback_date=date,
        performance_period_days=90
    )
    
    if result is None or 'tickers' not in result:
        return []
    
    return result['tickers'][:top_n]


def simulate_flexible_strategy(start_date, end_date, initial_capital=10000, 
                               rebalance_frequency='weekly'):
    """
    유연한 전략 시뮬레이션
    
    - 주간/월간 상위 종목 재조회
    - 매도 신호: 즉시 매도
    - 매수 신호: 기술적 조건 + 상위 종목
    - 종목 수: 0~10개 유연
    """
    logger.info(f"=== 유연한 전략 시뮬레이션 시작 ===")
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"초기 자본: ${initial_capital:,.2f}")
    logger.info(f"리밸런싱: {rebalance_frequency}")
    
    # 초기 상위 종목 선정 (대형주 5 + 초대형주 5)
    logger.info("\n[초기 포트폴리오 구성]")
    large_tickers = get_top_performers_at_date("large", start_date, top_n=5)
    mega_tickers = get_top_performers_at_date("mega", start_date, top_n=5)
    
    if not large_tickers or not mega_tickers:
        logger.error("초기 종목 선정 실패")
        return None
    
    initial_tickers = large_tickers + mega_tickers
    logger.info(f"대형주 5개: {', '.join(large_tickers)}")
    logger.info(f"초대형주 5개: {', '.join(mega_tickers)}")
    
    # 시뮬레이션 변수
    portfolio_value = initial_capital
    cash = initial_capital  # 처음엔 전액 현금
    positions = {}  # {ticker: {'shares': N, 'avg_price': P}}
    trade_log = []
    portfolio_history = []
    daily_returns = []
    
    # 거래 날짜 생성
    current = start_date
    trading_dates = []
    while current <= end_date:
        # 주말 제외
        if current.weekday() < 5:
            trading_dates.append(current)
        current += timedelta(days=1)
    
    logger.info(f"총 {len(trading_dates)}개 거래일")
    
    # 매일 시뮬레이션
    prev_below_ma20 = {}
    prev_prices = {}
    last_rebalance_date = None
    
    for i, current_date in enumerate(trading_dates):
        day_start_value = portfolio_value
        
        # 리밸런싱 날짜 체크 (매월 첫 주 월요일)
        should_rebalance = False
        if rebalance_frequency == 'monthly' and current_date.day <= 7 and current_date.weekday() == 0:
            should_rebalance = True
        elif rebalance_frequency == 'weekly' and current_date.weekday() == 0:
            should_rebalance = True
        
        # 리밸런싱: 상위 종목 재조회
        if should_rebalance and (last_rebalance_date is None or 
                                (current_date - last_rebalance_date).days >= 20):
            rebal_type = "매월" if rebalance_frequency == 'monthly' else "주간"
            logger.info(f"\n{current_date.strftime('%Y-%m-%d')}: {rebal_type} 리밸런싱")
            large_top = get_top_performers_at_date("large", current_date, top_n=5)
            mega_top = get_top_performers_at_date("mega", current_date, top_n=5)
            
            if large_top and mega_top:
                target_tickers = large_top + mega_top
                logger.info(f"  새 상위 10개: {', '.join(target_tickers)}")
                last_rebalance_date = current_date
            else:
                target_tickers = list(positions.keys())
        else:
            target_tickers = list(positions.keys())
        
        # 1. 기존 보유 종목 체크 (매도 신호)
        to_sell = []
        for ticker in list(positions.keys()):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=current_date - timedelta(days=180), 
                                    end=current_date + timedelta(days=1))
                
                if hist.empty:
                    continue
                
                hist.index = hist.index.tz_localize(None)
                
                if current_date not in hist.index:
                    continue
                
                current_price = hist.loc[current_date]['Close']
                ma_data = calculate_moving_averages(hist['Close'], [20, 60, 120])
                ma20 = ma_data['MA20'].loc[current_date]
                ma60 = ma_data['MA60'].loc[current_date]
                
                # 트레일링 스탑 체크
                days_below = prev_below_ma20.get(ticker, 0)
                stop_triggered, new_days = check_trailing_stop(current_price, ma20, days_below)
                prev_below_ma20[ticker] = new_days
                
                if stop_triggered:
                    to_sell.append((ticker, current_price, "트레일링 스탑"))
                    continue
                
                # MA60 손절 체크
                if ticker in prev_prices:
                    prev_date_idx = hist.index.get_loc(current_date) - 1
                    if prev_date_idx >= 0:
                        prev_ma60 = ma_data['MA60'].iloc[prev_date_idx]
                        prev_price = prev_prices[ticker]
                        
                        if check_ma60_stop(current_price, prev_price, ma60, prev_ma60):
                            to_sell.append((ticker, current_price, "MA60 손절"))
                            continue
                
                prev_prices[ticker] = current_price
                
            except Exception as e:
                logger.debug(f"{ticker} 체크 실패: {e}")
                continue
        
        # 매도 실행
        for ticker, price, reason in to_sell:
            if ticker in positions:
                shares = positions[ticker]['shares']
                sell_value = shares * price
                cash += sell_value
                
                trade_log.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'ticker': ticker,
                    'action': 'SELL',
                    'price': price,
                    'shares': shares,
                    'value': sell_value,
                    'reason': reason
                })
                
                logger.info(f"{current_date.strftime('%Y-%m-%d')}: {ticker} 매도 ${price:.2f} - {reason}")
                
                del positions[ticker]
                prev_below_ma20[ticker] = 0
        
        # 2. 매수 기회 체크 (리밸런싱 시점 + 현금 여유)
        if should_rebalance and cash > 0 and len(positions) < 10:
            # 현재 보유하지 않은 상위 종목 중 기술적 조건 만족하는 것 매수
            candidates = [t for t in target_tickers if t not in positions]
            
            for ticker in candidates[:3]:  # 한 번에 최대 3개씩 매수
                if cash < 100:  # 최소 매수 금액
                    break
                
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=current_date - timedelta(days=180),
                                        end=current_date + timedelta(days=1))
                    
                    if hist.empty:
                        continue
                    
                    hist.index = hist.index.tz_localize(None)
                    
                    if current_date not in hist.index:
                        continue
                    
                    current_price = hist.loc[current_date]['Close']
                    ma_data = calculate_moving_averages(hist['Close'], [20, 60, 120])
                    
                    ma60 = ma_data['MA60'].loc[current_date]
                    ma120 = ma_data['MA120'].loc[current_date]
                    
                    # 기술적 조건 체크
                    if check_technical_condition(current_price, ma60, ma120):
                        # 매수 실행 (현금의 일부 투자, 최대 10개 분산)
                        target_positions = min(10, len(target_tickers))
                        buy_amount = cash / (target_positions - len(positions))
                        buy_amount = min(buy_amount, cash)
                        
                        shares = buy_amount / current_price
                        positions[ticker] = {
                            'shares': shares,
                            'avg_price': current_price
                        }
                        
                        cash -= buy_amount
                        prev_below_ma20[ticker] = 0
                        prev_prices[ticker] = current_price
                        
                        trade_log.append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'ticker': ticker,
                            'action': 'BUY',
                            'price': current_price,
                            'shares': shares,
                            'value': buy_amount,
                            'reason': '기술적 조건 만족'
                        })
                        
                        logger.info(f"{current_date.strftime('%Y-%m-%d')}: {ticker} 매수 ${current_price:.2f} (${buy_amount:.0f})")
                        
                except Exception as e:
                    logger.debug(f"{ticker} 매수 실패: {e}")
                    continue
        
        # 3. 포트폴리오 가치 업데이트
        position_value = 0
        for ticker, pos in positions.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=current_date, end=current_date + timedelta(days=1))
                
                if not hist.empty:
                    hist.index = hist.index.tz_localize(None)
                    if current_date in hist.index:
                        current_price = hist.loc[current_date]['Close']
                        position_value += pos['shares'] * current_price
            except:
                # 가격 못 가져오면 전날 가격 사용
                position_value += pos['shares'] * pos['avg_price']
        
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
        
        # 진행 상황 로깅 (매월 1일)
        if current_date.day == 1:
            logger.info(f"{current_date.strftime('%Y-%m')}: 포트폴리오 ${portfolio_value:,.0f} (보유: {len(positions)}개, 현금: ${cash:,.0f})")
    
    # 성과 지표 계산
    final_value = portfolio_value
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    days = (trading_dates[-1] - trading_dates[0]).days
    if days > 0:
        annualized_return = ((final_value / initial_capital) ** (365 / days) - 1) * 100
    else:
        annualized_return = 0
    
    # MDD, 샤프비율, 승률 계산
    from historical_backtest import calculate_mdd, calculate_sharpe_ratio, calculate_win_rate
    
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
        'start_date': trading_dates[0].strftime('%Y-%m-%d'),
        'end_date': trading_dates[-1].strftime('%Y-%m-%d'),
        'initial_capital': initial_capital,
        'final_value': final_value,
        'final_cash': cash,
        'final_positions': len(positions),
        'total_return': total_return,
        'annualized_return': annualized_return,
        'mdd': mdd,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'trading_days': len(trading_dates),
        'best_day': best_day,
        'worst_day': worst_day,
        'portfolio_history': portfolio_history,
        'daily_returns': daily_returns,
        'trade_log': trade_log,
        'total_trades': len(trade_log),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades)
    }
    
    return result


def main(year=2022):
    """메인 실행 함수"""
    
    start_date = datetime(year, 1, 3)
    if year == 2025 and datetime.now() < datetime(2025, 12, 30):
        end_date = datetime.now() - timedelta(days=1)
    else:
        end_date = datetime(year, 12, 30)
    
    logger.info("=" * 60)
    logger.info(f"{year}년 유연한 백테스팅 (매매 신호 + 종목 교체)")
    logger.info("=" * 60)
    logger.info(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    logger.info("\n전략 규칙:")
    logger.info("1. 매월 첫 월요일: 상위 10개 재조회 및 리밸런싱")
    logger.info("2. 매도 신호: 트레일링 스탑 또는 MA60 손절")
    logger.info("3. 매수 신호: 기술적 조건 + 상위 종목")
    logger.info("4. 종목 수: 0~10개 유연 (상황에 따라)")
    logger.info("5. 매도 시 현금 보유 OK")
    
    # 시뮬레이션 실행
    result = simulate_flexible_strategy(
        start_date=start_date,
        end_date=end_date,
        initial_capital=10000,
        rebalance_frequency='monthly'
    )
    
    if result is None:
        logger.error("시뮬레이션 실패")
        return None
    
    # 결과 출력
    logger.info("\n" + "="*60)
    logger.info(f"{year}년 유연한 백테스팅 결과")
    logger.info("="*60)
    
    logger.info(f"\n[성과 지표]")
    logger.info(f"기간: {result['start_date']} ~ {result['end_date']}")
    logger.info(f"초기 자본: ${result['initial_capital']:,.0f}")
    logger.info(f"최종 가치: ${result['final_value']:,.0f}")
    logger.info(f"  - 현금: ${result['final_cash']:,.0f}")
    logger.info(f"  - 보유 종목: {result['final_positions']}개")
    logger.info(f"총 수익률: {result['total_return']:+.2f}%")
    logger.info(f"연환산 수익률: {result['annualized_return']:+.2f}%")
    logger.info(f"최대낙폭 (MDD): {result['mdd']:.2f}%")
    logger.info(f"샤프비율: {result['sharpe_ratio']:.2f}")
    logger.info(f"승률: {result['win_rate']:.2f}%")
    logger.info(f"거래일수: {result['trading_days']}일")
    
    logger.info(f"\n[거래 통계]")
    logger.info(f"총 거래: {result['total_trades']}회")
    logger.info(f"  - 매수: {result['buy_count']}회")
    logger.info(f"  - 매도: {result['sell_count']}회")
    
    logger.info(f"\n[최고/최악의 날]")
    logger.info(f"최고 수익일: {result['best_day']['date']} ({result['best_day']['return']:+.2f}%)")
    logger.info(f"최악 수익일: {result['worst_day']['date']} ({result['worst_day']['return']:+.2f}%)")
    
    # 월별 포트폴리오 변화
    logger.info(f"\n[월별 포트폴리오 상태]")
    monthly_snapshots = [h for h in result['portfolio_history'] if h['date'].endswith('-01')]
    for snapshot in monthly_snapshots[:12]:
        logger.info(f"{snapshot['date'][:7]}: ${snapshot['value']:,.0f} (보유: {snapshot['positions']}개, 현금: ${snapshot['cash']:,.0f})")
    
    # Telegram 전송
    logger.info(f"\nTelegram으로 결과 전송 중...")
    message = create_flexible_backtest_message(result, year)
    success = send_to_telegram(message)
    if success:
        logger.info("✅ Telegram 전송 성공!")
    else:
        logger.warning("⚠️ Telegram 전송 실패")
    
    # JSON 저장
    save_path = Path('daily_data') / f'backtest_{year}_flexible.json'
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump({
            'strategy': 'flexible',
            'year': year,
            'result': result
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"결과 저장: {save_path}")
    
    logger.info("\n" + "="*60)
    logger.info("유연한 백테스팅 완료")
    logger.info("="*60)
    
    return result


def create_flexible_backtest_message(result, year):
    """Telegram 메시지 생성"""
    message = f"📊 *{year}년 유연한 백테스팅*\n"
    message += "_(매매 신호 + 종목 교체)_\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "🎯 *전략 규칙*\n"
    message += "• 매월: 상위 10개 재조회\n"
    message += "• 매도: 트레일링 스탑 or MA60\n"
    message += "• 매수: 기술적 조건 만족 시\n"
    message += "• 종목 수: 0~10개 유연\n"
    message += "• 현금 보유: OK\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "💰 *성과 지표*\n"
    message += f"• 기간: {result['start_date']} ~ {result['end_date']}\n"
    message += f"• 초기 자본: ${result['initial_capital']:,.0f}\n"
    message += f"• 최종 가치: ${result['final_value']:,.0f}\n"
    message += f"  - 현금: ${result['final_cash']:,.0f}\n"
    message += f"  - 보유: {result['final_positions']}개\n"
    message += f"• 총 수익률: {result['total_return']:+.2f}%\n"
    message += f"• 연환산: {result['annualized_return']:+.2f}%\n"
    message += f"• MDD: {result['mdd']:.2f}%\n"
    message += f"• 샤프비율: {result['sharpe_ratio']:.2f}\n"
    message += f"• 승률: {result['win_rate']:.2f}%\n\n"
    
    message += "📈 *거래 통계*\n"
    message += f"• 총 거래: {result['total_trades']}회\n"
    message += f"  - 매수: {result['buy_count']}회\n"
    message += f"  - 매도: {result['sell_count']}회\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "💡 *특징*\n"
    message += "• 상황에 따라 현금 비중 조절\n"
    message += "• 하락장: 현금 보유로 손실 제한\n"
    message += "• 상승장: 기회 포착하여 매수\n"
    
    return message


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='유연한 백테스팅 (매매 신호 + 종목 교체)')
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

