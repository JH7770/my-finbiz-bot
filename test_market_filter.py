#!/usr/bin/env python3
"""
시장 필터 테스트 스크립트
"""
import sys
import os

# src 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from market_filter import check_market_regime, get_historical_market_regime
from logger import get_logger

logger = get_logger()

def test_current_market():
    """현재 시장 상태 테스트"""
    print("=" * 60)
    print("현재 시장 상태 테스트")
    print("=" * 60)
    
    result = check_market_regime(use_cache=False)
    
    if result:
        print(f"\n📅 날짜: {result['date']}")
        print(f"⏰ 시간: {result['timestamp']}")
        print(f"\n💰 SPY 가격: ${result['spy_price']:.2f}")
        print(f"📊 SPY MA200: ${result['spy_ma200']:.2f}")
        print(f"📊 SPY MA120: ${result['spy_ma120']:.2f}")
        print(f"📈 VIX: {result['vix']:.2f} (임계값: {result['vix_threshold']})")
        
        print(f"\n🔍 판단: {result['reason']}")
        
        if result['hold_cash']:
            print("\n⚠️ **약세장 감지 - 매수 금지**")
        else:
            print("\n✅ **정상 시장 - 매수 가능**")
        
        # 조건별 상세 분석
        print("\n" + "=" * 60)
        print("상세 분석")
        print("=" * 60)
        
        spy_below_ma200 = result['spy_price'] < result['spy_ma200']
        spy_below_ma120 = result['spy_price'] < result['spy_ma120']
        vix_high = result['vix'] > result['vix_threshold']
        
        print(f"SPY < MA200: {'예' if spy_below_ma200 else '아니오'}")
        print(f"SPY < MA120: {'예' if spy_below_ma120 else '아니오'}")
        print(f"VIX > {result['vix_threshold']}: {'예' if vix_high else '아니오'}")
        
        print(f"\n조건 1 (SPY < MA200): {'충족' if spy_below_ma200 else '미충족'}")
        print(f"조건 2 (SPY < MA120 AND VIX > {result['vix_threshold']}): {'충족' if (spy_below_ma120 and vix_high) else '미충족'}")
        
    else:
        print("❌ 시장 상태를 가져올 수 없습니다.")
        return False
    
    return True


def test_historical_market(date_str):
    """특정 날짜의 시장 상태 테스트 (백테스팅용)"""
    print("\n" + "=" * 60)
    print(f"히스토리 시장 상태 테스트: {date_str}")
    print("=" * 60)
    
    result = get_historical_market_regime(date_str)
    
    if result:
        print(f"\n📅 날짜: {result['date']}")
        print(f"💰 SPY: ${result['spy_price']:.2f}")
        print(f"📊 MA200: ${result['spy_ma200']:.2f}")
        print(f"📊 MA120: ${result['spy_ma120']:.2f}")
        print(f"📈 VIX: {result['vix']:.2f}")
        print(f"\n🔍 판단: {result['reason']}")
        print(f"약세장: {'예' if result['hold_cash'] else '아니오'}")
    else:
        print(f"❌ {date_str}의 시장 상태를 가져올 수 없습니다.")
        return False
    
    return True


if __name__ == "__main__":
    print("\n🚀 시장 필터 테스트 시작\n")
    
    # 현재 시장 상태 테스트
    success = test_current_market()
    
    if success:
        print("\n✅ 현재 시장 상태 테스트 완료")
    else:
        print("\n❌ 현재 시장 상태 테스트 실패")
        sys.exit(1)
    
    # 히스토리 테스트 (예시: 2024년 10월 1일)
    print("\n" + "=" * 60)
    print("히스토리 테스트는 필요시 날짜를 지정하여 실행하세요.")
    print("예: test_historical_market('2024-10-01')")
    print("=" * 60)
    
    print("\n✅ 모든 테스트 완료!")


