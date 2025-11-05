"""
데이터 포맷팅 유틸리티
"""
import pandas as pd


def format_percentage(value):
    """
    퍼센트 포맷팅
    
    Args:
        value: 숫자 또는 문자열
    
    Returns:
        str: 포맷된 퍼센트 문자열
    """
    try:
        if isinstance(value, str):
            # 이미 %가 포함되어 있으면 그대로 반환
            if '%' in value:
                return value
            value = float(value.replace('%', ''))
        
        return f"{value:.2f}%"
    except:
        return str(value)


def format_currency(value):
    """
    통화 포맷팅 (달러)
    
    Args:
        value: 숫자
    
    Returns:
        str: 포맷된 통화 문자열
    """
    try:
        value = float(value)
        return f"${value:,.2f}"
    except:
        return str(value)


def format_number(value, decimals=2):
    """
    숫자 포맷팅
    
    Args:
        value: 숫자
        decimals: 소수점 자릿수
    
    Returns:
        str: 포맷된 숫자 문자열
    """
    try:
        value = float(value)
        return f"{value:,.{decimals}f}"
    except:
        return str(value)


def parse_performance(perf_str):
    """
    수익률 문자열을 숫자로 변환
    
    Args:
        perf_str: 수익률 문자열 (예: "123.45%")
    
    Returns:
        float: 수익률 숫자
    """
    try:
        return float(str(perf_str).replace('%', ''))
    except:
        return 0.0


def parse_price(price_str):
    """
    가격 문자열을 숫자로 변환
    
    Args:
        price_str: 가격 문자열
    
    Returns:
        float: 가격 숫자
    """
    try:
        return float(price_str)
    except:
        return 0.0


def get_performance_color(value):
    """
    수익률 값에 따른 색상 반환
    
    Args:
        value: 수익률 값
    
    Returns:
        str: 색상 코드
    """
    try:
        value = float(value)
        if value > 0:
            return "green"
        elif value < 0:
            return "red"
        else:
            return "gray"
    except:
        return "gray"


def get_rank_change_emoji(change):
    """
    순위 변화에 따른 이모지 반환
    
    Args:
        change: 순위 변화 (양수=상승, 음수=하락)
    
    Returns:
        str: 이모지
    """
    if change is None:
        return "🆕"
    elif change > 0:
        return "⬆️"
    elif change < 0:
        return "⬇️"
    else:
        return "➡️"


def format_rank_change(change):
    """
    순위 변화 포맷팅
    
    Args:
        change: 순위 변화 (양수=상승, 음수=하락)
    
    Returns:
        str: 포맷된 순위 변화 문자열
    """
    if change is None:
        return "신규"
    elif change > 0:
        return f"↑{change}"
    elif change < 0:
        return f"↓{abs(change)}"
    else:
        return "→"


def style_dataframe(df):
    """
    DataFrame에 스타일 적용
    
    Args:
        df: pandas DataFrame
    
    Returns:
        styled DataFrame
    """
    # 수익률 컬럼에 색상 적용
    def color_performance(val):
        try:
            num_val = parse_performance(val)
            if num_val > 0:
                return 'color: green'
            elif num_val < 0:
                return 'color: red'
            else:
                return 'color: gray'
        except:
            return ''
    
    # Change 컬럼에 색상 적용
    def color_change(val):
        try:
            num_val = parse_performance(val)
            if num_val > 0:
                return 'color: green'
            elif num_val < 0:
                return 'color: red'
            else:
                return 'color: gray'
        except:
            return ''
    
    styled = df.copy()
    
    # 수익률 및 변화 컬럼에 스타일 적용
    if 'Perf Quart' in styled.columns:
        styled = styled.style.applymap(color_performance, subset=['Perf Quart'])
    
    if 'Change' in styled.columns:
        styled = styled.style.applymap(color_change, subset=['Change'])
    
    return styled


