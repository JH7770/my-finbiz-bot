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
    plot_portfolio_value, plot_daily_returns, plot_mdd_curve
)

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
    
    # 성과 메트릭
    display_backtest_metrics(backtest_result)
    
    st.divider()
    
    # 차트 섹션
    st.header("📈 성과 차트")
    
    # 포트폴리오 가치 변화
    st.subheader("💵 포트폴리오 가치 변화")
    portfolio_fig = plot_portfolio_value(backtest_result)
    if portfolio_fig:
        st.plotly_chart(portfolio_fig, use_container_width=True)
    else:
        st.warning("포트폴리오 가치 차트를 생성할 수 없습니다.")
    
    st.write("")  # 공백
    
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
        st.subheader("📉 최대낙폭 (MDD)")
        mdd_fig = plot_mdd_curve(backtest_result)
        if mdd_fig:
            st.plotly_chart(mdd_fig, use_container_width=True)
        else:
            st.warning("MDD 차트를 생성할 수 없습니다.")
    
    st.divider()
    
    # 상세 정보
    st.header("📝 상세 정보")
    
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


