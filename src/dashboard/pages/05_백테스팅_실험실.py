"""
백테스팅 실험실 - 파라미터 조정 및 실험
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from dashboard.utils.data_loader import get_available_dates
from dashboard.utils.backtest_manager import get_backtest_manager
from dashboard.components.charts import (
    plot_portfolio_value, plot_daily_returns, plot_mdd_curve,
    plot_cumulative_returns_vs_spy, plot_monthly_returns_heatmap,
    plot_rolling_sharpe
)
from dashboard.components.metrics import display_backtest_metrics
from backtester import load_historical_portfolio_data, simulate_portfolio_flexible
from telegram_notifier import send_backtest_report, send_backtest_chart

# 페이지 설정
st.set_page_config(
    page_title="백테스팅 실험실",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 백테스팅 실험실")
st.markdown("---")

# 사이드바 - 스크리너 선택
with st.sidebar:
    st.header("⚙️ 설정")
    
    screener_type = st.selectbox(
        "스크리너 타입",
        options=["large", "mega"],
        format_func=lambda x: "대형주 (Large Cap)" if x == "large" else "초대형주 (Mega Cap)",
        index=0
    )
    
    screener_name = "대형주" if screener_type == "large" else "초대형주"
    
    st.divider()
    
    st.info("""
    **백테스팅 실험실**
    
    다양한 파라미터로 백테스팅을 실행하고 결과를 비교할 수 있습니다.
    
    - 종목 수, 리밸런싱 주기 조정
    - 비중 전략 선택
    - 백테스팅 기간 설정
    - 시장 필터 ON/OFF
    """)

# 메인 콘텐츠
try:
    # 세션 스테이트 초기화
    if 'experiment_results' not in st.session_state:
        st.session_state.experiment_results = []
    
    # 사용 가능한 날짜 확인
    available_dates = get_available_dates(screener_type)
    
    if not available_dates:
        st.error("사용 가능한 데이터가 없습니다. main.py를 실행하여 데이터를 수집하세요.")
        st.stop()
    
    st.success(f"📊 사용 가능한 데이터: {len(available_dates)}일 ({available_dates[0]} ~ {available_dates[-1]})")
    
    st.divider()
    
    # 파라미터 설정 섹션
    st.header("⚙️ 백테스팅 파라미터 설정")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        num_stocks = st.selectbox(
            "포트폴리오 종목 수",
            options=[5, 10, 15],
            index=0,
            help="매일 보유할 종목 수"
        )
    
    with col2:
        rebalance_frequency = st.selectbox(
            "리밸런싱 주기",
            options=["daily", "weekly"],
            format_func=lambda x: "매일" if x == "daily" else "매주",
            index=0,
            help="포트폴리오 재조정 주기"
        )
    
    with col3:
        weight_method = st.selectbox(
            "비중 전략",
            options=["equal", "market_cap", "momentum"],
            format_func=lambda x: {
                "equal": "동일 비중",
                "market_cap": "시가총액 가중",
                "momentum": "모멘텀 가중"
            }[x],
            index=0,
            help="종목별 투자 비중 결정 방식"
        )
    
    with col4:
        enable_market_filter = st.checkbox(
            "시장 필터 활성화",
            value=True,
            help="약세장 시 현금 보유"
        )
    
    st.divider()
    
    # 백테스팅 기간 설정
    st.subheader("📅 백테스팅 기간")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        use_custom_dates = st.checkbox("기간 직접 설정", value=False)
    
    if use_custom_dates:
        with col2:
            start_date = st.selectbox(
                "시작 날짜",
                options=available_dates,
                index=max(0, len(available_dates) - 30)
            )
        
        with col3:
            end_date = st.selectbox(
                "종료 날짜",
                options=available_dates,
                index=len(available_dates) - 1
            )
        
        weeks = None
    else:
        with col2:
            weeks = st.slider(
                "백테스팅 기간 (주)",
                min_value=4,
                max_value=52,
                value=12,
                step=4,
                help="최근 N주 데이터로 백테스팅"
            )
        
        start_date = None
        end_date = None
    
    # 초기 자본
    with col1:
        initial_capital = st.number_input(
            "초기 자본 ($)",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000,
            help="백테스팅 시작 자본금"
        )
    
    st.divider()
    
    # 실험 라벨
    experiment_label = st.text_input(
        "실험 라벨 (선택사항)",
        value="",
        placeholder=f"{screener_name} - {num_stocks}종목 - {rebalance_frequency}",
        help="이 실험을 구분할 수 있는 라벨"
    )
    
    # 백테스팅 실행 버튼
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        run_backtest_btn = st.button(
            "🚀 백테스팅 실행",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        clear_results_btn = st.button(
            "🗑️ 결과 초기화",
            use_container_width=True
        )
    
    # 결과 초기화
    if clear_results_btn:
        st.session_state.experiment_results = []
        st.success("실험 결과가 초기화되었습니다.")
        st.rerun()
    
    # 백테스팅 실행
    if run_backtest_btn:
        with st.spinner("백테스팅 실행 중..."):
            try:
                # 파라미터 구성
                params = {
                    'num_stocks': num_stocks,
                    'rebalance_frequency': rebalance_frequency,
                    'weight_method': weight_method,
                    'enable_market_filter': enable_market_filter,
                    'initial_capital': initial_capital
                }
                
                if use_custom_dates:
                    params['start_date'] = start_date
                    params['end_date'] = end_date
                else:
                    params['weeks'] = weeks
                
                # 백테스트 매니저
                manager = get_backtest_manager()
                
                # 캐시 확인
                cached = manager.check_cache(params)
                if cached:
                    st.info("캐시된 결과를 사용합니다.")
                    result = cached['result']
                else:
                    # 데이터 로드
                    historical_data = load_historical_portfolio_data(screener_type)
                    
                    if not historical_data:
                        st.error("역사적 데이터를 로드할 수 없습니다.")
                        st.stop()
                    
                    # 백테스팅 실행
                    progress_bar = st.progress(0)
                    result = simulate_portfolio_flexible(historical_data, params)
                    progress_bar.progress(100)
                    
                    if not result:
                        st.error("백테스팅 실행 실패")
                        st.stop()
                    
                    # 결과 저장
                    label = experiment_label or f"{screener_name} - {num_stocks}종목 - {rebalance_frequency}"
                    manager.save_result(params, result, label)
                
                # 세션에 추가
                label = experiment_label or f"{screener_name} - {num_stocks}종목 - {rebalance_frequency}"
                st.session_state.experiment_results.append({
                    'label': label,
                    'params': params,
                    'result': result,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                st.success("✅ 백테스팅 완료!")
                
            except Exception as e:
                st.error(f"백테스팅 실행 중 오류: {e}")
                st.exception(e)
    
    st.divider()
    
    # 결과 표시
    if st.session_state.experiment_results:
        st.header("📊 실험 결과")
        
        # 탭 생성
        result_tabs = st.tabs([
            f"{i+1}. {exp['label'][:30]}" 
            for i, exp in enumerate(st.session_state.experiment_results)
        ])
        
        for idx, (tab, experiment) in enumerate(zip(result_tabs, st.session_state.experiment_results)):
            with tab:
                result = experiment['result']
                params = experiment['params']
                label = experiment['label']
                
                # 파라미터 표시
                st.subheader("⚙️ 파라미터")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("종목 수", params.get('num_stocks', '-'))
                
                with col2:
                    st.metric("리밸런싱", params.get('rebalance_frequency', '-'))
                
                with col3:
                    st.metric("비중 방식", params.get('weight_method', '-'))
                
                with col4:
                    st.metric("시장 필터", "ON" if params.get('enable_market_filter') else "OFF")
                
                st.divider()
                
                # 성과 메트릭
                display_backtest_metrics(result)
                
                st.divider()
                
                # 차트
                st.subheader("📈 성과 차트")
                
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    # 포트폴리오 가치
                    portfolio_fig = plot_portfolio_value(result)
                    if portfolio_fig:
                        st.plotly_chart(portfolio_fig, use_container_width=True)
                
                with chart_col2:
                    # 일별 수익률
                    returns_fig = plot_daily_returns(result)
                    if returns_fig:
                        st.plotly_chart(returns_fig, use_container_width=True)
                
                # 추가 차트
                with st.expander("📊 추가 차트 보기"):
                    chart_col1, chart_col2 = st.columns(2)
                    
                    with chart_col1:
                        # MDD 곡선
                        mdd_fig = plot_mdd_curve(result)
                        if mdd_fig:
                            st.plotly_chart(mdd_fig, use_container_width=True)
                    
                    with chart_col2:
                        # 롤링 샤프비율
                        sharpe_fig = plot_rolling_sharpe(result)
                        if sharpe_fig:
                            st.plotly_chart(sharpe_fig, use_container_width=True)
                    
                    # SPY 비교
                    spy_fig = plot_cumulative_returns_vs_spy(result)
                    if spy_fig:
                        st.plotly_chart(spy_fig, use_container_width=True)
                    
                    # 월별 히트맵
                    heatmap_fig = plot_monthly_returns_heatmap(result)
                    if heatmap_fig:
                        st.plotly_chart(heatmap_fig, use_container_width=True)
                
                st.divider()
                
                # 액션 버튼
                st.subheader("📤 공유 및 관리")
                
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button(f"📤 텔레그램 전송 (결과 {idx+1})", key=f"telegram_{idx}"):
                        with st.spinner("전송 중..."):
                            success = send_backtest_report(result, label)
                            if success:
                                st.success("텔레그램 전송 완료!")
                            else:
                                st.error("텔레그램 전송 실패")
                
                with action_col2:
                    if st.button(f"📊 차트 전송 (결과 {idx+1})", key=f"chart_{idx}"):
                        with st.spinner("차트 생성 및 전송 중..."):
                            portfolio_fig = plot_portfolio_value(result)
                            if portfolio_fig:
                                success = send_backtest_chart(portfolio_fig, f"{label} - 포트폴리오 가치")
                                if success:
                                    st.success("차트 전송 완료!")
                                else:
                                    st.error("차트 전송 실패")
                
                with action_col3:
                    if st.button(f"❌ 삭제 (결과 {idx+1})", key=f"delete_{idx}"):
                        st.session_state.experiment_results.pop(idx)
                        st.rerun()
        
        st.divider()
        
        # 전체 비교
        if len(st.session_state.experiment_results) > 1:
            st.header("🔬 실험 비교")
            
            from dashboard.components.strategy_comparison import (
                display_strategy_comparison_table,
                plot_strategy_comparison_returns,
                plot_strategy_metrics_comparison,
                display_best_strategy_recommendation,
                display_risk_return_scatter
            )
            
            # 비교 테이블
            display_strategy_comparison_table(st.session_state.experiment_results)
            
            st.divider()
            
            # 최적 전략 추천
            display_best_strategy_recommendation(st.session_state.experiment_results)
            
            st.divider()
            
            # 비교 차트
            st.subheader("📈 성과 비교 차트")
            
            # 누적 수익률 비교
            comp_fig = plot_strategy_comparison_returns(st.session_state.experiment_results)
            if comp_fig:
                st.plotly_chart(comp_fig, use_container_width=True)
            
            # 메트릭 비교
            metrics_fig = plot_strategy_metrics_comparison(st.session_state.experiment_results)
            if metrics_fig:
                st.plotly_chart(metrics_fig, use_container_width=True)
            
            # 리스크-수익률 산점도
            scatter_fig = display_risk_return_scatter(st.session_state.experiment_results)
            if scatter_fig:
                st.plotly_chart(scatter_fig, use_container_width=True)
            
            # 전체 비교 리포트 전송
            if st.button("📤 전체 비교 리포트 텔레그램 전송", type="primary"):
                from telegram_notifier import send_strategy_comparison_report
                
                with st.spinner("전송 중..."):
                    success = send_strategy_comparison_report(st.session_state.experiment_results)
                    if success:
                        st.success("비교 리포트 전송 완료!")
                    else:
                        st.error("리포트 전송 실패")
    
    else:
        st.info("👆 위에서 파라미터를 설정하고 백테스팅을 실행하세요.")

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)

