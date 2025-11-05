# 데이터 분석 모듈
import pandas as pd

def compare_data(current_df, previous_df, period_name):
    """현재 데이터와 이전 데이터를 비교"""
    if previous_df is None:
        return f"{period_name}: 비교할 데이터가 없습니다."
    
    current_top10 = current_df.head(5)
    previous_top10 = previous_df.head(5)
    
    # 새로운 종목들 (이전에 없었던 종목)
    current_tickers = set(current_top10['Ticker'])
    previous_tickers = set(previous_top10['Ticker'])
    new_tickers = current_tickers - previous_tickers
    dropped_tickers = previous_tickers - current_tickers
    
    # 순위 변화 분석
    rank_changes = []
    for ticker in current_tickers & previous_tickers:
        current_rank = current_top10[current_top10['Ticker'] == ticker].index[0] + 1
        previous_rank = previous_top10[previous_top10['Ticker'] == ticker].index[0] + 1
        change = previous_rank - current_rank  # 양수면 상승, 음수면 하락
        rank_changes.append({
            'ticker': ticker,
            'current_rank': current_rank,
            'previous_rank': previous_rank,
            'change': change
        })
    
    # 상위 3개 종목의 수익률 및 가격 변화
    top3_changes = []
    for i in range(min(3, len(current_top10), len(previous_top10))):
        current_ticker = current_top10.iloc[i]['Ticker']
        current_perf = current_top10.iloc[i]['Perf Quart']
        current_price = current_top10.iloc[i]['Price']
        
        if current_ticker in previous_tickers:
            prev_row = previous_top10[previous_top10['Ticker'] == current_ticker]
            if not prev_row.empty:
                previous_perf = prev_row.iloc[0]['Perf Quart']
                previous_price = prev_row.iloc[0]['Price']
                
                # 수익률 변화 계산
                perf_change = float(current_perf.replace('%', '')) - float(previous_perf.replace('%', ''))
                
                # 가격 변화 계산
                try:
                    current_price_num = float(current_price)
                    previous_price_num = float(previous_price)
                    price_change = current_price_num - previous_price_num
                    price_change_pct = (price_change / previous_price_num) * 100
                except (ValueError, ZeroDivisionError):
                    price_change = 0
                    price_change_pct = 0
                
                top3_changes.append({
                    'ticker': current_ticker,
                    'current_perf': current_perf,
                    'previous_perf': previous_perf,
                    'perf_change': perf_change,
                    'current_price': current_price,
                    'previous_price': previous_price,
                    'price_change': price_change,
                    'price_change_pct': price_change_pct
                })
    
    return {
        'period': period_name,
        'new_tickers': list(new_tickers),
        'dropped_tickers': list(dropped_tickers),
        'rank_changes': rank_changes,
        'top3_changes': top3_changes
    }

def get_top_performers(df, n=10):
    """상위 N개 종목 반환"""
    return df.head(n)[['Ticker', 'Perf Quart', 'Price', 'Change']]

def calculate_portfolio_allocation(n_stocks):
    """포트폴리오 동일비중 할당 계산"""
    return 1.0 / n_stocks if n_stocks > 0 else 0

def calculate_summary_stats(df):
    """요약 통계 계산"""
    top10 = df.head(5)
    
    # 수익률을 숫자로 변환
    perf_values = []
    for perf in top10['Perf Quart']:
        try:
            perf_num = float(perf.replace('%', ''))
            perf_values.append(perf_num)
        except (ValueError, AttributeError):
            continue
    
    # 가격을 숫자로 변환
    price_values = []
    for price in top10['Price']:
        try:
            price_num = float(price)
            price_values.append(price_num)
        except (ValueError, AttributeError):
            continue
    
    # 거래량을 숫자로 변환 (M, K 단위 처리)
    volume_values = []
    for volume in top10['Volume']:
        try:
            vol_str = str(volume).replace(',', '').replace('"', '')
            if 'M' in vol_str:
                vol_num = float(vol_str.replace('M', '')) * 1000000
            elif 'K' in vol_str:
                vol_num = float(vol_str.replace('K', '')) * 1000
            else:
                vol_num = float(vol_str)
            volume_values.append(vol_num)
        except (ValueError, AttributeError):
            continue
    
    stats = {
        'avg_performance': sum(perf_values) / len(perf_values) if perf_values else 0,
        'max_performance': max(perf_values) if perf_values else 0,
        'min_performance': min(perf_values) if perf_values else 0,
        'avg_price': sum(price_values) / len(price_values) if price_values else 0,
        'total_volume': sum(volume_values) if volume_values else 0,
        'avg_volume': sum(volume_values) / len(volume_values) if volume_values else 0,
        'count': len(top10)
    }
    
    # 가장 큰 상승/하락 종목 찾기
    if len(top10) > 0:
        # Change 컬럼에서 가장 큰 변화 찾기
        change_values = []
        for change in top10['Change']:
            try:
                change_num = float(change.replace('%', ''))
                change_values.append(change_num)
            except (ValueError, AttributeError):
                change_values.append(0)
        
        if change_values:
            max_change_idx = change_values.index(max(change_values))
            min_change_idx = change_values.index(min(change_values))
            
            stats['biggest_gainer'] = {
                'ticker': top10.iloc[max_change_idx]['Ticker'],
                'change': f"{change_values[max_change_idx]:.2f}%"
            }
            stats['biggest_loser'] = {
                'ticker': top10.iloc[min_change_idx]['Ticker'],
                'change': f"{change_values[min_change_idx]:.2f}%"
            }
    
    return stats

def get_rank_changes_detailed(current_df, previous_df):
    """상세한 순위 변화 분석"""
    if previous_df is None:
        return []
    
    current_top10 = current_df.head(5)
    previous_top10 = previous_df.head(5)
    
    rank_changes = []
    
    # 현재 상위 5개 종목들의 순위 변화 분석
    for i, row in current_top10.iterrows():
        ticker = row['Ticker']
        current_rank = i + 1
        
        # 이전 데이터에서 해당 종목 찾기
        prev_match = previous_top10[previous_top10['Ticker'] == ticker]
        
        if not prev_match.empty:
            previous_rank = prev_match.index[0] + 1
            rank_change = previous_rank - current_rank  # 양수면 상승, 음수면 하락
            
            # 수익률과 가격 변화도 계산
            current_perf = row['Perf Quart']
            current_price = row['Price']
            
            prev_perf = prev_match.iloc[0]['Perf Quart']
            prev_price = prev_match.iloc[0]['Price']
            
            # 수익률 변화
            try:
                perf_change = float(current_perf.replace('%', '')) - float(prev_perf.replace('%', ''))
            except (ValueError, AttributeError):
                perf_change = 0
            
            # 가격 변화
            try:
                price_change = float(current_price) - float(prev_price)
                price_change_pct = (price_change / float(prev_price)) * 100 if float(prev_price) != 0 else 0
            except (ValueError, AttributeError, ZeroDivisionError):
                price_change = 0
                price_change_pct = 0
            
            rank_changes.append({
                'ticker': ticker,
                'current_rank': current_rank,
                'previous_rank': previous_rank,
                'rank_change': rank_change,
                'perf_change': perf_change,
                'price_change': price_change,
                'price_change_pct': price_change_pct
            })
        else:
            # 새로 진입한 종목
            rank_changes.append({
                'ticker': ticker,
                'current_rank': current_rank,
                'previous_rank': None,
                'rank_change': None,
                'perf_change': 0,
                'price_change': 0,
                'price_change_pct': 0
            })
    
    return rank_changes
