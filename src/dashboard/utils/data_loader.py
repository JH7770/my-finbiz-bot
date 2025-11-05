"""
데이터 로딩 유틸리티
"""
import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config import DATA_DIR


@st.cache_data(ttl=300)  # 5분 캐시
def load_latest_data(screener_type="large"):
    """
    최신 데이터 로드
    
    Args:
        screener_type: 'large' 또는 'mega'
    
    Returns:
        DataFrame 또는 None
    """
    data_path = Path(DATA_DIR)
    
    # 최신 파일 찾기
    csv_files = sorted(data_path.glob(f'finviz_data_{screener_type}_*.csv'), reverse=True)
    
    if not csv_files:
        return None
    
    latest_file = csv_files[0]
    
    try:
        df = pd.read_csv(latest_file)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


@st.cache_data(ttl=300)
def load_data_by_date(date_str, screener_type="large"):
    """
    특정 날짜의 데이터 로드
    
    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)
        screener_type: 'large' 또는 'mega'
    
    Returns:
        DataFrame 또는 None
    """
    data_path = Path(DATA_DIR)
    filename = data_path / f'finviz_data_{screener_type}_{date_str}.csv'
    
    if not filename.exists():
        return None
    
    try:
        df = pd.read_csv(filename)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


@st.cache_data(ttl=300)
def get_available_dates(screener_type="large"):
    """
    사용 가능한 날짜 목록 반환
    
    Args:
        screener_type: 'large' 또는 'mega'
    
    Returns:
        list: 날짜 문자열 리스트 (정렬됨)
    """
    data_path = Path(DATA_DIR)
    
    csv_files = sorted(data_path.glob(f'finviz_data_{screener_type}_*.csv'))
    
    dates = []
    for f in csv_files:
        # 파일명에서 날짜 추출
        date_str = f.stem.replace(f'finviz_data_{screener_type}_', '')
        dates.append(date_str)
    
    return sorted(dates)


@st.cache_data(ttl=300)
def load_historical_range(start_date, end_date, screener_type="large"):
    """
    기간별 히스토리 데이터 로드
    
    Args:
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        screener_type: 'large' 또는 'mega'
    
    Returns:
        dict: {날짜: DataFrame}
    """
    available_dates = get_available_dates(screener_type)
    
    # 날짜 필터링
    filtered_dates = [
        d for d in available_dates 
        if start_date <= d <= end_date
    ]
    
    historical_data = {}
    for date in filtered_dates:
        df = load_data_by_date(date, screener_type)
        if df is not None:
            historical_data[date] = df
    
    return historical_data


@st.cache_data(ttl=300)
def load_backtest_results(screener_type="large"):
    """
    백테스팅 결과 로드
    
    Args:
        screener_type: 'large' 또는 'mega'
    
    Returns:
        dict 또는 None
    """
    cache_file = Path(DATA_DIR) / 'backtest_cache.json'
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # 캐시 키 찾기 (가장 최근 것 사용)
        matching_keys = [k for k in cache.keys() if k.startswith(f"{screener_type}_")]
        
        if not matching_keys:
            return None
        
        # 가장 최근 캐시 반환
        latest_key = matching_keys[-1]
        return cache[latest_key].get('result')
    
    except Exception as e:
        st.error(f"백테스팅 결과 로드 실패: {e}")
        return None


@st.cache_data(ttl=300)
def load_technical_analysis(screener_type="large"):
    """
    기술적 분석 결과 로드 (최신 데이터 기반으로 재계산)
    
    Args:
        screener_type: 'large' 또는 'mega'
    
    Returns:
        dict 또는 None
    """
    df = load_latest_data(screener_type)
    
    if df is None:
        return None
    
    try:
        # technical_analyzer 모듈 임포트
        sys.path.insert(0, str(project_root / 'src'))
        from technical_analyzer import analyze_top10_technical
        
        technical_analysis = analyze_top10_technical(df)
        return technical_analysis
    
    except Exception as e:
        st.error(f"기술적 분석 로드 실패: {e}")
        return None


@st.cache_data(ttl=300)
def get_latest_date(screener_type="large"):
    """
    최신 데이터의 날짜 반환
    
    Args:
        screener_type: 'large' 또는 'mega'
    
    Returns:
        str: 날짜 문자열 (YYYY-MM-DD) 또는 None
    """
    dates = get_available_dates(screener_type)
    
    if not dates:
        return None
    
    return dates[-1]


@st.cache_data(ttl=300)
def load_market_regime():
    """
    시장 필터 상태 로드
    
    Returns:
        dict 또는 None
    """
    cache_file = Path(DATA_DIR) / 'market_regime_cache.json'
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            market_regime = json.load(f)
        return market_regime
    except Exception as e:
        st.error(f"시장 상태 로드 실패: {e}")
        return None


def clear_cache():
    """
    모든 캐시 클리어
    """
    st.cache_data.clear()

