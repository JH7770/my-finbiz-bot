# Telegram 알림 모듈
import requests
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from analyzer import calculate_summary_stats

def create_telegram_message(current_df, yesterday_analysis, week_analysis, technical_analysis=None, screener_name="대형주", ma60_breaks=None, trailing_stops=None, breakout_highs=None, market_regime=None):
    """Telegram 메시지 생성 - 투자 전략 중심의 간결한 형식
    
    Args:
        current_df: 현재 데이터 DataFrame
        yesterday_analysis: 전날 분석 결과
        week_analysis: 일주일 전 분석 결과
        technical_analysis: 기술적 분석 결과 (선택사항)
        screener_name: 스크리너 이름 (대형주/초대형주)
        ma60_breaks: MA60 이탈 종목 리스트 (선택사항)
        trailing_stops: 트레일링 스탑 종목 리스트 (선택사항)
        breakout_highs: 신고가 돌파 종목 리스트 (선택사항)
        market_regime: 시장 상태 정보 (선택사항)
    """
    current_top10 = current_df.head(10)
    
    # 요약 통계 계산
    stats = calculate_summary_stats(current_df)
    
    # 메시지 헤더
    message = f"📈 *Finviz {screener_name} 3개월 수익률 상위 10개*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # 시장 필터 섹션
    if market_regime:
        message += "🌍 *시장 상태*\n"
        
        if market_regime.get('hold_cash', False):
            message += "⚠️ *약세장 감지 - 매수 금지*\n"
        else:
            message += "✅ *정상 시장 - 매수 가능*\n"
        
        message += f"• SPY: ${market_regime.get('spy_price', 0):.2f}\n"
        message += f"• MA200: ${market_regime.get('spy_ma200', 0):.2f}\n"
        message += f"• MA120: ${market_regime.get('spy_ma120', 0):.2f}\n"
        message += f"• VIX: {market_regime.get('vix', 0):.2f}\n"
        message += f"• 판단: {market_regime.get('reason', 'N/A')}\n"
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 요약 통계 섹션
    message += f"📊 *요약 통계*\n"
    message += f"• 평균 수익률: {stats['avg_performance']:.1f}%\n"
    message += f"• 최고 수익률: {stats['max_performance']:.1f}%\n"
    message += f"• 평균 가격: ${stats['avg_price']:.2f}\n"
    if 'biggest_gainer' in stats:
        message += f"• 최대 상승: {stats['biggest_gainer']['ticker']} ({stats['biggest_gainer']['change']})\n"
    if 'biggest_loser' in stats:
        message += f"• 최대 하락: {stats['biggest_loser']['ticker']} ({stats['biggest_loser']['change']})\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 현재 상위 5개 종목 (포트폴리오)
    message += "🏆 *포트폴리오 상위 5개 종목*\n\n"
    
    # 트레일링 스탑 종목 리스트
    trailing_stop_tickers = [s['ticker'] for s in trailing_stops] if trailing_stops else []
    # MA60 이탈 종목 리스트
    ma60_break_tickers = [b['ticker'] for b in ma60_breaks] if ma60_breaks else []
    # 신고가 돌파 종목 리스트
    breakout_tickers = [b['ticker'] for b in breakout_highs] if breakout_highs else []
    
    # 순위 변화 계산
    rank_changes_dict = {}
    if yesterday_analysis and 'rank_changes' in yesterday_analysis:
        # 리스트를 딕셔너리로 변환
        rank_changes_list = yesterday_analysis['rank_changes']
        if isinstance(rank_changes_list, list):
            rank_changes_dict = {item['ticker']: item for item in rank_changes_list}
        else:
            rank_changes_dict = rank_changes_list
    
    # 상위 5개만 표시
    top5 = current_top10.head(5)
    
    for i, row in top5.iterrows():
        ticker = row['Ticker']
        perf = row['Perf Quart']
        price = row['Price']
        
        # 순위 변화 표시
        rank_indicator = ""
        if ticker in rank_changes_dict:
            change = rank_changes_dict[ticker]['change']
            if change > 0:
                rank_indicator = f" ↑{change}"
            elif change < 0:
                rank_indicator = f" ↓{abs(change)}"
            else:
                rank_indicator = " ➡"
        else:
            rank_indicator = " 🆕"
        
        # 기술적 분석 아이콘
        tech_icon = ""
        if technical_analysis and ticker in technical_analysis:
            from technical_analyzer import get_technical_icon
            tech_icon = f" {get_technical_icon(technical_analysis[ticker])}"
        
        # 매매 신호 결정
        action_signal = ""
        if ticker in trailing_stop_tickers or ticker in ma60_break_tickers:
            action_signal = " → 🔴 *매도*"
        elif ticker in breakout_tickers and technical_analysis and ticker in technical_analysis:
            if technical_analysis[ticker].get('all_conditions_met', False):
                action_signal = " → 🟢 *매수*"
            else:
                action_signal = " → 🟡 *보유*"
        elif technical_analysis and ticker in technical_analysis:
            if technical_analysis[ticker].get('all_conditions_met', False):
                action_signal = " → 🟢 *보유*"
            else:
                action_signal = " → 🟡 *관망*"
        
        message += f"{i+1}. `{ticker}` - {perf} (${price}){rank_indicator}{tech_icon}{action_signal}\n"
    
    # 전날 비교
    if yesterday_analysis:
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "📊 *전날 대비 변화*\n\n"
        
        if yesterday_analysis['new_tickers']:
            message += f"• 🆕 새로 진입: {', '.join(['`' + t + '`' for t in yesterday_analysis['new_tickers']])}\n"
        if yesterday_analysis['dropped_tickers']:
            message += f"• 📉 탈락: {', '.join(['`' + t + '`' for t in yesterday_analysis['dropped_tickers']])}\n"
        
        if yesterday_analysis['top3_changes']:
            message += f"\n• 🔥 상위 3개 종목 변화:\n\n"
            for change in yesterday_analysis['top3_changes']:
                # 수익률 변화
                perf_change_str = f"+{change['perf_change']:.1f}%" if change['perf_change'] > 0 else f"{change['perf_change']:.1f}%"
                perf_emoji = "📈" if change['perf_change'] > 0 else "📉" if change['perf_change'] < 0 else "➡"
                
                # 가격 변화
                price_change_str = f"+${change['price_change']:.2f}" if change['price_change'] > 0 else f"${change['price_change']:.2f}"
                price_pct_str = f"+{change['price_change_pct']:.1f}%" if change['price_change_pct'] > 0 else f"{change['price_change_pct']:.1f}%"
                price_emoji = "💰" if change['price_change'] > 0 else "💸" if change['price_change'] < 0 else "💵"
                
                message += f"  *{change['ticker']}*:\n"
                message += f"  • {perf_emoji} 수익률: {change['previous_perf']} → {change['current_perf']} ({perf_change_str})\n"
                message += f"  • {price_emoji} 가격: ${change['previous_price']} → ${change['current_price']} ({price_change_str}, {price_pct_str})\n\n"
    
    # 일주일 전 비교
    if week_analysis:
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "📅 *일주일 전 대비 변화*\n\n"
        
        if week_analysis['new_tickers']:
            message += f"• 🆕 새로 진입: {', '.join(['`' + t + '`' for t in week_analysis['new_tickers']])}\n"
        if week_analysis['dropped_tickers']:
            message += f"• 📉 탈락: {', '.join(['`' + t + '`' for t in week_analysis['dropped_tickers']])}\n"
    
    # 신고가 돌파 (매수 신호)
    if breakout_highs and len(breakout_highs) > 0:
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "🚀 *신고가 돌파 (매수 신호)*\n\n"
        
        for breakout in breakout_highs:
            ticker = breakout['ticker']
            current = breakout['current_price']
            prev_high = breakout['previous_high']
            breakout_pct = breakout['breakout_percent']
            
            message += f"• `{ticker}`: ${current:.2f}\n"
            message += f"  📊 전 최고가: ${prev_high:.2f}\n"
            message += f"  🎯 돌파율: +{breakout_pct:.1f}%\n"
        
        message += f"\n🎉 *총 {len(breakout_highs)}개 종목이 3개월 신고가 경신!*\n"
        message += f"💡 *권장: 매수 또는 추가 매수 검토*\n"
    
    # 트레일링 스탑 경고 (개선된 조건)
    if trailing_stops and len(trailing_stops) > 0:
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "🔴 *트레일링 스탑 경고 (매도 신호)*\n\n"
        
        for stop in trailing_stops:
            ticker = stop['ticker']
            current = stop['current_price']
            ma20 = stop['ma20']
            distance = stop['distance']
            buffer_pct = stop.get('buffer_pct', 1.0)
            atr_pct = stop.get('atr_pct', 0.0)
            ma20_slope = stop.get('ma20_slope', 0.0)
            
            message += f"• `{ticker}`: ${current:.2f}\n"
            message += f"  📊 MA20: ${ma20:.2f} (기울기: {ma20_slope:.2f}%)\n"
            message += f"  📉 이탈폭: {distance:.1f}%\n"
            message += f"  🛡️ 버퍼: {buffer_pct:.1f}% (ATR: {atr_pct:.1f}%)\n"
        
        message += f"\n🚨 *총 {len(trailing_stops)}개 종목이 조건 충족*\n"
        message += f"💡 *조건: 버퍼(min 1% or 0.5×ATR) + 2일 연속 + MA20↓*\n"
        message += f"💡 *권장: 즉시 매도 검토*\n"
    
    # MA60 이탈 경고 (손절 신호)
    if ma60_breaks and len(ma60_breaks) > 0:
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "🚨 *MA60 이탈 경고 (손절 신호)*\n\n"
        
        for break_info in ma60_breaks:
            ticker = break_info['ticker']
            price = break_info['current_price']
            ma60 = break_info['ma60']
            distance = break_info['distance']
            
            message += f"• `{ticker}`: ${price:.2f} (MA60 ${ma60:.2f}, {distance:.1f}% 이탈)\n"
        
        message += f"\n⚠️ *총 {len(ma60_breaks)}개 종목이 60일선을 이탈했습니다.*\n"
        message += f"💡 *권장: 손절 검토*\n"
    
    # 기술적 분석 요약 (상위 5개만)
    if technical_analysis:
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        message += "📊 *기술적 분석 (이동평균선)*\n\n"
        
        # 상위 5개 종목의 티커 리스트
        top5_tickers = top5['Ticker'].tolist()
        
        # 상위 5개에 대해서만 조건 만족 여부 집계
        all_conditions_met = [ticker for ticker in top5_tickers if ticker in technical_analysis and technical_analysis[ticker].get('all_conditions_met', False)]
        partial_met = [ticker for ticker in top5_tickers if ticker in technical_analysis and not technical_analysis[ticker].get('all_conditions_met', False) and technical_analysis[ticker].get('status') == 'success']
        no_data = [ticker for ticker in top5_tickers if ticker not in technical_analysis or technical_analysis[ticker].get('status') != 'success']
        
        message += f"• ✅ 모든 조건 만족: {len(all_conditions_met)}개\n"
        if all_conditions_met:
            message += f"  → {', '.join(['`' + t + '`' for t in all_conditions_met])}\n"
        
        message += f"• ⚠️ 부분 조건 만족: {len(partial_met)}개\n"
        if partial_met:
            message += f"  → {', '.join(['`' + t + '`' for t in partial_met])}\n"
        
        if no_data:
            message += f"• ❓ 데이터 없음: {len(no_data)}개\n"
        
        message += f"\n*조건:* 현재가 > 60일선 > 120일선\n"
    
    return message

def send_to_telegram(message, bot_token=None, chat_id=None):
    """Telegram으로 메시지 전송"""
    if bot_token is None:
        bot_token = TELEGRAM_BOT_TOKEN
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID
    
    if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Telegram Bot Token이 설정되지 않았습니다.")
        return False
    
    if not chat_id or chat_id == "YOUR_TELEGRAM_CHAT_ID_HERE":
        print("Telegram Chat ID가 설정되지 않았습니다.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("Telegram 메시지 전송 성공!")
            return True
        else:
            print(f"Telegram 전송 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
    except Exception as e:
        print(f"Telegram 전송 중 오류: {e}")
        return False

def send_test_message():
    """테스트 메시지 전송"""
    test_message = "🧪 *Finviz Daily Report 테스트 메시지입니다!* 🚀\n\n✅ Telegram 연결이 정상적으로 작동합니다! 🎉"
    return send_to_telegram(test_message)

def create_historical_backtest_message(result):
    """3개월 역산 백테스팅 결과 메시지 생성
    
    Args:
        result: run_historical_backtest() 또는 run_combined_backtest() 함수의 반환값
    
    Returns:
        Telegram 메시지 문자열
    """
    if result is None:
        return "❌ 백테스팅 결과를 생성할 수 없습니다."
    
    selection = result['selection']
    simulation = result['simulation']
    screener_type = result['screener_type']
    
    # 결합 백테스팅 여부 확인
    is_combined = screener_type == 'combined'
    
    if is_combined:
        screener_name = "결합 포트폴리오"
        message = f"📊 *3개월 역산 백테스팅 결과*\n"
        message += f"*대형주 {result['large_top_n']}개 + 초대형주 {result['mega_top_n']}개*\n"
    else:
        screener_name = "대형주" if screener_type == "large" else "초대형주"
        top_n = result.get('top_n', 10)
        message = f"📊 *3개월 역산 백테스팅 결과 ({screener_name})*\n"
        message += f"*상위 {top_n}개 종목*\n"
    
    message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 선정된 종목 표시
    if is_combined:
        # 결합 백테스팅
        large_data = selection['large']['data']
        mega_data = selection['mega']['data']
        
        message += f"🎯 *선정 기준일: {result['run_date'][:10]}*\n\n"
        
        message += f"📈 *대형주 상위 {len(large_data)}개*\n"
        for i, stock in enumerate(large_data, 1):
            ticker = stock['ticker']
            performance = stock['performance']
            message += f"{i}. `{ticker}` - {performance:+.2f}%\n"
        
        message += f"\n📊 *초대형주 상위 {len(mega_data)}개*\n"
        for i, stock in enumerate(mega_data, 1):
            ticker = stock['ticker']
            performance = stock['performance']
            message += f"{i}. `{ticker}` - {performance:+.2f}%\n"
    else:
        # 단일 백테스팅
        message += f"🎯 *선정 기준일: {selection['selection_date']}*\n"
        top_n = len(selection['top10_data'])
        message += f"3개월 수익률 기준 상위 {top_n}개 종목:\n\n"
        
        for i, stock in enumerate(selection['top10_data'], 1):
            ticker = stock['ticker']
            performance = stock['performance']
            message += f"{i:2d}. `{ticker}` - {performance:+.2f}%\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 시뮬레이션 결과
    message += "💰 *매일 리밸런싱 시뮬레이션 결과*\n\n"
    message += f"• 기간: `{simulation['start_date']}` ~ `{simulation['end_date']}`\n"
    message += f"• 초기 자본: ${simulation['initial_capital']:,.0f}\n"
    message += f"• 최종 가치: ${simulation['final_value']:,.0f}\n"
    message += f"• 총 수익률: *{simulation['total_return']:+.2f}%*\n"
    message += f"• 연환산 수익률: *{simulation['annualized_return']:+.2f}%*\n"
    message += f"• 거래일수: {simulation['trading_days']}일\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 리스크 지표
    message += "📉 *리스크 지표*\n\n"
    message += f"• 최대낙폭 (MDD): {simulation['mdd']:.2f}%\n"
    message += f"• 샤프비율: {simulation['sharpe_ratio']:.2f}\n"
    message += f"• 승률: {simulation['win_rate']:.2f}%\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 최고/최악의 날
    message += "📈 *최고 수익일*\n"
    message += f"• 날짜: `{simulation['best_day']['date']}`\n"
    message += f"• 수익률: {simulation['best_day']['return']:+.2f}%\n\n"
    
    message += "📉 *최악 수익일*\n"
    message += f"• 날짜: `{simulation['worst_day']['date']}`\n"
    message += f"• 수익률: {simulation['worst_day']['return']:+.2f}%\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 간단한 성과 차트 (텍스트 기반)
    message += "📊 *포트폴리오 가치 추이 (주요 지점)*\n\n"
    
    # 5개 지점만 표시 (시작, 25%, 50%, 75%, 종료)
    history = simulation['portfolio_history']
    if len(history) >= 5:
        indices = [0, len(history)//4, len(history)//2, 3*len(history)//4, -1]
        for idx in indices:
            point = history[idx]
            value = point['value']
            date = point['date']
            change = ((value - simulation['initial_capital']) / simulation['initial_capital']) * 100
            
            # 바 차트 (간단히)
            bar_length = int(abs(change) / 5)  # 5%당 1개 바
            bar = "▓" * min(bar_length, 20)
            
            message += f"`{date}` ${value:,.0f} ({change:+.1f}%)\n"
            if change >= 0:
                message += f"🟢 {bar}\n"
            else:
                message += f"🔴 {bar}\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Buy & Hold 수익률 (개별 종목)
    if 'buy_hold_returns' in simulation and simulation['buy_hold_returns']:
        message += "📌 *개별 종목 Buy & Hold 수익률*\n"
        message += f"_({simulation['start_date']} 매수 → 현재 보유)_\n\n"
        
        buy_hold = simulation['buy_hold_returns']
        for i, stock in enumerate(buy_hold, 1):
            ticker = stock['ticker']
            buy_price = stock['buy_price']
            current_price = stock['current_price']
            return_pct = stock['return_pct']
            
            # 이모지 선택
            if return_pct > 50:
                emoji = "🚀"
            elif return_pct > 20:
                emoji = "📈"
            elif return_pct > 0:
                emoji = "✅"
            elif return_pct > -10:
                emoji = "⚠️"
            else:
                emoji = "🔴"
            
            message += f"{i:2d}. `{ticker}` {emoji}\n"
            message += f"    ${buy_price:.2f} → ${current_price:.2f} (*{return_pct:+.2f}%*)\n"
        
        # 평균 수익률
        avg_return = sum(s['return_pct'] for s in buy_hold) / len(buy_hold)
        message += f"\n💡 *평균 수익률: {avg_return:+.2f}%*\n"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 결론
    if simulation['total_return'] > 0:
        message += "✅ *결론: 수익 달성*\n"
        if simulation['sharpe_ratio'] > 1:
            message += "💡 우수한 샤프비율로 리스크 대비 수익이 양호합니다.\n"
    else:
        message += "❌ *결론: 손실 발생*\n"
        message += "⚠️ 해당 기간 동안 이 전략은 손실을 기록했습니다.\n"
    
    if simulation['mdd'] < -20:
        message += f"⚠️ 최대낙폭이 {simulation['mdd']:.1f}%로 높습니다. 리스크 관리가 필요합니다.\n"
    
    return message

def send_historical_backtest_result(result, bot_token=None, chat_id=None):
    """3개월 역산 백테스팅 결과를 Telegram으로 전송
    
    Args:
        result: run_historical_backtest() 함수의 반환값
        bot_token: Telegram Bot Token (None이면 config에서 가져옴)
        chat_id: Telegram Chat ID (None이면 config에서 가져옴)
    
    Returns:
        전송 성공 여부 (bool)
    """
    message = create_historical_backtest_message(result)
    return send_to_telegram(message, bot_token, chat_id)


# ===== 백테스팅 리포트 전송 함수 (GUI용) =====

def send_backtest_report(backtest_result, label="백테스팅 결과", bot_token=None, chat_id=None):
    """
    백테스팅 결과 요약 리포트 전송
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
        label: 리포트 라벨
        bot_token: Telegram Bot Token (None이면 config에서 가져옴)
        chat_id: Telegram Chat ID (None이면 config에서 가져옴)
    
    Returns:
        전송 성공 여부 (bool)
    """
    if not backtest_result:
        return False
    
    # 메시지 생성
    message = f"📊 *{label}*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 백테스팅 기간
    message += "📆 *백테스팅 기간*\n"
    message += f"• 시작일: {backtest_result.get('start_date', '-')}\n"
    message += f"• 종료일: {backtest_result.get('end_date', '-')}\n"
    message += f"• 거래일수: {backtest_result.get('num_rebalances', 0)}일\n\n"
    
    # 파라미터 정보
    if 'params' in backtest_result:
        params = backtest_result['params']
        message += "⚙️ *전략 파라미터*\n"
        message += f"• 종목 수: {params.get('num_stocks', '-')}\n"
        message += f"• 리밸런싱: {params.get('rebalance_frequency', '-')}\n"
        message += f"• 비중 방식: {params.get('weight_method', '-')}\n"
        message += f"• 시장 필터: {'활성화' if params.get('enable_market_filter') else '비활성화'}\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 성과 지표
    message += "💰 *성과 지표*\n"
    message += f"• 초기 자본: ${backtest_result.get('initial_capital', 0):,.0f}\n"
    message += f"• 최종 가치: ${backtest_result.get('final_value', 0):,.0f}\n"
    message += f"• 손익: ${backtest_result.get('final_value', 0) - backtest_result.get('initial_capital', 0):,.0f}\n\n"
    
    message += f"• 총 수익률: {backtest_result.get('total_return', 0):.2f}%\n"
    message += f"• 연환산 수익률: {backtest_result.get('annualized_return', 0):.2f}%\n"
    message += f"• 최대낙폭 (MDD): {backtest_result.get('mdd', 0):.2f}%\n"
    message += f"• 샤프비율: {backtest_result.get('sharpe_ratio', 0):.2f}\n"
    message += f"• 승률: {backtest_result.get('win_rate', 0):.2f}%\n\n"
    
    # 최고/최악의 거래일
    best_day = backtest_result.get('best_day', {})
    worst_day = backtest_result.get('worst_day', {})
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    message += "📈 *최고/최악 거래일*\n"
    message += f"• 최고: {best_day.get('date', '-')} ({best_day.get('return', 0):.2f}%)\n"
    message += f"• 최악: {worst_day.get('date', '-')} ({worst_day.get('return', 0):.2f}%)\n\n"
    
    # 시장 필터 정보
    cash_holding_days = backtest_result.get('cash_holding_days', 0)
    if cash_holding_days > 0:
        message += f"🏦 시장 필터로 {cash_holding_days}일 동안 현금 보유\n"
        message += f"   (전체의 {backtest_result.get('cash_holding_ratio', 0):.1f}%)\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    
    return send_to_telegram(message, bot_token, chat_id)


def send_backtest_chart(fig, caption="백테스팅 차트", bot_token=None, chat_id=None):
    """
    Plotly 차트를 PNG로 변환하여 전송
    
    Args:
        fig: Plotly Figure 객체
        caption: 차트 캡션
        bot_token: Telegram Bot Token (None이면 config에서 가져옴)
        chat_id: Telegram Chat ID (None이면 config에서 가져옴)
    
    Returns:
        전송 성공 여부 (bool)
    """
    if not fig:
        return False
    
    try:
        import io
        
        # Plotly 차트를 이미지로 변환
        img_bytes = fig.to_image(format="png", width=1200, height=600)
        
        # Telegram API 엔드포인트
        if bot_token is None:
            bot_token = TELEGRAM_BOT_TOKEN
        if chat_id is None:
            chat_id = TELEGRAM_CHAT_ID
        
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        # 파일 전송
        files = {
            'photo': ('chart.png', img_bytes, 'image/png')
        }
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            print(f"[텔레그램] 차트 전송 성공: {caption}")
            return True
        else:
            print(f"[텔레그램] 차트 전송 실패: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"[텔레그램] 차트 전송 에러: {e}")
        return False


def send_strategy_comparison_report(strategies, bot_token=None, chat_id=None):
    """
    전략 비교 리포트 전송
    
    Args:
        strategies: 전략 결과 리스트
        bot_token: Telegram Bot Token (None이면 config에서 가져옴)
        chat_id: Telegram Chat ID (None이면 config에서 가져옴)
    
    Returns:
        전송 성공 여부 (bool)
    """
    if not strategies:
        return False
    
    # 메시지 생성
    message = f"🔬 *전략 비교 분석*\n"
    message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"📊 총 {len(strategies)}개 전략 비교\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 각 전략 요약
    for idx, strategy in enumerate(strategies, 1):
        result = strategy['result']
        label = strategy.get('label', f"전략 {idx}")
        params = strategy.get('params', {})
        
        message += f"*{idx}. {label}*\n"
        message += f"• 종목 수: {params.get('num_stocks', '-')}\n"
        message += f"• 리밸런싱: {params.get('rebalance_frequency', '-')}\n"
        message += f"• 비중: {params.get('weight_method', '-')}\n"
        message += f"• 수익률: {result['total_return']:.2f}%\n"
        message += f"• 샤프비율: {result['sharpe_ratio']:.2f}\n"
        message += f"• MDD: {result['mdd']:.2f}%\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 최적 전략 추천
    best_sharpe = max(strategies, key=lambda x: x['result']['sharpe_ratio'])
    best_return = max(strategies, key=lambda x: x['result']['total_return'])
    best_mdd = min(strategies, key=lambda x: abs(x['result']['mdd']))
    
    message += "🏆 *최적 전략*\n\n"
    
    message += f"*샤프비율 최고*\n"
    message += f"• {best_sharpe.get('label', '전략')}\n"
    message += f"• 샤프비율: {best_sharpe['result']['sharpe_ratio']:.2f}\n"
    message += f"• 수익률: {best_sharpe['result']['total_return']:.2f}%\n\n"
    
    message += f"*총 수익률 최고*\n"
    message += f"• {best_return.get('label', '전략')}\n"
    message += f"• 수익률: {best_return['result']['total_return']:.2f}%\n"
    message += f"• 샤프비율: {best_return['result']['sharpe_ratio']:.2f}\n\n"
    
    message += f"*MDD 최소*\n"
    message += f"• {best_mdd.get('label', '전략')}\n"
    message += f"• MDD: {best_mdd['result']['mdd']:.2f}%\n"
    message += f"• 수익률: {best_mdd['result']['total_return']:.2f}%\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    
    return send_to_telegram(message, bot_token, chat_id)
