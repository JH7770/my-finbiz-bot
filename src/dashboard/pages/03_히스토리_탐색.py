"""
히스토리 탐색 페이지
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from dashboard.utils.data_loader import (
    get_available_dates, load_data_by_date, load_historical_range
)
from dashboard.components.charts import (
    plot_rank_changes_heatmap, plot_performance_comparison
)
from dashboard.components.tables import (
    display_top_stocks_table, display_comparison_table
)

# 페이지 설정
st.set_page_config(
    page_title="히스토리 탐색",
    page_icon="📅",
    layout="wide"
)

st.title("📅 히스토리 탐색")
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
    
    # 사용 가능한 날짜
    available_dates = get_available_dates(screener_type)
    
    if available_dates:
        st.success(f"📊 {len(available_dates)}일치 데이터 사용 가능")
        st.caption(f"최초: {available_dates[0]}")
        st.caption(f"최신: {available_dates[-1]}")
    else:
        st.error("사용 가능한 데이터가 없습니다.")

# 메인 콘텐츠
try:
    if not available_dates:
        st.error("히스토리 데이터가 없습니다. main.py를 실행하여 데이터를 수집하세요.")
        st.stop()
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📅 날짜별 조회", "📊 기간별 비교", "🔥 순위 변화 히트맵"])
    
    # 탭 1: 날짜별 조회
    with tab1:
        st.header("📅 날짜별 데이터 조회")
        
        # 날짜 선택
        selected_date = st.selectbox(
            "날짜 선택",
            options=available_dates,
            index=len(available_dates) - 1  # 최신 날짜 기본 선택
        )
        
        if selected_date:
            st.divider()
            
            # 선택된 날짜 데이터 로드
            df = load_data_by_date(selected_date, screener_type)
            
            if df is not None and not df.empty:
                # 상위 종목 테이블
                display_top_stocks_table(df, f"{screener_name} ({selected_date})")
                
                st.write("")  # 공백
                
                # 전날과 비교
                date_idx = available_dates.index(selected_date)
                if date_idx > 0:
                    previous_date = available_dates[date_idx - 1]
                    previous_df = load_data_by_date(previous_date, screener_type)
                    
                    st.divider()
                    display_comparison_table(df, previous_df, f"{previous_date} 대비")
                else:
                    st.info("비교할 이전 데이터가 없습니다.")
            else:
                st.error("데이터를 불러올 수 없습니다.")
    
    # 탭 2: 기간별 비교
    with tab2:
        st.header("📊 기간별 성과 비교")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 시작 날짜
            start_date = st.selectbox(
                "시작 날짜",
                options=available_dates,
                index=max(0, len(available_dates) - 7)  # 기본 7일 전
            )
        
        with col2:
            # 종료 날짜
            end_date = st.selectbox(
                "종료 날짜",
                options=available_dates,
                index=len(available_dates) - 1  # 최신 날짜
            )
        
        if start_date and end_date and start_date <= end_date:
            st.divider()
            
            # 기간별 데이터 로드
            historical_data = load_historical_range(start_date, end_date, screener_type)
            
            if historical_data:
                st.success(f"📊 {len(historical_data)}일치 데이터 로드됨")
                
                # 평균 수익률 추이 차트
                st.subheader("📈 평균 수익률 추이")
                perf_fig = plot_performance_comparison(historical_data)
                if perf_fig:
                    st.plotly_chart(perf_fig, use_container_width=True)
                else:
                    st.warning("차트를 생성할 수 없습니다.")
                
                st.divider()
                
                # 시작일과 종료일 비교
                st.subheader("📊 기간 비교")
                
                start_df = historical_data.get(start_date)
                end_df = historical_data.get(end_date)
                
                if start_df is not None and end_df is not None:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**시작일 ({start_date})**")
                        display_top_stocks_table(start_df, f"{start_date}")
                    
                    with col2:
                        st.write(f"**종료일 ({end_date})**")
                        display_top_stocks_table(end_df, f"{end_date}")
                    
                    st.divider()
                    
                    # 변화 비교
                    from dashboard.components.tables import display_new_dropped_stocks
                    display_new_dropped_stocks(end_df, start_df)
                else:
                    st.error("데이터를 불러올 수 없습니다.")
            else:
                st.error("기간별 데이터를 불러올 수 없습니다.")
        else:
            st.warning("시작 날짜는 종료 날짜보다 이전이어야 합니다.")
    
    # 탭 3: 순위 변화 히트맵
    with tab3:
        st.header("🔥 순위 변화 히트맵")
        
        # 최소 데이터 확인
        if len(available_dates) < 2:
            st.warning("히트맵을 표시하려면 최소 2일 이상의 데이터가 필요합니다.")
            st.info("main.py를 여러 번 실행하여 더 많은 데이터를 수집하세요.")
        else:
            # 기간 선택
            max_days = min(30, len(available_dates))
            min_days = 2  # 최소 2일
            default_days = min(14, max_days)
            
            # 데이터가 충분하면 슬라이더 표시, 아니면 자동 설정
            if max_days > min_days:
                days_back = st.slider(
                    "조회 기간 (일)",
                    min_value=min_days,
                    max_value=max_days,
                    value=default_days,
                    step=1,
                    help=f"사용 가능한 데이터: {len(available_dates)}일"
                )
            else:
                # 데이터가 2일치만 있으면 자동으로 2일 선택
                days_back = len(available_dates)
                st.info(f"📊 사용 가능한 데이터: {len(available_dates)}일 (전체 표시)")
            
            if days_back <= len(available_dates):
                # 최근 N일 데이터 로드
                recent_dates = available_dates[-days_back:]
                start_date = recent_dates[0]
                end_date = recent_dates[-1]
                
                historical_data = load_historical_range(start_date, end_date, screener_type)
                
                if historical_data:
                    st.divider()
                    
                    st.info(f"📊 {start_date} ~ {end_date} 기간의 순위 변화를 표시합니다. ({len(historical_data)}일)")
                    
                    # 히트맵 생성
                    heatmap_fig = plot_rank_changes_heatmap(historical_data)
                    
                    if heatmap_fig:
                        st.plotly_chart(heatmap_fig, use_container_width=True)
                        
                        st.write("")  # 공백
                        
                        st.caption("""
                        **히트맵 해석:**
                        - 빨간색(1): 1위
                        - 초록색(5): 5위
                        - 빈 칸: 순위 밖
                        - 같은 종목이 계속 상위권을 유지하면 수평선이 나타납니다.
                        """)
                    else:
                        st.warning("히트맵을 생성할 수 없습니다.")
                else:
                    st.error("히스토리 데이터를 불러올 수 없습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)

