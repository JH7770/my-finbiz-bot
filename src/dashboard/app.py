"""
Finviz 대시보드 - 메인 앱
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 유틸리티 임포트
from dashboard.utils.data_loader import (
    load_latest_data, get_latest_date, load_backtest_results,
    load_technical_analysis, load_data_by_date, get_available_dates,
    clear_cache, load_market_regime
)
from dashboard.components.metrics import (
    display_summary_cards, display_technical_status,
    display_signals, display_backtest_metrics, display_market_status
)
from dashboard.components.charts import (
    plot_pie_portfolio, plot_portfolio_value, plot_performance_comparison
)
from dashboard.components.tables import (
    display_top_stocks_table, display_comparison_table,
    display_new_dropped_stocks
)

# 페이지 설정
st.set_page_config(
    page_title="Finviz 주식 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 타이틀
st.title("📈 Finviz 주식 분석 대시보드")
st.markdown("---")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 스크리너 타입 선택
    screener_type = st.selectbox(
        "스크리너 타입",
        options=["large", "mega"],
        format_func=lambda x: "대형주 (Large Cap)" if x == "large" else "초대형주 (Mega Cap)",
        index=0
    )
    
    screener_name = "대형주" if screener_type == "large" else "초대형주"
    
    st.divider()
    
    # 새로고침 버튼
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        clear_cache()
        st.rerun()
    
    st.divider()
    
    # 정보
    st.info("""
    **대시보드 기능:**
    - 실시간 상위 종목 모니터링
    - 기술적 분석 결과
    - 백테스팅 성과
    - 히스토리 데이터 탐색
    """)
    
    st.divider()
    
    # 최신 업데이트 시간
    latest_date = get_latest_date(screener_type)
    if latest_date:
        st.success(f"📅 최신 데이터: {latest_date}")
    else:
        st.warning("데이터 없음")

# 메인 콘텐츠
try:
    # 최신 데이터 로드
    current_df = load_latest_data(screener_type)
    
    if current_df is None or current_df.empty:
        st.error("데이터를 불러올 수 없습니다. 먼저 main.py를 실행하여 데이터를 수집하세요.")
        st.code("python main.py", language="bash")
        st.stop()
    
    # 시장 필터 상태
    st.header("🌍 시장 상태")
    market_regime = load_market_regime()
    display_market_status(market_regime)
    
    st.divider()
    
    # 요약 통계 카드
    st.header(f"📊 {screener_name} 요약")
    display_summary_cards(current_df)
    
    st.divider()
    
    # 레이아웃: 좌측(테이블) + 우측(파이 차트)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 상위 종목 테이블
        display_top_stocks_table(current_df, screener_name)
    
    with col2:
        # 포트폴리오 구성 파이 차트
        st.subheader("📊 포트폴리오 구성")
        pie_fig = plot_pie_portfolio(current_df)
        if pie_fig:
            st.plotly_chart(pie_fig, use_container_width=True)
    
    st.divider()
    
    # 전날 대비 비교
    st.header("📈 전날 대비 변화")
    
    # 전날 데이터 로드
    available_dates = get_available_dates(screener_type)
    if len(available_dates) >= 2:
        yesterday_date = available_dates[-2]
        yesterday_df = load_data_by_date(yesterday_date, screener_type)
        
        # 신규/탈락 종목
        display_new_dropped_stocks(current_df, yesterday_df)
        
        st.write("")  # 공백
        
        # 비교 테이블
        display_comparison_table(current_df, yesterday_df, period_name="전날")
    else:
        st.info("비교할 전날 데이터가 없습니다.")
    
    st.divider()
    
    # 기술적 분석
    st.header("🔍 기술적 분석")
    
    with st.spinner("기술적 분석 로딩 중..."):
        technical_analysis = load_technical_analysis(screener_type)
        
        if technical_analysis:
            display_technical_status(technical_analysis)
            
            st.write("")  # 공백
            
            # 매매 신호
            display_signals(current_df, technical_analysis)
        else:
            st.warning("기술적 분석 데이터를 불러올 수 없습니다.")
    
    st.divider()
    
    # 백테스팅 결과
    st.header("💰 백테스팅 성과")
    
    backtest_result = load_backtest_results(screener_type)
    
    if backtest_result:
        display_backtest_metrics(backtest_result)
        
        st.write("")  # 공백
        
        # 포트폴리오 가치 차트
        col1, col2 = st.columns(2)
        
        with col1:
            portfolio_fig = plot_portfolio_value(backtest_result)
            if portfolio_fig:
                st.plotly_chart(portfolio_fig, use_container_width=True)
        
        with col2:
            # 기간별 성과 비교 (최근 데이터 사용)
            if len(available_dates) >= 7:
                from dashboard.utils.data_loader import load_historical_range
                
                start_date = available_dates[-7]
                end_date = available_dates[-1]
                historical_data = load_historical_range(start_date, end_date, screener_type)
                
                perf_fig = plot_performance_comparison(historical_data)
                if perf_fig:
                    st.plotly_chart(perf_fig, use_container_width=True)
    else:
        st.info("백테스팅 결과가 없습니다. main.py를 실행하여 백테스팅을 수행하세요.")
    
    st.divider()
    
    # 푸터
    st.markdown("---")
    st.caption(f"📅 마지막 업데이트: {latest_date if latest_date else '알 수 없음'}")
    st.caption("💡 다른 페이지에서 더 많은 분석을 확인하세요!")

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)

