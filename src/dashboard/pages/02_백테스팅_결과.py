"""
백테스팅 결과 페이지
"""
import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from dashboard.utils.data_loader import load_backtest_results
from dashboard.components.metrics import display_backtest_metrics
from dashboard.components.charts import (
    plot_portfolio_value, plot_daily_returns, plot_mdd_curve,
    plot_cumulative_returns_vs_spy, plot_monthly_returns_heatmap,
    plot_yearly_returns_bar, plot_rolling_sharpe, plot_drawdown_histogram,
    plot_win_loss_distribution, plot_trade_frequency
)
from telegram_notifier import send_backtest_report, send_backtest_chart

# 페이지 설정
st.set_page_config(
    page_title="백테스팅 결과",
    page_icon="💰",
    layout="wide"
)

st.title("💰 백테스팅 결과")
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
    
    st.info("""
    **백테스팅 전략:**
    - 매일 상위 5개 종목으로 리밸런싱
    - 각 종목 동일 비중 (10%)
    - 실제 역사적 가격 데이터 사용
    """)

# 메인 콘텐츠
try:
    st.header(f"📊 {screener_name} 백테스팅 성과")
    
    # 백테스팅 결과 로드
    backtest_result = load_backtest_results(screener_type)
    
    if backtest_result is None:
        st.error("백테스팅 결과를 불러올 수 없습니다.")
        st.info("main.py를 실행하여 백테스팅을 수행하세요.")
        st.code("python main.py", language="bash")
        st.stop()
    
    # 탭 생성
    tab1, tab2 = st.tabs(["📊 단일 전략 상세", "📈 고급 분석"])
    
    # 탭 1: 단일 전략 상세
    with tab1:
        # 성과 메트릭
        display_backtest_metrics(backtest_result)
        
        st.divider()
        
        # 텔레그램 전송 버튼
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 텔레그램으로 결과 전송", use_container_width=True):
                with st.spinner("전송 중..."):
                    success = send_backtest_report(backtest_result, f"{screener_name} 백테스팅")
                    if success:
                        st.success("✅ 텔레그램 전송 완료!")
                    else:
                        st.error("❌ 텔레그램 전송 실패")
        
        with col2:
            if st.button("📊 차트를 텔레그램으로 전송", use_container_width=True):
                with st.spinner("차트 생성 및 전송 중..."):
                    portfolio_fig = plot_portfolio_value(backtest_result)
                    if portfolio_fig:
                        success = send_backtest_chart(portfolio_fig, f"{screener_name} - 포트폴리오 가치")
                        if success:
                            st.success("✅ 차트 전송 완료!")
                        else:
                            st.error("❌ 차트 전송 실패")
        
        st.divider()
        
        # 차트 섹션
        st.subheader("📈 주요 성과 차트")
        
        # 포트폴리오 가치 변화
        portfolio_fig = plot_portfolio_value(backtest_result)
        if portfolio_fig:
            st.plotly_chart(portfolio_fig, use_container_width=True)
        else:
            st.warning("포트폴리오 가치 차트를 생성할 수 없습니다.")
        
        # 레이아웃: 일별 수익률 + MDD
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 일별 수익률")
            returns_fig = plot_daily_returns(backtest_result)
            if returns_fig:
                st.plotly_chart(returns_fig, use_container_width=True)
            else:
                st.warning("일별 수익률 차트를 생성할 수 없습니다.")
        
        with col2:
            st.subheader("📉 드로다운 곡선")
            mdd_fig = plot_mdd_curve(backtest_result)
            if mdd_fig:
                st.plotly_chart(mdd_fig, use_container_width=True)
            else:
                st.warning("MDD 차트를 생성할 수 없습니다.")
        
        st.divider()
        
        # 상세 정보
        st.subheader("📝 상세 정보")
        
        with st.expander("백테스팅 파라미터 및 결과 보기"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**백테스팅 기간**")
                st.write(f"- 시작일: {backtest_result.get('start_date', '-')}")
                st.write(f"- 종료일: {backtest_result.get('end_date', '-')}")
                st.write(f"- 거래일수: {backtest_result.get('num_rebalances', 0)}일")
                
                st.write("")
                st.write("**자본 정보**")
                st.write(f"- 초기 자본: ${backtest_result.get('initial_capital', 0):,.2f}")
                st.write(f"- 최종 가치: ${backtest_result.get('final_value', 0):,.2f}")
                st.write(f"- 손익: ${backtest_result.get('final_value', 0) - backtest_result.get('initial_capital', 0):,.2f}")
            
            with col2:
                st.write("**성과 지표**")
                st.write(f"- 총 수익률: {backtest_result.get('total_return', 0):.2f}%")
                st.write(f"- 연환산 수익률: {backtest_result.get('annualized_return', 0):.2f}%")
                st.write(f"- 최대낙폭 (MDD): {backtest_result.get('mdd', 0):.2f}%")
                
                st.write("")
                st.write("**리스크 지표**")
                st.write(f"- 샤프비율: {backtest_result.get('sharpe_ratio', 0):.2f}")
                st.write(f"- 승률: {backtest_result.get('win_rate', 0):.2f}%")
    
    # 탭 2: 고급 분석
    with tab2:
        st.subheader("📈 고급 성과 분석")
        
        # SPY 비교
        st.write("**누적 수익률 vs SPY**")
        spy_fig = plot_cumulative_returns_vs_spy(backtest_result)
        if spy_fig:
            st.plotly_chart(spy_fig, use_container_width=True)
        else:
            st.info("누적 수익률 차트를 생성할 수 없습니다.")
        
        st.divider()
        
        # 기간별 수익률 분석
        st.subheader("📅 기간별 수익률 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 월별 히트맵
            heatmap_fig = plot_monthly_returns_heatmap(backtest_result)
            if heatmap_fig:
                st.plotly_chart(heatmap_fig, use_container_width=True)
        
        with col2:
            # 연도별 수익률
            yearly_fig = plot_yearly_returns_bar(backtest_result)
            if yearly_fig:
                st.plotly_chart(yearly_fig, use_container_width=True)
        
        st.divider()
        
        # 리스크 분석
        st.subheader("⚠️ 리스크 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 롤링 샤프비율
            sharpe_fig = plot_rolling_sharpe(backtest_result)
            if sharpe_fig:
                st.plotly_chart(sharpe_fig, use_container_width=True)
        
        with col2:
            # 드로다운 분포
            dd_hist_fig = plot_drawdown_histogram(backtest_result)
            if dd_hist_fig:
                st.plotly_chart(dd_hist_fig, use_container_width=True)
        
        st.divider()
        
        # 거래 분석
        st.subheader("📊 거래 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 승패 분포
            win_loss_fig = plot_win_loss_distribution(backtest_result)
            if win_loss_fig:
                st.plotly_chart(win_loss_fig, use_container_width=True)
        
        with col2:
            # 거래 빈도
            freq_fig = plot_trade_frequency(backtest_result)
            if freq_fig:
                st.plotly_chart(freq_fig, use_container_width=True)
    
    st.divider()
    
    # 주의사항
    st.warning("""
    ⚠️ **주의사항:**
    - 백테스팅 결과는 과거 데이터를 기반으로 하며, 미래 성과를 보장하지 않습니다.
    - 실제 거래 시 거래 수수료, 슬리피지 등이 추가로 발생할 수 있습니다.
    - 투자 결정은 신중하게 하시기 바랍니다.
    """)

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)


