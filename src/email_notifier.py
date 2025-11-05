# 이메일 알림 모듈
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import (
    ENABLE_EMAIL_NOTIFICATIONS, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT,
    EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO
)
from logger import get_logger

logger = get_logger()

def create_email_message(current_df, yesterday_analysis, week_analysis):
    """이메일 메시지 생성"""
    if not ENABLE_EMAIL_NOTIFICATIONS:
        return None
    
    current_top10 = current_df.head(10)
    
    # HTML 이메일 생성
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; }}
            .stats {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; }}
            .stock-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
            .positive {{ color: #27ae60; font-weight: bold; }}
            .negative {{ color: #e74c3c; font-weight: bold; }}
            .neutral {{ color: #7f8c8d; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #34495e; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📈 Finviz 대형주 3개월 수익률 상위 10개</h1>
            <p>{datetime.now().strftime('%Y년 %m월 %d일')}</p>
        </div>
        
        <div class="section">
            <h2>🏆 현재 상위 10개 종목</h2>
            <div class="stock-list">
                <table>
                    <tr>
                        <th>순위</th>
                        <th>종목</th>
                        <th>3개월 수익률</th>
                        <th>현재가</th>
                        <th>일일변화</th>
                    </tr>
    """
    
    for i, row in current_top10.iterrows():
        change_class = "positive" if float(row['Change'].replace('%', '')) > 0 else "negative" if float(row['Change'].replace('%', '')) < 0 else "neutral"
        html_content += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td><strong>{row['Ticker']}</strong></td>
                        <td>{row['Perf Quart']}</td>
                        <td>${row['Price']}</td>
                        <td class="{change_class}">{row['Change']}</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>
        </div>
    """
    
    # 전날 비교
    if yesterday_analysis:
        html_content += """
        <div class="section">
            <h2>📊 전날 대비 변화</h2>
        """
        
        if yesterday_analysis['new_tickers']:
            html_content += f"<p><strong>🆕 새로 진입:</strong> {', '.join(yesterday_analysis['new_tickers'])}</p>"
        
        if yesterday_analysis['dropped_tickers']:
            html_content += f"<p><strong>📉 탈락:</strong> {', '.join(yesterday_analysis['dropped_tickers'])}</p>"
        
        if yesterday_analysis['top3_changes']:
            html_content += "<h3>🔥 상위 3개 종목 변화</h3><ul>"
            for change in yesterday_analysis['top3_changes']:
                perf_class = "positive" if change['perf_change'] > 0 else "negative" if change['perf_change'] < 0 else "neutral"
                price_class = "positive" if change['price_change'] > 0 else "negative" if change['price_change'] < 0 else "neutral"
                
                html_content += f"""
                <li>
                    <strong>{change['ticker']}:</strong><br>
                    <span class="{perf_class}">수익률: {change['previous_perf']} → {change['current_perf']} ({change['perf_change']:+.1f}%)</span><br>
                    <span class="{price_class}">가격: ${change['previous_price']} → ${change['current_price']} ({change['price_change']:+.2f}, {change['price_change_pct']:+.1f}%)</span>
                </li>
                """
            html_content += "</ul>"
        
        html_content += "</div>"
    
    # 일주일 전 비교
    if week_analysis:
        html_content += """
        <div class="section">
            <h2>📅 일주일 전 대비 변화</h2>
        """
        
        if week_analysis['new_tickers']:
            html_content += f"<p><strong>🆕 새로 진입:</strong> {', '.join(week_analysis['new_tickers'])}</p>"
        
        if week_analysis['dropped_tickers']:
            html_content += f"<p><strong>📉 탈락:</strong> {', '.join(week_analysis['dropped_tickers'])}</p>"
        
        html_content += "</div>"
    
    html_content += """
        <div class="section">
            <p><em>이 보고서는 Finviz Daily Report 시스템에 의해 자동 생성되었습니다.</em></p>
        </div>
    </body>
    </html>
    """
    
    return html_content

def send_email(html_content, subject=None):
    """이메일 전송"""
    if not ENABLE_EMAIL_NOTIFICATIONS:
        logger.info("이메일 알림이 비활성화되어 있습니다.")
        return False
    
    if not all([EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO]):
        logger.warning("이메일 설정이 완전하지 않습니다.")
        return False
    
    if not html_content:
        logger.warning("이메일 내용이 없습니다.")
        return False
    
    try:
        # 이메일 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_USERNAME
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject or f"Finviz Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # HTML 내용 추가
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # SMTP 서버 연결 및 전송
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info("이메일 전송 성공!")
        return True
        
    except Exception as e:
        logger.error(f"이메일 전송 중 오류: {e}")
        return False

def send_test_email():
    """테스트 이메일 전송"""
    test_content = """
    <html>
    <body>
        <h1>🧪 Finviz Daily Report 테스트</h1>
        <p>이메일 알림이 정상적으로 작동합니다! ✅</p>
        <p>시간: {}</p>
    </body>
    </html>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    return send_email(test_content, "Finviz Daily Report 테스트")

