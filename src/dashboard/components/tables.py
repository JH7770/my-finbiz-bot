"""
데이터 테이블 컴포넌트
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# 유틸리티 임포트
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src' / 'dashboard' / 'utils'))
from formatting import parse_performance, parse_price, format_percentage, format_currency


def display_top_stocks_table(df, screener_name="대형주"):
    """
    상위 종목 테이블 표시
    
    Args:
        df: DataFrame
        screener_name: 스크리너 이름
    """
    if df is None or df.empty:
        st.warning("데이터가 없습니다.")
        return
    
    st.subheader(f"🏆 {screener_name} 상위 5개 종목")
    
    top5 = df.head(5).copy()
    
    # 순위 컬럼 추가
    top5.insert(0, '순위', range(1, len(top5) + 1))
    
    # 필요한 컬럼만 선택
    display_columns = ['순위', 'Ticker', 'Perf Quart', 'Price', 'Change']
    
    if all(col in top5.columns for col in display_columns):
        display_df = top5[display_columns].copy()
        
        # 컬럼명 한글화
        display_df.columns = ['순위', '티커', '3개월 수익률', '현재가 ($)', '일일 변화']
        
        # 스타일 적용 함수
        def highlight_performance(row):
            styles = [''] * len(row)
            
            # 3개월 수익률 색상
            perf_idx = 2
            perf_val = parse_performance(row.iloc[perf_idx])
            if perf_val > 0:
                styles[perf_idx] = 'color: green; font-weight: bold'
            elif perf_val < 0:
                styles[perf_idx] = 'color: red; font-weight: bold'
            
            # 일일 변화 색상
            change_idx = 4
            change_val = parse_performance(row.iloc[change_idx])
            if change_val > 0:
                styles[change_idx] = 'color: green'
            elif change_val < 0:
                styles[change_idx] = 'color: red'
            
            return styles
        
        # 인덱스 리셋 (PyArrow 에러 방지)
        display_df = display_df.reset_index(drop=True)
        
        # 스타일 적용
        styled_df = display_df.style.apply(highlight_performance, axis=1)
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        # 컬럼이 없으면 전체 표시
        st.dataframe(top5, use_container_width=True)


def display_comparison_table(current_df, previous_df, period_name="전날"):
    """
    비교 테이블 표시
    
    Args:
        current_df: 현재 DataFrame
        previous_df: 이전 DataFrame
        period_name: 비교 기간 이름
    """
    if current_df is None or current_df.empty:
        st.warning("현재 데이터가 없습니다.")
        return
    
    if previous_df is None or previous_df.empty:
        st.info(f"{period_name} 데이터가 없습니다.")
        return
    
    st.subheader(f"📊 {period_name} 대비 변화")
    
    current_top5 = current_df.head(5)
    previous_top5 = previous_df.head(5)
    
    # 비교 데이터 생성
    comparison_data = []
    
    for i, row in current_top5.iterrows():
        ticker = row['Ticker']
        current_rank = i + 1
        current_perf = parse_performance(row['Perf Quart'])
        current_price = parse_price(row['Price'])
        
        # 이전 데이터에서 찾기
        prev_row = previous_top5[previous_top5['Ticker'] == ticker]
        
        if not prev_row.empty:
            previous_rank = prev_row.index[0] + 1
            previous_perf = parse_performance(prev_row.iloc[0]['Perf Quart'])
            previous_price = parse_price(prev_row.iloc[0]['Price'])
            
            rank_change = previous_rank - current_rank
            perf_change = current_perf - previous_perf
            price_change = current_price - previous_price
            price_change_pct = (price_change / previous_price * 100) if previous_price > 0 else 0
            
            rank_emoji = '🆕' if rank_change is None else ('⬆️' if rank_change > 0 else ('⬇️' if rank_change < 0 else '➡️'))
            
            comparison_data.append({
                '티커': ticker,
                '순위': f"{current_rank} {rank_emoji}",
                '순위변화': f"{rank_change:+d}" if rank_change else "→",
                '3개월 수익률': format_percentage(current_perf),
                '수익률 변화': format_percentage(perf_change),
                '현재가': format_currency(current_price),
                '가격 변화': f"{format_currency(price_change)} ({price_change_pct:+.2f}%)"
            })
        else:
            # 신규 진입
            comparison_data.append({
                '티커': ticker,
                '순위': f"{current_rank} 🆕",
                '순위변화': "신규",
                '3개월 수익률': format_percentage(current_perf),
                '수익률 변화': "-",
                '현재가': format_currency(current_price),
                '가격 변화': "-"
            })
    
    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        comp_df = comp_df.reset_index(drop=True)  # PyArrow 에러 방지
        st.dataframe(comp_df, use_container_width=True, hide_index=True)


def display_new_dropped_stocks(current_df, previous_df):
    """
    신규 진입 및 탈락 종목 표시
    
    Args:
        current_df: 현재 DataFrame
        previous_df: 이전 DataFrame
    """
    if current_df is None or previous_df is None:
        return
    
    current_tickers = set(current_df.head(5)['Ticker'])
    previous_tickers = set(previous_df.head(5)['Ticker'])
    
    new_tickers = current_tickers - previous_tickers
    dropped_tickers = previous_tickers - current_tickers
    
    col1, col2 = st.columns(2)
    
    with col1:
        if new_tickers:
            st.success(f"🆕 신규 진입: {', '.join(new_tickers)}")
        else:
            st.info("신규 진입 종목 없음")
    
    with col2:
        if dropped_tickers:
            st.warning(f"📉 탈락: {', '.join(dropped_tickers)}")
        else:
            st.info("탈락 종목 없음")


def display_historical_table(historical_data, limit=10):
    """
    히스토리 데이터 테이블 표시
    
    Args:
        historical_data: {날짜: DataFrame} 딕셔너리
        limit: 표시할 최대 날짜 수
    """
    if not historical_data:
        st.warning("히스토리 데이터가 없습니다.")
        return
    
    dates = sorted(historical_data.keys(), reverse=True)[:limit]
    
    for date in dates:
        with st.expander(f"📅 {date}"):
            df = historical_data[date]
            display_top_stocks_table(df, screener_name=f"{date} 데이터")

