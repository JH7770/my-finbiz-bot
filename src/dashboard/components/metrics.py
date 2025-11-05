"""
메트릭 및 상태 표시 컴포넌트
"""
import streamlit as st
import sys
from pathlib import Path
import plotly.graph_objects as go

# 유틸리티 임포트
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src' / 'dashboard' / 'utils'))
from formatting import format_percentage, format_currency, parse_performance, parse_price


def display_market_status(market_regime):
    """
    시장 필터 상태 표시
    
    Args:
        market_regime: 시장 상태 정보 딕셔너리
    """
    if not market_regime:
        st.info("시장 상태 정보를 불러올 수 없습니다. main.py를 실행하여 시장 데이터를 수집하세요.")
        return
    
    hold_cash = market_regime.get('hold_cash', False)
    
    # 큰 경고 배너
    if hold_cash:
        st.error("⚠️ **약세장 감지 - 매수 금지**")
        st.markdown(f"**사유:** {market_regime.get('reason', 'N/A')}")
    else:
        st.success("✅ **정상 시장 - 매수 가능**")
        st.markdown(f"**상태:** {market_regime.get('reason', 'N/A')}")
    
    # 메트릭 4개
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        spy_price = market_regime.get('spy_price', 0)
        st.metric(
            label="SPY 가격",
            value=format_currency(spy_price),
            delta=None
        )
    
    with col2:
        spy_ma200 = market_regime.get('spy_ma200', 0)
        above_ma200 = spy_price > spy_ma200
        delta_ma200 = spy_price - spy_ma200
        st.metric(
            label="MA200",
            value=format_currency(spy_ma200),
            delta=f"{delta_ma200:+.2f}" if above_ma200 else f"{delta_ma200:.2f}",
            delta_color="normal" if above_ma200 else "inverse"
        )
    
    with col3:
        spy_ma120 = market_regime.get('spy_ma120', 0)
        above_ma120 = spy_price > spy_ma120
        delta_ma120 = spy_price - spy_ma120
        st.metric(
            label="MA120",
            value=format_currency(spy_ma120),
            delta=f"{delta_ma120:+.2f}" if above_ma120 else f"{delta_ma120:.2f}",
            delta_color="normal" if above_ma120 else "inverse"
        )
    
    with col4:
        vix = market_regime.get('vix', 0)
        vix_threshold = market_regime.get('vix_threshold', 20)
        vix_high = vix > vix_threshold
        st.metric(
            label=f"VIX (임계값: {vix_threshold})",
            value=f"{vix:.2f}",
            delta="과열" if vix_high else "안정",
            delta_color="inverse" if vix_high else "normal"
        )
    
    # SPY vs MA 차트
    with st.expander("📊 SPY vs 이동평균선 차트"):
        fig = go.Figure()
        
        # 간단한 비교 바 차트
        categories = ['SPY', 'MA200', 'MA120']
        values = [spy_price, spy_ma200, spy_ma120]
        colors = ['blue', 'green' if above_ma200 else 'red', 'orange' if above_ma120 else 'red']
        
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f"${v:.2f}" for v in values],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="SPY vs 이동평균선",
            yaxis_title="가격 ($)",
            xaxis_title="",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 업데이트 시간
    timestamp = market_regime.get('timestamp', 'N/A')
    st.caption(f"📅 마지막 업데이트: {timestamp}")


def display_summary_cards(df):
    """
    요약 통계 카드 표시
    
    Args:
        df: DataFrame
    """
    if df is None or df.empty:
        st.warning("데이터가 없습니다.")
        return
    
    top5 = df.head(5)
    
    # 수익률 계산
    perfs = [parse_performance(p) for p in top5['Perf Quart']]
    prices = [parse_price(p) for p in top5['Price']]
    changes = [parse_performance(c) for c in top5['Change']]
    
    avg_perf = sum(perfs) / len(perfs) if perfs else 0
    max_perf = max(perfs) if perfs else 0
    min_perf = min(perfs) if perfs else 0
    avg_price = sum(prices) / len(prices) if prices else 0
    
    # 최대 상승/하락 종목
    max_change_idx = changes.index(max(changes)) if changes else 0
    min_change_idx = changes.index(min(changes)) if changes else 0
    
    biggest_gainer = top5.iloc[max_change_idx]['Ticker'] if len(top5) > 0 else '-'
    biggest_gainer_change = changes[max_change_idx] if changes else 0
    
    biggest_loser = top5.iloc[min_change_idx]['Ticker'] if len(top5) > 0 else '-'
    biggest_loser_change = changes[min_change_idx] if changes else 0
    
    # 4개 컬럼으로 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="평균 수익률 (3개월)",
            value=format_percentage(avg_perf),
            delta=None
        )
    
    with col2:
        st.metric(
            label="최고 수익률",
            value=format_percentage(max_perf),
            delta=None
        )
    
    with col3:
        st.metric(
            label="평균 주가",
            value=format_currency(avg_price),
            delta=None
        )
    
    with col4:
        st.metric(
            label="최대 상승 종목",
            value=biggest_gainer,
            delta=format_percentage(biggest_gainer_change)
        )


def display_technical_status(technical_analysis):
    """
    기술적 지표 상태 표시
    
    Args:
        technical_analysis: 기술적 분석 결과 딕셔너리
    """
    if not technical_analysis:
        st.warning("기술적 분석 데이터가 없습니다.")
        return
    
    # 조건 만족 종목 수 계산
    all_conditions_count = sum(
        1 for v in technical_analysis.values() 
        if v.get('all_conditions_met', False)
    )
    
    partial_conditions_count = sum(
        1 for v in technical_analysis.values()
        if v.get('status') == 'success' and not v.get('all_conditions_met', False)
        and (v.get('above_ma60', False) or v.get('above_ma120', False))
    )
    
    error_count = sum(
        1 for v in technical_analysis.values()
        if v.get('status') != 'success'
    )
    
    st.subheader("📊 기술적 분석 요약")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="✅ 모든 조건 만족",
            value=f"{all_conditions_count}개",
            help="현재가 > 60일선 > 120일선"
        )
    
    with col2:
        st.metric(
            label="⚠️ 부분 만족",
            value=f"{partial_conditions_count}개",
            help="일부 조건만 만족"
        )
    
    with col3:
        st.metric(
            label="❌ 데이터 없음",
            value=f"{error_count}개",
            help="분석 데이터 부족"
        )
    
    # 상세 테이블
    with st.expander("상세 정보 보기"):
        data = []
        for ticker, status in technical_analysis.items():
            if status['status'] == 'success':
                icon = '✅' if status['all_conditions_met'] else ('⚠️' if status.get('above_ma60') or status.get('above_ma120') else '❌')
                data.append({
                    '종목': ticker,
                    '상태': icon,
                    '현재가': format_currency(status['price']),
                    'MA60': format_currency(status['ma60']),
                    'MA120': format_currency(status['ma120']),
                    '60일선 위': '✅' if status['above_ma60'] else '❌',
                    '120일선 위': '✅' if status['above_ma120'] else '❌'
                })
            else:
                data.append({
                    '종목': ticker,
                    '상태': '❓',
                    '현재가': '-',
                    'MA60': '-',
                    'MA120': '-',
                    '60일선 위': '-',
                    '120일선 위': '-'
                })
        
        import pandas as pd
        df = pd.DataFrame(data)
        df = df.reset_index(drop=True)  # PyArrow 에러 방지
        st.dataframe(df, use_container_width=True, hide_index=True)


def display_signals(df, technical_analysis):
    """
    매수/매도 신호 표시
    
    Args:
        df: 현재 DataFrame
        technical_analysis: 기술적 분석 결과
    """
    if df is None or df.empty:
        st.warning("데이터가 없습니다.")
        return
    
    st.subheader("🎯 매매 신호")
    
    top5 = df.head(5)
    
    buy_signals = []
    hold_signals = []
    sell_signals = []
    watch_signals = []
    
    for idx, row in top5.iterrows():
        ticker = row['Ticker']
        price = parse_price(row['Price'])
        perf = parse_performance(row['Perf Quart'])
        
        # 기술적 분석 결과 확인
        tech = technical_analysis.get(ticker, {}) if technical_analysis else {}
        all_conditions = tech.get('all_conditions_met', False)
        
        signal_info = {
            '종목': ticker,
            '현재가': format_currency(price),
            '3개월 수익률': format_percentage(perf)
        }
        
        if all_conditions:
            # 기술적 조건 만족 - 보유 또는 매수
            # (실제로는 신고가 돌파 여부를 체크해야 함)
            hold_signals.append({**signal_info, '신호': '🟢 보유'})
        elif tech.get('status') == 'success':
            # 데이터는 있지만 조건 미달 - 관망
            watch_signals.append({**signal_info, '신호': '🟡 관망'})
        else:
            # 데이터 없음
            watch_signals.append({**signal_info, '신호': '❓ 데이터 부족'})
    
    # 신호별로 표시
    if buy_signals:
        st.success("🟢 매수 신호")
        import pandas as pd
        df = pd.DataFrame(buy_signals).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    if hold_signals:
        st.info("🟢 보유 추천")
        import pandas as pd
        df = pd.DataFrame(hold_signals).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    if sell_signals:
        st.error("🔴 매도 신호")
        import pandas as pd
        df = pd.DataFrame(sell_signals).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    if watch_signals:
        st.warning("🟡 관망")
        import pandas as pd
        df = pd.DataFrame(watch_signals).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)


def display_backtest_metrics(backtest_result):
    """
    백테스팅 성과 메트릭 표시
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    """
    if not backtest_result:
        st.warning("백테스팅 결과가 없습니다.")
        return
    
    st.subheader("💰 백테스팅 성과")
    
    # 주요 메트릭 4개
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_return = backtest_result.get('total_return', 0)
        st.metric(
            label="총 수익률",
            value=format_percentage(total_return),
            delta=None
        )
    
    with col2:
        annualized_return = backtest_result.get('annualized_return', 0)
        st.metric(
            label="연환산 수익률",
            value=format_percentage(annualized_return),
            delta=None
        )
    
    with col3:
        mdd = backtest_result.get('mdd', 0)
        st.metric(
            label="최대낙폭 (MDD)",
            value=format_percentage(mdd),
            delta=None,
            delta_color="inverse"
        )
    
    with col4:
        sharpe_ratio = backtest_result.get('sharpe_ratio', 0)
        st.metric(
            label="샤프비율",
            value=f"{sharpe_ratio:.2f}",
            delta=None
        )
    
    # 추가 메트릭
    st.divider()
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        win_rate = backtest_result.get('win_rate', 0)
        st.metric(
            label="승률",
            value=format_percentage(win_rate),
            delta=None
        )
    
    with col6:
        num_rebalances = backtest_result.get('num_rebalances', 0)
        st.metric(
            label="거래일수",
            value=f"{num_rebalances}일",
            delta=None
        )
    
    with col7:
        initial_capital = backtest_result.get('initial_capital', 0)
        st.metric(
            label="초기 자본",
            value=format_currency(initial_capital),
            delta=None
        )
    
    with col8:
        final_value = backtest_result.get('final_value', 0)
        st.metric(
            label="최종 가치",
            value=format_currency(final_value),
            delta=None
        )
    
    # 시장 필터 정보 (있는 경우)
    cash_holding_days = backtest_result.get('cash_holding_days', 0)
    if cash_holding_days > 0:
        st.divider()
        st.info(f"🏦 **시장 필터 적용**: 약세장으로 {cash_holding_days}일 동안 현금 보유 ({format_percentage(backtest_result.get('cash_holding_ratio', 0))})")
    
    
    # 최고/최악의 날
    st.divider()
    
    col9, col10 = st.columns(2)
    
    with col9:
        best_day = backtest_result.get('best_day', {})
        st.success(f"📈 최고 수익일: {best_day.get('date', '-')}")
        st.write(f"수익률: {format_percentage(best_day.get('return', 0))}")
    
    with col10:
        worst_day = backtest_result.get('worst_day', {})
        st.error(f"📉 최악 수익일: {worst_day.get('date', '-')}")
        st.write(f"수익률: {format_percentage(worst_day.get('return', 0))}")

