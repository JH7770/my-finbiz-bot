"""
차트 생성 함수들
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# yfinance 임포트
import yfinance as yf

# 유틸리티 임포트
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src' / 'dashboard' / 'utils'))
from formatting import parse_performance, parse_price


def plot_candlestick_with_ma(ticker, period="3mo"):
    """
    캔들스틱 차트 + 이동평균선
    
    Args:
        ticker: 종목 티커
        period: 기간 (3mo, 6mo, 1y 등)
    
    Returns:
        plotly Figure
    """
    try:
        # yfinance로 데이터 가져오기
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            return None
        
        # 이동평균 계산
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        hist['MA120'] = hist['Close'].rolling(window=120).mean()
        
        # 캔들스틱 차트 생성
        fig = go.Figure()
        
        # 캔들스틱
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name='주가',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ))
        
        # MA20
        fig.add_trace(go.Scatter(
            x=hist.index,
            y=hist['MA20'],
            name='MA20',
            line=dict(color='orange', width=1)
        ))
        
        # MA60
        fig.add_trace(go.Scatter(
            x=hist.index,
            y=hist['MA60'],
            name='MA60',
            line=dict(color='blue', width=1)
        ))
        
        # MA120
        fig.add_trace(go.Scatter(
            x=hist.index,
            y=hist['MA120'],
            name='MA120',
            line=dict(color='purple', width=1)
        ))
        
        # 레이아웃 설정
        fig.update_layout(
            title=f"{ticker} 주가 차트 (이동평균선 포함)",
            xaxis_title="날짜",
            yaxis_title="가격 ($)",
            xaxis_rangeslider_visible=False,
            height=600,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"차트 생성 실패: {e}")
        return None


def plot_portfolio_value(backtest_result):
    """
    포트폴리오 가치 변화 그래프
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not backtest_result:
        return None
    
    try:
        # 포트폴리오 가치 변화 데이터 생성
        # 실제 백테스팅 결과에서 일별 데이터를 추출해야 함
        # 여기서는 간단히 시작-종료 값으로 선 그래프 생성
        
        start_date = backtest_result.get('start_date', '')
        end_date = backtest_result.get('end_date', '')
        initial_capital = backtest_result.get('initial_capital', 10000)
        final_value = backtest_result.get('final_value', 10000)
        
        # 간단한 선형 그래프 (실제로는 일별 데이터가 있어야 함)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 선형 증가 시뮬레이션 (실제 데이터가 있으면 교체)
        values = np.linspace(initial_capital, final_value, len(dates))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode='lines',
            name='포트폴리오 가치',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        
        # 초기 자본 기준선
        fig.add_hline(
            y=initial_capital,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"초기 자본 ${initial_capital:,.0f}"
        )
        
        fig.update_layout(
            title="포트폴리오 가치 변화",
            xaxis_title="날짜",
            yaxis_title="가치 ($)",
            height=500,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"포트폴리오 가치 차트 생성 실패: {e}")
        return None


def plot_daily_returns(backtest_result):
    """
    일별 수익률 바 차트
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not backtest_result:
        return None
    
    try:
        # best_day와 worst_day에서 간단한 예시 데이터 생성
        best_day = backtest_result.get('best_day', {})
        worst_day = backtest_result.get('worst_day', {})
        
        # 실제로는 일별 수익률 데이터가 있어야 함
        # 여기서는 간단히 몇 개의 샘플 데이터로 표시
        dates = [best_day.get('date', '2025-01-01'), worst_day.get('date', '2025-01-02')]
        returns = [best_day.get('return', 0), worst_day.get('return', 0)]
        
        colors = ['green' if r > 0 else 'red' for r in returns]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=dates,
            y=returns,
            marker_color=colors,
            text=[f"{r:.2f}%" for r in returns],
            textposition='outside',
            name='일별 수익률'
        ))
        
        fig.update_layout(
            title="일별 수익률",
            xaxis_title="날짜",
            yaxis_title="수익률 (%)",
            height=400,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    
    except Exception as e:
        print(f"일별 수익률 차트 생성 실패: {e}")
        return None


def plot_rank_changes_heatmap(historical_data):
    """
    순위 변화 히트맵
    
    Args:
        historical_data: {날짜: DataFrame} 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not historical_data:
        return None
    
    try:
        # 날짜별 상위 5개 종목의 순위 추출
        dates = sorted(historical_data.keys())
        all_tickers = set()
        
        # 모든 종목 수집
        for date, df in historical_data.items():
            top5 = df.head(5)
            all_tickers.update(top5['Ticker'].tolist())
        
        # 종목별 날짜별 순위 매트릭스 생성
        rank_matrix = []
        ticker_list = sorted(all_tickers)
        
        for ticker in ticker_list:
            ranks = []
            for date in dates:
                df = historical_data[date]
                top5 = df.head(5)
                
                if ticker in top5['Ticker'].values:
                    rank = top5[top5['Ticker'] == ticker].index[0] + 1
                    ranks.append(rank)
                else:
                    ranks.append(None)  # 순위 밖
            
            rank_matrix.append(ranks)
        
        # 히트맵 생성
        fig = go.Figure(data=go.Heatmap(
            z=rank_matrix,
            x=dates,
            y=ticker_list,
            colorscale='RdYlGn_r',  # 빨강(1위) -> 노랑 -> 초록(5위)
            text=rank_matrix,
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="순위")
        ))
        
        fig.update_layout(
            title="종목별 순위 변화 히트맵",
            xaxis_title="날짜",
            yaxis_title="종목",
            height=max(400, len(ticker_list) * 30),
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"히트맵 생성 실패: {e}")
        return None


def plot_pie_portfolio(df):
    """
    포트폴리오 비중 파이 차트
    
    Args:
        df: 현재 DataFrame
    
    Returns:
        plotly Figure
    """
    if df is None or df.empty:
        return None
    
    try:
        top5 = df.head(5)
        
        # 동일 비중 (각 10%)
        tickers = top5['Ticker'].tolist()
        values = [10] * len(tickers)  # 10%씩
        
        fig = go.Figure(data=[go.Pie(
            labels=tickers,
            values=values,
            hole=0.3,
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title="포트폴리오 구성 (동일 비중)",
            height=500,
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"파이 차트 생성 실패: {e}")
        return None


def plot_mdd_curve(backtest_result):
    """
    MDD (최대낙폭) 곡선 그래프
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not backtest_result:
        return None
    
    try:
        # 실제로는 일별 MDD 데이터가 있어야 함
        # 여기서는 간단히 최종 MDD 값만 표시
        mdd = backtest_result.get('mdd', 0)
        
        fig = go.Figure()
        
        # 간단한 MDD 표시 (실제 데이터가 있으면 곡선으로)
        fig.add_trace(go.Scatter(
            x=[0, 1],
            y=[0, mdd],
            mode='lines+markers',
            name='MDD',
            line=dict(color='red', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.1)'
        ))
        
        fig.update_layout(
            title=f"최대낙폭 (MDD): {mdd:.2f}%",
            xaxis_title="기간",
            yaxis_title="낙폭 (%)",
            height=400,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    
    except Exception as e:
        print(f"MDD 차트 생성 실패: {e}")
        return None


def plot_performance_comparison(historical_data):
    """
    기간별 성과 비교 차트
    
    Args:
        historical_data: {날짜: DataFrame} 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not historical_data:
        return None
    
    try:
        dates = sorted(historical_data.keys())
        avg_performances = []
        
        for date in dates:
            df = historical_data[date]
            top5 = df.head(5)
            
            # 평균 수익률 계산
            perfs = [parse_performance(p) for p in top5['Perf Quart']]
            avg_perf = sum(perfs) / len(perfs) if perfs else 0
            avg_performances.append(avg_perf)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=avg_performances,
            mode='lines+markers',
            name='평균 수익률',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title="상위 5개 종목 평균 수익률 추이",
            xaxis_title="날짜",
            yaxis_title="평균 수익률 (%)",
            height=400,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"성과 비교 차트 생성 실패: {e}")
        return None


