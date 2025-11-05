# 데이터 저장 및 로드 모듈
import os
import pandas as pd
from datetime import datetime, timedelta
from config import DATA_DIR

def save_daily_data(df, date_str, filename_prefix=""):
    """일일 데이터를 CSV 파일로 저장
    
    Args:
        df: 저장할 DataFrame
        date_str: 날짜 문자열
        filename_prefix: 파일명 prefix (예: "large_", "mega_")
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    filename = f"{DATA_DIR}/finviz_data_{filename_prefix}{date_str}.csv"
    df.to_csv(filename, index=False)
    print(f"데이터를 {filename}에 저장했습니다.")
    return filename

def load_previous_data(days_ago, filename_prefix=""):
    """지정된 일수 전의 데이터를 로드
    
    Args:
        days_ago: 몇 일 전
        filename_prefix: 파일명 prefix (예: "large_", "mega_")
    """
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    filename = f"{DATA_DIR}/finviz_data_{filename_prefix}{target_date}.csv"
    
    print(f"로드 시도: {filename}")
    if os.path.exists(filename):
        print(f"파일 발견: {filename}")
        return pd.read_csv(filename)
    else:
        print(f"{days_ago}일 전 데이터를 찾을 수 없습니다: {filename}")
        return None

def get_last_business_day_offset():
    """현재 날짜 기준으로 마지막 영업일까지의 오프셋을 반환
    
    Returns:
        int: 마지막 영업일까지의 일수 (토요일=1, 일요일=2, 월요일=3, 화~금=1)
    """
    today_weekday = datetime.now().weekday()  # 0=월, 1=화, ..., 5=토, 6=일
    
    if today_weekday == 5:  # 토요일
        return 1  # 금요일
    elif today_weekday == 6:  # 일요일
        return 2  # 금요일
    elif today_weekday == 0:  # 월요일
        return 3  # 금요일
    else:  # 화~금
        return 1  # 전날

def load_last_business_day_data(filename_prefix=""):
    """마지막 영업일의 데이터를 로드
    
    Args:
        filename_prefix: 파일명 prefix (예: "large_", "mega_")
    
    Returns:
        DataFrame 또는 None
    """
    offset = get_last_business_day_offset()
    return load_previous_data(offset, filename_prefix)

def get_available_dates():
    """저장된 데이터의 날짜 목록을 반환"""
    if not os.path.exists(DATA_DIR):
        return []
    
    files = [f for f in os.listdir(DATA_DIR) if f.startswith('finviz_data_') and f.endswith('.csv')]
    dates = [f.replace('finviz_data_', '').replace('.csv', '') for f in files]
    return sorted(dates)
