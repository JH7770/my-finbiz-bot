# Finviz 웹 스크래핑 모듈
import requests
import pandas as pd
from bs4 import BeautifulSoup

def scrape_finviz_screener(url=None):
    """Finviz 스크리너에서 대형주/초대형주 3개월 수익률 데이터를 스크래핑
    
    Args:
        url: Finviz 스크리너 URL (None이면 기본 대형주 URL 사용)
    """
    if url is None:
        from config import FINVIZ_URL_LARGE
        url = FINVIZ_URL_LARGE
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print("Finviz 웹 페이지에서 데이터를 가져오는 중...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 테이블 찾기 (여러 가능한 클래스명 시도)
    table = None
    possible_classes = ['table-light', 'screener_table', 'table', 'screener']
    
    for class_name in possible_classes:
        table = soup.find('table', {'class': class_name})
        if table:
            print(f"테이블을 찾았습니다: {class_name}")
            break
    
    if not table:
        # 클래스명 없이 테이블 찾기
        tables = soup.find_all('table')
        print(f"총 {len(tables)}개의 테이블을 찾았습니다.")
        
        # 가장 큰 테이블 선택 (데이터가 많은 테이블)
        if tables:
            table = max(tables, key=lambda t: len(t.find_all('tr')))
            print("가장 큰 테이블을 선택했습니다.")
        else:
            print("테이블을 찾을 수 없습니다.")
            return None
    
    # 헤더 추출
    headers = []
    rows = table.find_all('tr')
    print(f"총 {len(rows)}개의 행을 찾았습니다.")
    
    # 첫 번째 행이 헤더인지 확인
    if len(rows) > 0:
        first_row = rows[0]
        cells = first_row.find_all(['td', 'th'])
        print(f"첫 번째 행의 셀 수: {len(cells)}")
        
        for cell in cells:
            text = cell.get_text().strip()
            headers.append(text)
            print(f"헤더 셀: '{text}'")
    
    print(f"컬럼 헤더: {headers}")
    
    # 헤더가 비어있으면 기본 헤더 사용
    if not headers or all(h == '' for h in headers):
        print("헤더가 비어있어서 기본 헤더를 사용합니다.")
        headers = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Market Cap', 'P/E', 'Price', 'Change', 'Volume', 'Performance (Quarter)', 'Performance (Month)', 'Performance (Week)', 'Performance (Half Year)', 'Performance (Year)', 'Performance (3 Years)', 'Performance (5 Years)', 'Performance (10 Years)']
    
    # 데이터 추출
    data = []
    data_rows = rows[1:] if len(rows) > 1 else rows  # 헤더가 있으면 제외, 없으면 모든 행 사용
    
    for row in data_rows:
        cells = row.find_all('td')
        if len(cells) > 0:
            row_data = []
            for cell in cells:
                text = cell.get_text().strip()
                # 링크가 있는 경우 (티커) 링크 텍스트 사용
                link = cell.find('a')
                if link:
                    text = link.get_text().strip()
                row_data.append(text)
            data.append(row_data)
    
    # DataFrame 생성
    df = pd.DataFrame(data, columns=headers)
    print(f"총 {len(df)}개 종목을 가져왔습니다.")
    
    return df

def scrape_all_tickers_with_pagination(screener_type="large", max_pages=20):
    """Finviz 스크리너에서 모든 페이지의 티커 리스트를 가져오기
    
    Args:
        screener_type: 'large' 또는 'mega'
        max_pages: 최대 페이지 수 (기본: 20)
    
    Returns:
        모든 티커가 포함된 DataFrame
    """
    from config import FINVIZ_URL_LARGE, FINVIZ_URL_MEGA
    
    base_url = FINVIZ_URL_LARGE if screener_type == "large" else FINVIZ_URL_MEGA
    
    all_data = []
    page = 1
    
    print(f"{screener_type} 스크리너에서 모든 티커를 가져오는 중...")
    
    while page <= max_pages:
        # 페이지네이션 URL 생성 (r=1, r=21, r=41, ...)
        offset = (page - 1) * 20
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}&r={offset + 1}"
        
        try:
            df_page = scrape_finviz_screener(url)
            
            if df_page is None or len(df_page) == 0:
                print(f"페이지 {page}: 데이터가 없습니다. 중단합니다.")
                break
            
            all_data.append(df_page)
            print(f"페이지 {page}: {len(df_page)}개 종목 수집")
            
            # 20개 미만이면 마지막 페이지
            if len(df_page) < 20:
                print(f"마지막 페이지에 도달했습니다.")
                break
            
            page += 1
            
        except Exception as e:
            print(f"페이지 {page} 수집 중 오류: {e}")
            break
    
    if not all_data:
        print("티커 데이터를 가져올 수 없습니다.")
        return None
    
    # 모든 페이지 데이터 합치기
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"총 {len(combined_df)}개 종목을 수집했습니다.")
    
    return combined_df
