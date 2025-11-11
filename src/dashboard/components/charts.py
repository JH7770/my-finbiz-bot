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
    포트폴리오 가치 변화 그래프 (개선됨 - 실제 데이터 사용)
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not backtest_result:
        return None
    
    try:
        initial_capital = backtest_result.get('initial_capital', 10000)
        
        # 실제 일별 데이터가 있으면 사용
        if 'daily_returns' in backtest_result and backtest_result['daily_returns']:
            daily_returns = backtest_result['daily_returns']
            dates = [r['date'] for r in daily_returns]
            values = [r['value'] for r in daily_returns]
        elif 'portfolio_history' in backtest_result and backtest_result['portfolio_history']:
            # portfolio_history만 있는 경우
            portfolio_history = backtest_result['portfolio_history']
            start_date = backtest_result.get('start_date', '')
            end_date = backtest_result.get('end_date', '')
            dates = pd.date_range(start=start_date, end=end_date, periods=len(portfolio_history))
            values = portfolio_history
        else:
            # 폴백: 선형 시뮬레이션
            start_date = backtest_result.get('start_date', '')
            end_date = backtest_result.get('end_date', '')
            final_value = backtest_result.get('final_value', 10000)
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
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
    일별 수익률 바 차트 (개선됨 - 전체 데이터 표시)
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not backtest_result:
        return None
    
    try:
        # 실제 일별 수익률 데이터 사용
        if 'daily_returns' in backtest_result and backtest_result['daily_returns']:
            daily_returns = backtest_result['daily_returns']
            dates = [r['date'] for r in daily_returns]
            returns = [r['return'] for r in daily_returns]
        else:
            # 폴백: best_day와 worst_day만 표시
            best_day = backtest_result.get('best_day', {})
            worst_day = backtest_result.get('worst_day', {})
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
            name='일별 수익률',
            showlegend=False
        ))
        
        # 0선 추가
        fig.add_hline(
            y=0,
            line_dash="solid",
            line_color="gray",
            line_width=1
        )
        
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
    MDD (최대낙폭) 곡선 그래프 (개선됨 - 실제 시계열 표시)
    
    Args:
        backtest_result: 백테스팅 결과 딕셔너리
    
    Returns:
        plotly Figure
    """
    if not backtest_result:
        return None
    
    try:
        # 실제 포트폴리오 히스토리로 MDD 곡선 계산
        if 'daily_returns' in backtest_result and backtest_result['daily_returns']:
            daily_returns = backtest_result['daily_returns']
            dates = [r['date'] for r in daily_returns]
            values = [r['value'] for r in daily_returns]
            
            # MDD 곡선 계산
            drawdowns = []
            peak = values[0]
            
            for value in values:
                if value > peak:
                    peak = value
                drawdown = ((value - peak) / peak) * 100
                drawdowns.append(drawdown)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=drawdowns,
                mode='lines',
                name='드로다운',
                line=dict(color='red', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.1)'
            ))
            
            mdd = min(drawdowns)
            
        elif 'portfolio_history' in backtest_result and backtest_result['portfolio_history']:
            portfolio_history = backtest_result['portfolio_history']
            start_date = backtest_result.get('start_date', '')
            end_date = backtest_result.get('end_date', '')
            dates = pd.date_range(start=start_date, end=end_date, periods=len(portfolio_history))
            
            # MDD 곡선 계산
            drawdowns = []
            peak = portfolio_history[0]
            
            for value in portfolio_history:
                if value > peak:
                    peak = value
                drawdown = ((value - peak) / peak) * 100
                drawdowns.append(drawdown)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=drawdowns,
                mode='lines',
                name='드로다운',
                line=dict(color='red', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.1)'
            ))
            
            mdd = min(drawdowns)
            
        else:
            # 폴백: 최종 MDD 값만 표시
            mdd = backtest_result.get('mdd', 0)
            
            fig = go.Figure()
            
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
            title=f"드로다운 곡선 (최대낙폭: {mdd:.2f}%)",
            xaxis_title="날짜",
            yaxis_title="드로다운 (%)",
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


# ===== 고급 차트 함수들 (신규) =====

def plot_cumulative_returns_vs_spy(backtest_result):
    """
    전략 vs SPY 누적 수익률 비교
    
    Args:
        backtest_result: 백테스팅 결과 (portfolio_history, daily_returns 포함)
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'daily_returns' not in backtest_result:
        return None
    
    try:
        import yfinance as yf
        
        daily_returns = backtest_result['daily_returns']
        if not daily_returns:
            return None
        
        # 전략의 누적 수익률 계산
        dates = [r['date'] for r in daily_returns]
        values = [r['value'] for r in daily_returns]
        initial = backtest_result['initial_capital']
        cumulative_returns = [(v / initial - 1) * 100 for v in values]
        
        # SPY 데이터 가져오기
        try:
            start_date = backtest_result['start_date']
            end_date = backtest_result['end_date']
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(start=start_date, end=end_date)
            
            if not spy_hist.empty:
                spy_initial = spy_hist['Close'].iloc[0]
                spy_cumulative = [(p / spy_initial - 1) * 100 for p in spy_hist['Close']]
                
                fig = go.Figure()
                
                # 전략
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=cumulative_returns,
                    mode='lines',
                    name='전략',
                    line=dict(color='#1f77b4', width=2)
                ))
                
                # SPY
                fig.add_trace(go.Scatter(
                    x=spy_hist.index,
                    y=spy_cumulative,
                    mode='lines',
                    name='SPY (S&P 500)',
                    line=dict(color='#ff7f0e', width=2, dash='dash')
                ))
                
                fig.update_layout(
                    title="누적 수익률 비교: 전략 vs SPY",
                    xaxis_title="날짜",
                    yaxis_title="누적 수익률 (%)",
                    height=500,
                    hovermode='x unified',
                    template='plotly_white',
                    legend=dict(x=0.01, y=0.99)
                )
                
                return fig
        except:
            pass
        
        # SPY 데이터가 없으면 전략만 표시
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_returns,
            mode='lines',
            name='전략',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        
        fig.update_layout(
            title="누적 수익률",
            xaxis_title="날짜",
            yaxis_title="누적 수익률 (%)",
            height=500,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"누적 수익률 차트 생성 실패: {e}")
        return None


def plot_monthly_returns_heatmap(backtest_result):
    """
    월별 수익률 히트맵 (연도 x 월)
    
    Args:
        backtest_result: 백테스팅 결과
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'daily_returns' not in backtest_result:
        return None
    
    try:
        daily_returns = backtest_result['daily_returns']
        if not daily_returns:
            return None
        
        # 월별 수익률 계산
        monthly_data = {}
        for r in daily_returns:
            date = datetime.strptime(r['date'], '%Y-%m-%d')
            year_month = f"{date.year}-{date.month:02d}"
            
            if year_month not in monthly_data:
                monthly_data[year_month] = []
            monthly_data[year_month].append(r['return'])
        
        # 월별 합산
        monthly_returns = {k: sum(v) for k, v in monthly_data.items()}
        
        if not monthly_returns:
            return None
        
        # 연도와 월로 분리
        years = set()
        months = set()
        for ym in monthly_returns.keys():
            year, month = ym.split('-')
            years.add(int(year))
            months.add(int(month))
        
        years = sorted(years)
        months = sorted(months)
        
        # 히트맵 데이터 생성
        z_data = []
        for month in months:
            row = []
            for year in years:
                key = f"{year}-{month:02d}"
                row.append(monthly_returns.get(key, None))
            z_data.append(row)
        
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=[str(y) for y in years],
            y=[f"{m}월" for m in months],
            colorscale='RdYlGn',
            text=[[f"{v:.1f}%" if v is not None else "-" for v in row] for row in z_data],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="수익률 (%)")
        ))
        
        fig.update_layout(
            title="월별 수익률 히트맵",
            xaxis_title="연도",
            yaxis_title="월",
            height=400,
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"월별 히트맵 생성 실패: {e}")
        return None


def plot_yearly_returns_bar(backtest_result):
    """
    연도별 수익률 막대 그래프
    
    Args:
        backtest_result: 백테스팅 결과
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'daily_returns' not in backtest_result:
        return None
    
    try:
        daily_returns = backtest_result['daily_returns']
        if not daily_returns:
            return None
        
        # 연도별 수익률 계산
        yearly_data = {}
        for r in daily_returns:
            date = datetime.strptime(r['date'], '%Y-%m-%d')
            year = date.year
            
            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(r['return'])
        
        # 연도별 합산
        yearly_returns = {k: sum(v) for k, v in yearly_data.items()}
        
        if not yearly_returns:
            return None
        
        years = sorted(yearly_returns.keys())
        returns = [yearly_returns[y] for y in years]
        colors = ['green' if r > 0 else 'red' for r in returns]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[str(y) for y in years],
            y=returns,
            marker_color=colors,
            text=[f"{r:.1f}%" for r in returns],
            textposition='outside',
            name='연간 수익률'
        ))
        
        fig.update_layout(
            title="연도별 수익률",
            xaxis_title="연도",
            yaxis_title="수익률 (%)",
            height=400,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    
    except Exception as e:
        print(f"연도별 수익률 차트 생성 실패: {e}")
        return None


def plot_rolling_sharpe(backtest_result, window=60):
    """
    롤링 샤프비율 (N일 윈도우)
    
    Args:
        backtest_result: 백테스팅 결과
        window: 윈도우 크기 (기본 60일)
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'daily_returns' not in backtest_result:
        return None
    
    try:
        daily_returns = backtest_result['daily_returns']
        if len(daily_returns) < window:
            return None
        
        dates = []
        rolling_sharpes = []
        
        for i in range(window, len(daily_returns)):
            window_data = daily_returns[i-window:i]
            returns = [r['return'] for r in window_data]
            
            # 샤프비율 계산
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5
            
            if std_dev > 0:
                sharpe = (avg_return / std_dev) * (252 ** 0.5)
            else:
                sharpe = 0
            
            dates.append(daily_returns[i]['date'])
            rolling_sharpes.append(sharpe)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=rolling_sharpes,
            mode='lines',
            name=f'{window}일 롤링 샤프비율',
            line=dict(color='#2ca02c', width=2)
        ))
        
        # 기준선 (샤프비율 1.0)
        fig.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="gray",
            annotation_text="샤프비율 1.0"
        )
        
        fig.update_layout(
            title=f"롤링 샤프비율 ({window}일 윈도우)",
            xaxis_title="날짜",
            yaxis_title="샤프비율",
            height=400,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"롤링 샤프비율 차트 생성 실패: {e}")
        return None


def plot_drawdown_histogram(backtest_result):
    """
    드로다운 분포 히스토그램
    
    Args:
        backtest_result: 백테스팅 결과
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'portfolio_history' not in backtest_result:
        return None
    
    try:
        portfolio_history = backtest_result['portfolio_history']
        if len(portfolio_history) < 2:
            return None
        
        # 드로다운 계산
        drawdowns = []
        peak = portfolio_history[0]
        
        for value in portfolio_history:
            if value > peak:
                peak = value
            
            drawdown = ((value - peak) / peak) * 100
            if drawdown < 0:
                drawdowns.append(drawdown)
        
        if not drawdowns:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=drawdowns,
            nbinsx=30,
            marker_color='#d62728',
            name='드로다운 분포'
        ))
        
        fig.update_layout(
            title="드로다운 분포",
            xaxis_title="드로다운 (%)",
            yaxis_title="빈도",
            height=400,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    
    except Exception as e:
        print(f"드로다운 히스토그램 생성 실패: {e}")
        return None


def plot_win_loss_distribution(backtest_result):
    """
    승/패 거래 분포
    
    Args:
        backtest_result: 백테스팅 결과
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'daily_returns' not in backtest_result:
        return None
    
    try:
        daily_returns = backtest_result['daily_returns']
        if not daily_returns:
            return None
        
        wins = [r['return'] for r in daily_returns if r['return'] > 0]
        losses = [r['return'] for r in daily_returns if r['return'] < 0]
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=wins,
            name='수익 거래',
            marker_color='green',
            opacity=0.7,
            nbinsx=20
        ))
        
        fig.add_trace(go.Histogram(
            x=losses,
            name='손실 거래',
            marker_color='red',
            opacity=0.7,
            nbinsx=20
        ))
        
        fig.update_layout(
            title="승/패 거래 분포",
            xaxis_title="수익률 (%)",
            yaxis_title="빈도",
            height=400,
            barmode='overlay',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"승패 분포 차트 생성 실패: {e}")
        return None


def plot_trade_frequency(backtest_result):
    """
    리밸런싱 빈도 및 거래 통계
    
    Args:
        backtest_result: 백테스팅 결과
    
    Returns:
        plotly Figure
    """
    if not backtest_result or 'daily_returns' not in backtest_result:
        return None
    
    try:
        daily_returns = backtest_result['daily_returns']
        if not daily_returns:
            return None
        
        # 월별 거래 횟수 계산
        monthly_trades = {}
        for r in daily_returns:
            date = datetime.strptime(r['date'], '%Y-%m-%d')
            year_month = f"{date.year}-{date.month:02d}"
            
            if year_month not in monthly_trades:
                monthly_trades[year_month] = 0
            monthly_trades[year_month] += 1
        
        months = sorted(monthly_trades.keys())
        counts = [monthly_trades[m] for m in months]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=months,
            y=counts,
            marker_color='#17becf',
            text=counts,
            textposition='outside',
            name='거래 횟수'
        ))
        
        fig.update_layout(
            title="월별 리밸런싱 빈도",
            xaxis_title="월",
            yaxis_title="거래 횟수",
            height=400,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    
    except Exception as e:
        print(f"거래 빈도 차트 생성 실패: {e}")
        return None


def plot_sector_distribution(historical_data, top_n=5):
    """
    포트폴리오 섹터 분포 (시간별 변화)
    주의: 섹터 정보가 historical_data에 없을 경우 동작하지 않음
    
    Args:
        historical_data: {날짜: DataFrame} 딕셔너리
        top_n: 상위 N개 종목
    
    Returns:
        plotly Figure
    """
    if not historical_data:
        return None
    
    try:
        # 섹터 분포 계산 (Sector 컬럼이 있다고 가정)
        dates = sorted(historical_data.keys())
        sector_counts = {}
        
        for date in dates:
            df = historical_data[date]
            top = df.head(top_n)
            
            if 'Sector' in top.columns:
                for sector in top['Sector']:
                    if sector not in sector_counts:
                        sector_counts[sector] = []
                    sector_counts[sector].append(1)
            else:
                # Sector 컬럼이 없으면 None 반환
                return None
        
        if not sector_counts:
            return None
        
        fig = go.Figure()
        
        for sector, counts in sector_counts.items():
            fig.add_trace(go.Scatter(
                x=dates[:len(counts)],
                y=counts,
                mode='lines+markers',
                name=sector,
                stackgroup='one'
            ))
        
        fig.update_layout(
            title=f"포트폴리오 섹터 분포 (상위 {top_n}개 종목)",
            xaxis_title="날짜",
            yaxis_title="종목 수",
            height=400,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    except Exception as e:
        print(f"섹터 분포 차트 생성 실패: {e}")
        return None


