#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
3개월 역산 백테스팅 실행 스크립트

3개월 전 시점의 대형주/초대형주 상위 10개 종목을 선정하고,
매일 리밸런싱 전략으로 현재까지의 실제 성과를 시뮬레이션합니다.
"""

import sys
import argparse
from pathlib import Path

# src 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from historical_backtest import run_historical_backtest, run_combined_backtest
from telegram_notifier import send_historical_backtest_result
from logger import get_logger
import json

logger = get_logger()

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='3개월 역산 백테스팅')
    parser.add_argument('--screener', type=str, default='combined', 
                       choices=['large', 'mega', 'both', 'combined'],
                       help='스크리너 타입: large, mega, both, combined (기본: combined)')
    parser.add_argument('--capital', type=float, default=10000,
                       help='초기 자본금 (기본: 10000)')
    parser.add_argument('--days', type=int, default=90,
                       help='역산 기간 (일) (기본: 90)')
    parser.add_argument('--large-top', type=int, default=5,
                       help='대형주 상위 N개 (combined 모드에서만, 기본: 5)')
    parser.add_argument('--mega-top', type=int, default=5,
                       help='초대형주 상위 N개 (combined 모드에서만, 기본: 5)')
    parser.add_argument('--no-telegram', action='store_true',
                       help='Telegram 전송 비활성화')
    parser.add_argument('--save-json', type=str, default=None,
                       help='결과를 JSON 파일로 저장 (파일 경로)')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("3개월 역산 백테스팅 시작")
    logger.info("=" * 60)
    logger.info(f"스크리너 타입: {args.screener}")
    logger.info(f"초기 자본: ${args.capital:,.0f}")
    logger.info(f"역산 기간: {args.days}일")
    if args.screener == 'combined':
        logger.info(f"대형주 상위: {args.large_top}개")
        logger.info(f"초대형주 상위: {args.mega_top}개")
    logger.info(f"Telegram 전송: {'비활성화' if args.no_telegram else '활성화'}")
    
    results = {}
    
    # Combined 모드
    if args.screener == 'combined':
        logger.info(f"\n{'='*60}")
        logger.info(f"결합 백테스팅: 대형주 {args.large_top}개 + 초대형주 {args.mega_top}개")
        logger.info(f"{'='*60}\n")
        
        try:
            # 결합 백테스팅 실행
            result = run_combined_backtest(
                initial_capital=args.capital,
                lookback_days=args.days,
                large_top_n=args.large_top,
                mega_top_n=args.mega_top
            )
            
            if result is None:
                logger.error("결합 백테스팅 실패")
            else:
                results['combined'] = result
                
                # 결과 출력
                logger.info("\n" + "="*60)
                logger.info("결합 백테스팅 결과")
                logger.info("="*60)
                
                simulation = result['simulation']
                
                logger.info(f"\n[선정된 종목 (총 {len(result['selection']['combined_tickers'])}개)]")
                logger.info(f"대형주 {args.large_top}개: {', '.join(result['selection']['large']['tickers'])}")
                logger.info(f"초대형주 {args.mega_top}개: {', '.join(result['selection']['mega']['tickers'])}")
                
                logger.info(f"\n[시뮬레이션 결과]")
                logger.info(f"기간: {simulation['start_date']} ~ {simulation['end_date']}")
                logger.info(f"초기 자본: ${simulation['initial_capital']:,.0f}")
                logger.info(f"최종 가치: ${simulation['final_value']:,.0f}")
                logger.info(f"총 수익률: {simulation['total_return']:+.2f}%")
                logger.info(f"연환산 수익률: {simulation['annualized_return']:+.2f}%")
                logger.info(f"최대낙폭 (MDD): {simulation['mdd']:.2f}%")
                logger.info(f"샤프비율: {simulation['sharpe_ratio']:.2f}")
                logger.info(f"승률: {simulation['win_rate']:.2f}%")
                logger.info(f"거래일수: {simulation['trading_days']}일")
                
                logger.info(f"\n[최고/최악의 날]")
                logger.info(f"최고 수익일: {simulation['best_day']['date']} ({simulation['best_day']['return']:+.2f}%)")
                logger.info(f"최악 수익일: {simulation['worst_day']['date']} ({simulation['worst_day']['return']:+.2f}%)")
                
                # Buy & Hold 수익률
                if 'buy_hold_returns' in simulation and simulation['buy_hold_returns']:
                    logger.info(f"\n[개별 종목 Buy & Hold 수익률]")
                    logger.info(f"매수일: {simulation['start_date']}, 현재: {simulation['end_date']}")
                    for i, stock in enumerate(simulation['buy_hold_returns'], 1):
                        logger.info(f"{i:2d}. {stock['ticker']:6s}: ${stock['buy_price']:8.2f} → ${stock['current_price']:8.2f} ({stock['return_pct']:+7.2f}%)")
                    avg_return = sum(s['return_pct'] for s in simulation['buy_hold_returns']) / len(simulation['buy_hold_returns'])
                    logger.info(f"평균 수익률: {avg_return:+.2f}%")
                
                # Telegram 전송
                if not args.no_telegram:
                    logger.info(f"\nTelegram으로 결과 전송 중...")
                    success = send_historical_backtest_result(result)
                    if success:
                        logger.info("✅ Telegram 전송 성공!")
                    else:
                        logger.warning("⚠️ Telegram 전송 실패")
                        
        except Exception as e:
            logger.error(f"결합 백테스팅 중 오류 발생: {e}", exc_info=True)
    
    # Both 또는 개별 모드
    else:
        screener_types = []
        if args.screener == 'both':
            screener_types = ['large', 'mega']
        else:
            screener_types = [args.screener]
        
        for screener_type in screener_types:
            logger.info(f"\n{'='*60}")
            logger.info(f"{'대형주' if screener_type == 'large' else '초대형주'} 백테스팅 시작")
            logger.info(f"{'='*60}\n")
            
            try:
                # 백테스팅 실행
                result = run_historical_backtest(
                    screener_type=screener_type,
                    initial_capital=args.capital,
                    lookback_days=args.days
                )
                
                if result is None:
                    logger.error(f"{screener_type} 백테스팅 실패")
                    continue
                
                results[screener_type] = result
                
                # 결과 출력
                logger.info("\n" + "="*60)
                logger.info(f"{'대형주' if screener_type == 'large' else '초대형주'} 백테스팅 결과")
                logger.info("="*60)
                
                selection = result['selection']
                simulation = result['simulation']
                
                logger.info(f"\n[선정된 종목 (상위 10개)]")
                for i, stock in enumerate(selection['top10_data'], 1):
                    logger.info(f"{i:2d}. {stock['ticker']:6s} - {stock['performance']:+7.2f}%")
                
                logger.info(f"\n[시뮬레이션 결과]")
                logger.info(f"기간: {simulation['start_date']} ~ {simulation['end_date']}")
                logger.info(f"초기 자본: ${simulation['initial_capital']:,.0f}")
                logger.info(f"최종 가치: ${simulation['final_value']:,.0f}")
                logger.info(f"총 수익률: {simulation['total_return']:+.2f}%")
                logger.info(f"연환산 수익률: {simulation['annualized_return']:+.2f}%")
                logger.info(f"최대낙폭 (MDD): {simulation['mdd']:.2f}%")
                logger.info(f"샤프비율: {simulation['sharpe_ratio']:.2f}")
                logger.info(f"승률: {simulation['win_rate']:.2f}%")
                logger.info(f"거래일수: {simulation['trading_days']}일")
                
                logger.info(f"\n[최고/최악의 날]")
                logger.info(f"최고 수익일: {simulation['best_day']['date']} ({simulation['best_day']['return']:+.2f}%)")
                logger.info(f"최악 수익일: {simulation['worst_day']['date']} ({simulation['worst_day']['return']:+.2f}%)")
                
                # Buy & Hold 수익률
                if 'buy_hold_returns' in simulation and simulation['buy_hold_returns']:
                    logger.info(f"\n[개별 종목 Buy & Hold 수익률]")
                    logger.info(f"매수일: {simulation['start_date']}, 현재: {simulation['end_date']}")
                    for i, stock in enumerate(simulation['buy_hold_returns'], 1):
                        logger.info(f"{i:2d}. {stock['ticker']:6s}: ${stock['buy_price']:8.2f} → ${stock['current_price']:8.2f} ({stock['return_pct']:+7.2f}%)")
                    avg_return = sum(s['return_pct'] for s in simulation['buy_hold_returns']) / len(simulation['buy_hold_returns'])
                    logger.info(f"평균 수익률: {avg_return:+.2f}%")
                
                # Telegram 전송
                if not args.no_telegram:
                    logger.info(f"\nTelegram으로 결과 전송 중...")
                    success = send_historical_backtest_result(result)
                    if success:
                        logger.info("✅ Telegram 전송 성공!")
                    else:
                        logger.warning("⚠️ Telegram 전송 실패")
                
            except Exception as e:
                logger.error(f"{screener_type} 백테스팅 중 오류 발생: {e}", exc_info=True)
                continue
    
    # JSON 파일로 저장
    if args.save_json and results:
        try:
            save_path = Path(args.save_json)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"\n결과를 {save_path}에 저장했습니다.")
        except Exception as e:
            logger.error(f"JSON 저장 실패: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("백테스팅 완료")
    logger.info("="*60)
    
    return results

if __name__ == "__main__":
    try:
        results = main()
        
        # 성공 여부 반환
        if results:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        sys.exit(1)

