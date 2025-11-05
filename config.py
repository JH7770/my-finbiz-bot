# 설정 파일
import os

# Slack 웹훅 URL (실제 URL로 변경 필요)
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', 'SLACK_WEBHOOK_URL')

# 데이터 저장 디렉토리
DATA_DIR = "daily_data"

# 실행 시간 설정
SCHEDULE_TIME = "09:00"  # 매일 오전 9시

# Finviz URL
FINVIZ_URL = "https://finviz.com/screener.ashx?v=141&f=cap_large&o=-perf13w"
FINVIZ_URL_LARGE = "https://finviz.com/screener.ashx?v=141&f=cap_large&o=-perf13w"
FINVIZ_URL_MEGA = "https://finviz.com/screener.ashx?v=141&f=cap_mega&o=-perf13w"

# 스크리너 타입 설정
SCREENER_TYPES = os.getenv('SCREENER_TYPES', 'both')  # 'both', 'large', 'mega'

# 로깅 설정
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 알림 설정
ENABLE_EMAIL_NOTIFICATIONS = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
ENABLE_DISCORD_NOTIFICATIONS = os.getenv('ENABLE_DISCORD_NOTIFICATIONS', 'False').lower() == 'true'

# 이메일 설정 (선택사항)
EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')

# Discord 설정 (선택사항)
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# Telegram 설정
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'TELEGRAM_CHAT_ID')
ENABLE_TELEGRAM_NOTIFICATIONS = os.getenv('ENABLE_TELEGRAM_NOTIFICATIONS', 'True').lower() == 'true'

# 백테스팅 설정
ENABLE_BACKTESTING = os.getenv('ENABLE_BACKTESTING', 'True').lower() == 'true'
BACKTEST_WEEKS = int(os.getenv('BACKTEST_WEEKS', '30'))  # 최근 N주
BACKTEST_INITIAL_CAPITAL = float(os.getenv('BACKTEST_INITIAL_CAPITAL', '10000'))
RISK_FREE_RATE = float(os.getenv('RISK_FREE_RATE', '0.05'))  # 무위험 수익률 5%

# 재시도 설정
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))  # 초

# 시장 필터 설정
ENABLE_MARKET_FILTER = os.getenv('ENABLE_MARKET_FILTER', 'True').lower() == 'true'
VIX_THRESHOLD = float(os.getenv('VIX_THRESHOLD', '20'))  # VIX 임계값
