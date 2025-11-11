"""
멀티 전략 비교 컴포넌트
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def display_strategy_comparison_table(strategies):
    """
    전략 비교 테이블 표시
    
    Args:
        strategies: 전략 결과 리스트
    """
    if not strategies:
        st.warning("비교할 전략이 없습니다.")
        return
    
    # 비교 데이터 생성
    comparison_data = []
    
    for idx, strategy in enumerate(strategies):
        result = strategy['result']
        params = strategy.get('params', {})
        label = strategy.get('label', f"전략 {idx+1}")
        
        comparison_data.append({
            '전략명': label,
            '종목 수': params.get('num_stocks', '-'),
            '리밸런싱': params.get('rebalance_frequency', '-'),
            '비중 방식': params.get('weight_method', '-'),
            '총 수익률 (%)': f"{result['total_return']:.2f}",
            '연환산 수익률 (%)': f"{result['annualized_return']:.2f}",
            'MDD (%)': f"{result['mdd']:.2f}",
            '샤프비율': f"{result['sharpe_ratio']:.2f}",
            '승률 (%)': f"{result['win_rate']:.2f}"
        })
    
    df = pd.DataFrame(comparison_data)
    
    # 스타일링
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


def plot_strategy_comparison_returns(strategies):
    """
    전략별 누적 수익률 비교 차트
    
    Args:
        strategies: 전략 결과 리스트
    
    Returns:
        plotly Figure
    """
    if not strategies:
        return None
    
    try:
        fig = go.Figure()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for idx, strategy in enumerate(strategies):
            result = strategy['result']
            label = strategy.get('label', f"전략 {idx+1}")
            
            if 'daily_returns' not in result:
                continue
            
            daily_returns = result['daily_returns']
            dates = [r['date'] for r in daily_returns]
            values = [r['value'] for r in daily_returns]
            initial = result['initial_capital']
            
            # 누적 수익률 계산
            cumulative = [(v / initial - 1) * 100 for v in values]
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=cumulative,
                mode='lines',
                name=label,
                line=dict(color=colors[idx % len(colors)], width=2)
            ))
        
        fig.update_layout(
            title="전략별 누적 수익률 비교",
            xaxis_title="날짜",
            yaxis_title="누적 수익률 (%)",
            height=500,
            hovermode='x unified',
            template='plotly_white',
            legend=dict(x=0.01, y=0.99)
        )
        
        return fig
    
    except Exception as e:
        print(f"전략 비교 차트 생성 실패: {e}")
        return None


def plot_strategy_metrics_comparison(strategies):
    """
    전략별 주요 메트릭 비교 차트
    
    Args:
        strategies: 전략 결과 리스트
    
    Returns:
        plotly Figure
    """
    if not strategies:
        return None
    
    try:
        labels = [s.get('label', f"전략 {i+1}") for i, s in enumerate(strategies)]
        
        total_returns = [s['result']['total_return'] for s in strategies]
        sharpe_ratios = [s['result']['sharpe_ratio'] for s in strategies]
        mdds = [abs(s['result']['mdd']) for s in strategies]
        win_rates = [s['result']['win_rate'] for s in strategies]
        
        # 서브플롯 생성 (2x2)
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('총 수익률', '샤프비율', 'MDD (절대값)', '승률'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}]]
        )
        
        # 총 수익률
        fig.add_trace(
            go.Bar(x=labels, y=total_returns, name='총 수익률', marker_color='#1f77b4'),
            row=1, col=1
        )
        
        # 샤프비율
        fig.add_trace(
            go.Bar(x=labels, y=sharpe_ratios, name='샤프비율', marker_color='#ff7f0e'),
            row=1, col=2
        )
        
        # MDD
        fig.add_trace(
            go.Bar(x=labels, y=mdds, name='MDD', marker_color='#d62728'),
            row=2, col=1
        )
        
        # 승률
        fig.add_trace(
            go.Bar(x=labels, y=win_rates, name='승률', marker_color='#2ca02c'),
            row=2, col=2
        )
        
        fig.update_yaxes(title_text="수익률 (%)", row=1, col=1)
        fig.update_yaxes(title_text="샤프비율", row=1, col=2)
        fig.update_yaxes(title_text="MDD (%)", row=2, col=1)
        fig.update_yaxes(title_text="승률 (%)", row=2, col=2)
        
        fig.update_layout(
            height=700,
            showlegend=False,
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"메트릭 비교 차트 생성 실패: {e}")
        return None


def display_best_strategy_recommendation(strategies):
    """
    최적 전략 추천 표시
    
    Args:
        strategies: 전략 결과 리스트
    """
    if not strategies:
        return
    
    # 샤프비율 기준 최적 전략
    best_sharpe = max(strategies, key=lambda x: x['result']['sharpe_ratio'])
    
    # 총 수익률 기준 최적 전략
    best_return = max(strategies, key=lambda x: x['result']['total_return'])
    
    # 최소 MDD 전략
    best_mdd = min(strategies, key=lambda x: abs(x['result']['mdd']))
    
    st.subheader("🏆 최적 전략 추천")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.success("**샤프비율 최고**")
        st.write(f"**전략:** {best_sharpe.get('label', '전략')}")
        st.write(f"샤프비율: {best_sharpe['result']['sharpe_ratio']:.2f}")
        st.write(f"수익률: {best_sharpe['result']['total_return']:.2f}%")
        
        params = best_sharpe.get('params', {})
        st.caption(f"• 종목 수: {params.get('num_stocks', '-')}")
        st.caption(f"• 리밸런싱: {params.get('rebalance_frequency', '-')}")
        st.caption(f"• 비중: {params.get('weight_method', '-')}")
    
    with col2:
        st.info("**총 수익률 최고**")
        st.write(f"**전략:** {best_return.get('label', '전략')}")
        st.write(f"수익률: {best_return['result']['total_return']:.2f}%")
        st.write(f"샤프비율: {best_return['result']['sharpe_ratio']:.2f}")
        
        params = best_return.get('params', {})
        st.caption(f"• 종목 수: {params.get('num_stocks', '-')}")
        st.caption(f"• 리밸런싱: {params.get('rebalance_frequency', '-')}")
        st.caption(f"• 비중: {params.get('weight_method', '-')}")
    
    with col3:
        st.warning("**MDD 최소**")
        st.write(f"**전략:** {best_mdd.get('label', '전략')}")
        st.write(f"MDD: {best_mdd['result']['mdd']:.2f}%")
        st.write(f"수익률: {best_mdd['result']['total_return']:.2f}%")
        
        params = best_mdd.get('params', {})
        st.caption(f"• 종목 수: {params.get('num_stocks', '-')}")
        st.caption(f"• 리밸런싱: {params.get('rebalance_frequency', '-')}")
        st.caption(f"• 비중: {params.get('weight_method', '-')}")


def display_risk_return_scatter(strategies):
    """
    리스크-수익률 산점도
    
    Args:
        strategies: 전략 결과 리스트
    
    Returns:
        plotly Figure
    """
    if not strategies:
        return None
    
    try:
        labels = []
        returns = []
        mdds = []
        sharpe_ratios = []
        
        for idx, strategy in enumerate(strategies):
            result = strategy['result']
            label = strategy.get('label', f"전략 {idx+1}")
            
            labels.append(label)
            returns.append(result['total_return'])
            mdds.append(abs(result['mdd']))
            sharpe_ratios.append(result['sharpe_ratio'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=mdds,
            y=returns,
            mode='markers+text',
            text=labels,
            textposition='top center',
            marker=dict(
                size=[s*10 for s in sharpe_ratios],  # 샤프비율에 따라 크기 조정
                color=sharpe_ratios,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="샤프비율")
            ),
            name='전략'
        ))
        
        fig.update_layout(
            title="리스크-수익률 분석 (버블 크기 = 샤프비율)",
            xaxis_title="리스크 (MDD %)",
            yaxis_title="수익률 (%)",
            height=500,
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"리스크-수익률 산점도 생성 실패: {e}")
        return None

