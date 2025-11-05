# Discord 알림 모듈
import requests
from datetime import datetime
from config import ENABLE_DISCORD_NOTIFICATIONS, DISCORD_WEBHOOK_URL
from logger import get_logger

logger = get_logger()

def create_discord_message(current_df, yesterday_analysis, week_analysis):
    """Discord 메시지 생성"""
    if not ENABLE_DISCORD_NOTIFICATIONS:
        return None
    
    current_top10 = current_df.head(10)
    
    # Discord Embed 메시지 생성
    embed = {
        "title": f"📈 Finviz 대형주 3개월 수익률 상위 10개 - {datetime.now().strftime('%Y-%m-%d')}",
        "color": 0x00ff00,  # 초록색
        "timestamp": datetime.now().isoformat(),
        "fields": []
    }
    
    # 상위 10개 종목 필드
    top10_text = ""
    for i, row in current_top10.iterrows():
        change_emoji = "📈" if float(row['Change'].replace('%', '')) > 0 else "📉" if float(row['Change'].replace('%', '')) < 0 else "➡️"
        top10_text += f"{i+1}. {row['Ticker']} - {row['Perf Quart']} (${row['Price']}) {change_emoji}\n"
    
    embed["fields"].append({
        "name": "🏆 현재 상위 10개 종목",
        "value": top10_text,
        "inline": False
    })
    
    # 전날 비교
    if yesterday_analysis:
        yesterday_text = ""
        
        if yesterday_analysis['new_tickers']:
            yesterday_text += f"🆕 **새로 진입:** {', '.join(yesterday_analysis['new_tickers'])}\n"
        
        if yesterday_analysis['dropped_tickers']:
            yesterday_text += f"📉 **탈락:** {', '.join(yesterday_analysis['dropped_tickers'])}\n"
        
        if yesterday_analysis['top3_changes']:
            yesterday_text += "\n🔥 **상위 3개 종목 변화:**\n"
            for change in yesterday_analysis['top3_changes']:
                perf_emoji = "📈" if change['perf_change'] > 0 else "📉" if change['perf_change'] < 0 else "➡️"
                price_emoji = "💰" if change['price_change'] > 0 else "💸" if change['price_change'] < 0 else "💵"
                
                yesterday_text += f"• **{change['ticker']}:**\n"
                yesterday_text += f"  {perf_emoji} 수익률: {change['previous_perf']} → {change['current_perf']} ({change['perf_change']:+.1f}%)\n"
                yesterday_text += f"  {price_emoji} 가격: ${change['previous_price']} → ${change['current_price']} ({change['price_change']:+.2f}, {change['price_change_pct']:+.1f}%)\n"
        
        if yesterday_text:
            embed["fields"].append({
                "name": "📊 전날 대비 변화",
                "value": yesterday_text,
                "inline": False
            })
    
    # 일주일 전 비교
    if week_analysis:
        week_text = ""
        
        if week_analysis['new_tickers']:
            week_text += f"🆕 **새로 진입:** {', '.join(week_analysis['new_tickers'])}\n"
        
        if week_analysis['dropped_tickers']:
            week_text += f"📉 **탈락:** {', '.join(week_analysis['dropped_tickers'])}\n"
        
        if week_text:
            embed["fields"].append({
                "name": "📅 일주일 전 대비 변화",
                "value": week_text,
                "inline": False
            })
    
    # 푸터 추가
    embed["footer"] = {
        "text": "Finviz Daily Report 시스템",
        "icon_url": "https://finviz.com/favicon.ico"
    }
    
    return {
        "embeds": [embed]
    }

def send_to_discord(message, webhook_url=None):
    """Discord로 메시지 전송"""
    if not ENABLE_DISCORD_NOTIFICATIONS:
        logger.info("Discord 알림이 비활성화되어 있습니다.")
        return False
    
    if webhook_url is None:
        webhook_url = DISCORD_WEBHOOK_URL
    
    if not webhook_url:
        logger.warning("Discord 웹훅 URL이 설정되지 않았습니다.")
        return False
    
    try:
        response = requests.post(webhook_url, json=message)
        if response.status_code in [200, 204]:
            logger.info("Discord 메시지 전송 성공!")
            return True
        else:
            logger.error(f"Discord 전송 실패: {response.status_code}")
            logger.error(f"응답: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Discord 전송 중 오류: {e}")
        return False

def send_test_message():
    """테스트 메시지 전송"""
    test_embed = {
        "title": "🧪 Finviz Daily Report 테스트",
        "description": "Discord 알림이 정상적으로 작동합니다! ✅",
        "color": 0x00ff00,
        "timestamp": datetime.now().isoformat(),
        "footer": {
            "text": "테스트 메시지"
        }
    }
    
    return send_to_discord({"embeds": [test_embed]})

