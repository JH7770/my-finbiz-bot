"""
종목 상세 분석 페이지
"""
import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from dashboard.utils.data_loader import load_latest_data, load_technical_analysis
from dashboard.components.charts import plot_candlestick_with_ma
from dashboard.utils.formatting import format_percentage, format_currency, parse_performance, parse_price

# 페이지 설정
st.set_page_config(
    page_title="종목 상세 분석",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 종목 상세 분석")
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
    
    # 차트 기간 선택
    period = st.selectbox(
        "차트 기간",
        options=["1mo", "3mo", "6mo", "1y", "2y"],
        format_func=lambda x: {
            "1mo": "1개월",
            "3mo": "3개월",
            "6mo": "6개월",
            "1y": "1년",
            "2y": "2년"
        }[x],
        index=1  # 기본 3개월
    )

# 메인 콘텐츠
try:
    # 데이터 로드
    df = load_latest_data(screener_type)
    
    if df is None or df.empty:
        st.error("데이터를 불러올 수 없습니다.")
        st.stop()
    
    top5 = df.head(5)
    
    # 종목 선택
    st.header(f"📊 {screener_name} 상위 5개 종목")
    
    ticker = st.selectbox(
        "종목 선택",
        options=top5['Ticker'].tolist(),
        format_func=lambda x: f"{x} - {format_percentage(top5[top5['Ticker']==x].iloc[0]['Perf Quart'])}"
    )
    
    if ticker:
        st.divider()
        
        # 선택된 종목 정보
        stock_info = top5[top5['Ticker'] == ticker].iloc[0]
        
        # 기본 정보 카드
        st.subheader(f"📈 {ticker} 기본 정보")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="현재가",
                value=format_currency(parse_price(stock_info['Price']))
            )
        
        with col2:
            st.metric(
                label="3개월 수익률",
                value=format_percentage(stock_info['Perf Quart'])
            )
        
        with col3:
            change = parse_performance(stock_info['Change'])
            st.metric(
                label="일일 변화",
                value=format_percentage(stock_info['Change']),
                delta=format_percentage(change)
            )
        
        with col4:
            st.metric(
                label="거래량",
                value=stock_info['Volume']
            )
        
        st.divider()
        
        # 기술적 분석 정보
        st.subheader("🔍 기술적 분석")
        
        with st.spinner("기술적 분석 로딩 중..."):
            technical_analysis = load_technical_analysis(screener_type)
            
            if technical_analysis and ticker in technical_analysis:
                tech = technical_analysis[ticker]
                
                if tech['status'] == 'success':
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            label="MA20 (20일선)",
                            value=format_currency(tech['ma20']),
                            delta="위" if tech['above_ma20'] else "아래",
                            delta_color="normal" if tech['above_ma20'] else "inverse"
                        )
                    
                    with col2:
                        st.metric(
                            label="MA60 (60일선)",
                            value=format_currency(tech['ma60']),
                            delta="위" if tech['above_ma60'] else "아래",
                            delta_color="normal" if tech['above_ma60'] else "inverse"
                        )
                    
                    with col3:
                        st.metric(
                            label="MA120 (120일선)",
                            value=format_currency(tech['ma120']),
                            delta="위" if tech['above_ma120'] else "아래",
                            delta_color="normal" if tech['above_ma120'] else "inverse"
                        )
                    
                    with col4:
                        status_icon = "✅" if tech['all_conditions_met'] else "❌"
                        status_text = "강세" if tech['all_conditions_met'] else "약세"
                        st.metric(
                            label="종합 판단",
                            value=f"{status_icon} {status_text}"
                        )
                    
                    # 조건 체크
                    st.write("")
                    st.write("**조건 체크:**")
                    st.write(f"- 현재가 > 60일선: {'✅' if tech['above_ma60'] else '❌'}")
                    st.write(f"- 현재가 > 120일선: {'✅' if tech['above_ma120'] else '❌'}")
                    st.write(f"- 60일선 > 120일선: {'✅' if tech['ma60_above_ma120'] else '❌'}")
                else:
                    st.warning("기술적 분석 데이터가 부족합니다.")
            else:
                st.warning("기술적 분석 데이터를 불러올 수 없습니다.")
        
        st.divider()
        
        # 가격 차트
        st.subheader(f"📊 {ticker} 가격 차트 (이동평균선 포함)")
        
        with st.spinner("차트 로딩 중..."):
            chart_fig = plot_candlestick_with_ma(ticker, period=period)
            
            if chart_fig:
                st.plotly_chart(chart_fig, use_container_width=True)
            else:
                st.error("차트를 생성할 수 없습니다.")
        
        st.divider()
        
        # 추가 정보
        with st.expander("📝 전체 정보 보기"):
            st.dataframe(stock_info.to_frame(), use_container_width=True)

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.exception(e)


