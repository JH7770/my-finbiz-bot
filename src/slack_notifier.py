# Slack 알림 모듈
import requests
from datetime import datetime
from config import SLACK_WEBHOOK_URL
from analyzer import calculate_summary_stats, get_rank_changes_detailed

def create_slack_message(current_df, yesterday_analysis, week_analysis):
    """Slack 메시지 생성 - Block Kit 사용"""
    current_top10 = current_df.head(10)
    
    # 요약 통계 계산
    stats = calculate_summary_stats(current_df)
    
    # Block Kit 메시지 구조
    blocks = []
    
    # 헤더 블록
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📈 Finviz 대형주 3개월 수익률 상위 10개 - {datetime.now().strftime('%Y-%m-%d')}"
        }
    })
    
    # 요약 통계 섹션
    stats_text = f"📊 *요약 통계*\n"
    stats_text += f"• 평균 수익률: {stats['avg_performance']:.1f}%\n"
    stats_text += f"• 최고 수익률: {stats['max_performance']:.1f}%\n"
    stats_text += f"• 평균 가격: ${stats['avg_price']:.2f}\n"
    if 'biggest_gainer' in stats:
        stats_text += f"• 최대 상승: {stats['biggest_gainer']['ticker']} ({stats['biggest_gainer']['change']})\n"
    if 'biggest_loser' in stats:
        stats_text += f"• 최대 하락: {stats['biggest_loser']['ticker']} ({stats['biggest_loser']['change']})"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": stats_text
        }
    })
    
    # 구분선
    blocks.append({"type": "divider"})
    
    # 현재 상위 10개 종목
    top10_text = "🏆 *현재 상위 10개 종목*\n"
    
    # 순위 변화 정보 가져오기
    rank_changes = []
    if yesterday_analysis and 'rank_changes' in yesterday_analysis:
        rank_changes = {change['ticker']: change for change in yesterday_analysis['rank_changes']}
    
    for i, row in current_top10.iterrows():
        ticker = row['Ticker']
        perf = row['Perf Quart']
        price = row['Price']
        
        # 순위 변화 표시
        rank_indicator = ""
        if ticker in rank_changes:
            change = rank_changes[ticker]['change']
            if change > 0:
                rank_indicator = f" ↑{change}"
            elif change < 0:
                rank_indicator = f" ↓{abs(change)}"
            else:
                rank_indicator = " ➡️"
        else:
            rank_indicator = " 🆕"  # 새로 진입
        
        top10_text += f"{i+1}. {ticker} - {perf} (${price}){rank_indicator}\n"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": top10_text
        }
    })
    
    # 전날 비교
    if yesterday_analysis:
        blocks.append({"type": "divider"})
        
        yesterday_text = "📊 *전날 대비 변화*\n"
        
        if yesterday_analysis['new_tickers']:
            yesterday_text += f"• 🆕 새로 진입: {', '.join(yesterday_analysis['new_tickers'])}\n"
        if yesterday_analysis['dropped_tickers']:
            yesterday_text += f"• 📉 탈락: {', '.join(yesterday_analysis['dropped_tickers'])}\n"
        
        if yesterday_analysis['top3_changes']:
            yesterday_text += f"\n• 🔥 상위 3개 종목 변화:\n"
            for change in yesterday_analysis['top3_changes']:
                # 수익률 변화
                perf_change_str = f"+{change['perf_change']:.1f}%" if change['perf_change'] > 0 else f"{change['perf_change']:.1f}%"
                perf_emoji = "📈" if change['perf_change'] > 0 else "📉" if change['perf_change'] < 0 else "➡️"
                
                # 가격 변화
                price_change_str = f"+${change['price_change']:.2f}" if change['price_change'] > 0 else f"${change['price_change']:.2f}"
                price_pct_str = f"+{change['price_change_pct']:.1f}%" if change['price_change_pct'] > 0 else f"{change['price_change_pct']:.1f}%"
                price_emoji = "💰" if change['price_change'] > 0 else "💸" if change['price_change'] < 0 else "💵"
                
                yesterday_text += f"  • {change['ticker']}:\n"
                yesterday_text += f"    - {perf_emoji} 수익률: {change['previous_perf']} → {change['current_perf']} ({perf_change_str})\n"
                yesterday_text += f"    - {price_emoji} 가격: ${change['previous_price']} → ${change['current_price']} ({price_change_str}, {price_pct_str})\n"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": yesterday_text
            }
        })
    
    # 일주일 전 비교
    if week_analysis:
        blocks.append({"type": "divider"})
        
        week_text = "📅 *일주일 전 대비 변화*\n"
        if week_analysis['new_tickers']:
            week_text += f"• 🆕 새로 진입: {', '.join(week_analysis['new_tickers'])}\n"
        if week_analysis['dropped_tickers']:
            week_text += f"• 📉 탈락: {', '.join(week_analysis['dropped_tickers'])}\n"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": week_text
            }
        })
    
    # Block Kit 메시지 반환
    return {
        "blocks": blocks
    }

def send_to_slack(message, webhook_url=None):
    """Slack으로 메시지 전송"""
    if webhook_url is None:
        webhook_url = SLACK_WEBHOOK_URL
    
    try:
        # Block Kit 메시지인지 확인
        if isinstance(message, dict) and 'blocks' in message:
            payload = message
        else:
            # 기존 텍스트 메시지 형식
            payload = {'text': message}
        
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print("Slack 메시지 전송 성공!")
            return True
        else:
            print(f"Slack 전송 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
    except Exception as e:
        print(f"Slack 전송 중 오류: {e}")
        return False

def send_test_message():
    """테스트 메시지 전송"""
    test_message = "🧪 Finviz Daily Report 테스트 메시지입니다! 🚀\n\n✅ Slack 연결이 정상적으로 작동합니다! 🎉"
    return send_to_slack(test_message)
