"""
설정 및 알림 관리 페이지
"""
import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from dashboard.utils.data_loader import clear_cache, get_available_dates
import config

# 페이지 설정
st.set_page_config(
    page_title="설정",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ 설정 및 관리")
st.markdown("---")

# 메인 콘텐츠
try:
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["🔧 시스템 설정", "📧 알림 설정", "🔄 데이터 관리", "ℹ️ 정보"])
    
    # 탭 1: 시스템 설정
    with tab1:
        st.header("🔧 시스템 설정")
        
        st.info("시스템 설정은 `config.py` 파일을 통해 관리됩니다.")
        
        # 현재 설정 표시
        st.subheader("📊 현재 설정")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**스크리너 설정**")
            st.write(f"- 스크리너 타입: `{config.SCREENER_TYPES}`")
            st.write(f"- 대형주 URL: [링크]({config.FINVIZ_URL_LARGE})")
            st.write(f"- 초대형주 URL: [링크]({config.FINVIZ_URL_MEGA})")
            
            st.write("")
            st.write("**데이터 설정**")
            st.write(f"- 데이터 디렉토리: `{config.DATA_DIR}`")
            st.write(f"- 로그 레벨: `{config.LOG_LEVEL}`")
        
        with col2:
            st.write("**백테스팅 설정**")
            st.write(f"- 백테스팅 활성화: `{config.ENABLE_BACKTESTING}`")
            st.write(f"- 백테스팅 기간: `{config.BACKTEST_WEEKS}주`")
            st.write(f"- 초기 자본: `${config.BACKTEST_INITIAL_CAPITAL:,.0f}`")
            st.write(f"- 무위험 수익률: `{config.RISK_FREE_RATE * 100}%`")
            
            st.write("")
            st.write("**스케줄 설정**")
            st.write(f"- 실행 시간: `{config.SCHEDULE_TIME}`")
        
        st.divider()
        
        st.warning("""
        ⚠️ **설정 변경 방법:**
        1. `config.py` 파일을 직접 편집하거나
        2. 환경 변수를 설정하세요.
        
        예시 (PowerShell):
        ```powershell
        $env:SCREENER_TYPES='mega'
        $env:BACKTEST_WEEKS='30'
        ```
        """)
    
    # 탭 2: 알림 설정
    with tab2:
        st.header("📧 알림 설정")
        
        st.subheader("현재 알림 채널 상태")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            telegram_enabled = config.ENABLE_TELEGRAM_NOTIFICATIONS
            if telegram_enabled:
                st.success("✅ Telegram 활성화")
                st.write(f"Bot Token: `{config.TELEGRAM_BOT_TOKEN[:20]}...`")
                st.write(f"Chat ID: `{config.TELEGRAM_CHAT_ID}`")
            else:
                st.error("❌ Telegram 비활성화")
        
        with col2:
            email_enabled = config.ENABLE_EMAIL_NOTIFICATIONS
            if email_enabled:
                st.success("✅ 이메일 활성화")
                st.write(f"SMTP: `{config.EMAIL_SMTP_SERVER}`")
                st.write(f"수신: `{config.EMAIL_TO}`")
            else:
                st.info("ℹ️ 이메일 비활성화")
        
        with col3:
            discord_enabled = config.ENABLE_DISCORD_NOTIFICATIONS
            if discord_enabled:
                st.success("✅ Discord 활성화")
                st.write(f"Webhook: `{config.DISCORD_WEBHOOK_URL[:30]}...`")
            else:
                st.info("ℹ️ Discord 비활성화")
        
        st.divider()
        
        st.info("""
        **알림 설정 변경:**
        - `config.py`에서 `ENABLE_TELEGRAM_NOTIFICATIONS`, `ENABLE_EMAIL_NOTIFICATIONS`, `ENABLE_DISCORD_NOTIFICATIONS` 값을 변경하세요.
        - 각 알림 채널의 API 키 및 URL도 설정해야 합니다.
        """)
        
        st.divider()
        
        # 테스트 알림 (실제 구현 시)
        st.subheader("🧪 알림 테스트")
        
        if st.button("📧 Telegram 테스트 메시지 전송", use_container_width=True):
            if telegram_enabled:
                try:
                    from telegram_notifier import send_to_telegram
                    
                    test_message = f"🧪 테스트 메시지\n\n대시보드에서 전송됨\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    success = send_to_telegram(test_message, config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
                    
                    if success:
                        st.success("✅ Telegram 메시지 전송 성공!")
                    else:
                        st.error("❌ Telegram 메시지 전송 실패")
                except Exception as e:
                    st.error(f"오류: {e}")
            else:
                st.warning("Telegram이 비활성화되어 있습니다.")
    
    # 탭 3: 데이터 관리
    with tab3:
        st.header("🔄 데이터 관리")
        
        # 캐시 관리
        st.subheader("💾 캐시 관리")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 캐시 새로고침", use_container_width=True):
                clear_cache()
                st.success("✅ 캐시가 클리어되었습니다!")
                st.rerun()
        
        with col2:
            st.info("캐시를 클리어하면 데이터가 다시 로드됩니다. (5분 캐시)")
        
        st.divider()
        
        # 데이터 상태
        st.subheader("📊 데이터 상태")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**대형주 (Large Cap)**")
            large_dates = get_available_dates("large")
            if large_dates:
                st.success(f"✅ {len(large_dates)}일치 데이터")
                st.write(f"- 최초: {large_dates[0]}")
                st.write(f"- 최신: {large_dates[-1]}")
            else:
                st.error("❌ 데이터 없음")
        
        with col2:
            st.write("**초대형주 (Mega Cap)**")
            mega_dates = get_available_dates("mega")
            if mega_dates:
                st.success(f"✅ {len(mega_dates)}일치 데이터")
                st.write(f"- 최초: {mega_dates[0]}")
                st.write(f"- 최신: {mega_dates[-1]}")
            else:
                st.error("❌ 데이터 없음")
        
        st.divider()
        
        # 수동 데이터 수집
        st.subheader("🔧 수동 데이터 수집")
        
        st.warning("""
        ⚠️ **주의:**
        데이터 수집은 메인 스크립트를 통해 수행하세요.
        """)
        
        st.code("""
# 한 번만 실행
python main.py

# 스케줄러로 자동 실행
python scheduler.py
        """, language="bash")
    
    # 탭 4: 정보
    with tab4:
        st.header("ℹ️ 시스템 정보")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**프로젝트 정보**")
            st.write("- 이름: Finviz 주식 분석 대시보드")
            st.write("- 버전: 1.0.0")
            st.write("- 프레임워크: Streamlit")
            
            st.write("")
            st.write("**주요 기능**")
            st.write("- 📊 실시간 상위 종목 모니터링")
            st.write("- 🔍 종목별 기술적 분석")
            st.write("- 💰 백테스팅 성과 시각화")
            st.write("- 📅 히스토리 데이터 탐색")
        
        with col2:
            st.write("**사용 라이브러리**")
            st.write("- Streamlit: 웹 대시보드")
            st.write("- Plotly: 인터랙티브 차트")
            st.write("- Pandas: 데이터 처리")
            st.write("- yfinance: 주가 데이터")
            st.write("- BeautifulSoup: 웹 스크래핑")
            
            st.write("")
            st.write("**데이터 소스**")
            st.write("- Finviz: 종목 스크리너")
            st.write("- Yahoo Finance: 주가 데이터")
        
        st.divider()
        
        st.success("""
        **대시보드 사용법:**
        1. 메인 페이지에서 전체 요약 확인
        2. 종목 상세 페이지에서 개별 종목 분석
        3. 백테스팅 페이지에서 전략 성과 확인
        4. 히스토리 페이지에서 과거 데이터 탐색
        5. 설정 페이지에서 시스템 관리
        """)
        
        st.divider()
        
        st.info("""
        **문의 및 지원:**
        - README.md 참고
        - GitHub Issues 활용
        """)

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)


