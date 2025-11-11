#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
백테스팅 비교: 기존 vs 개선된 버전

이 스크립트는 두 가지 백테스팅 방법을 비교합니다:
1. 기존 방식: Look-Ahead Bias 있음, 거래 비용 없음
2. 개선 방식: Look-Ahead Bias 제거, 거래 비용 반영
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from historical_backtest import run_historical_backtest
from realistic_backtest import run_realistic_backtest
from logger import get_logger
from telegram_notifier import send_to_telegram

logger = get_logger()


def create_comparison_message(old_result, new_result):
    """비교 결과 메시지 생성"""
    message = "📊 *백테스팅 비교 결과*\n"
    message += "_(기존 vs 개선 버전)_\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 기존 방식
    if old_result and 'simulation' in old_result:
        old_sim = old_result['simulation']
        message += "🔴 *기존 방식*\n"
        message += "• Look-Ahead Bias 있음\n"
        message += "• 거래 비용 없음\n\n"
        message += f"📈 총 수익률: {old_sim['total_return']:+.2f}%\n"
        message += f"📈 연환산: {old_sim['annualized_return']:+.2f}%\n"
        message += f"📉 MDD: {old_sim['mdd']:.2f}%\n"
        message += f"⚡ 샤프비율: {old_sim['sharpe_ratio']:.2f}\n"
        message += f"🎯 승률: {old_sim['win_rate']:.2f}%\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 개선 방식
    if new_result and 'simulation' in new_result:
        new_sim = new_result['simulation']
        message += "🟢 *개선 방식*\n"
        message += "• Look-Ahead Bias 제거\n"
        message += f"• 거래 비용: {new_sim['transaction_cost_pct']:.2f}%\n\n"
        message += f"📈 총 수익률: {new_sim['total_return']:+.2f}%\n"
        message += f"📈 연환산: {new_sim['annualized_return']:+.2f}%\n"
        message += f"📉 MDD: {new_sim['mdd']:.2f}%\n"
        message += f"⚡ 샤프비율: {new_sim['sharpe_ratio']:.2f}\n"
        message += f"🎯 승률: {new_sim['win_rate']:.2f}%\n\n"
        
        message += f"💸 *거래 비용 분석*\n"
        message += f"• 총 비용: ${new_sim['total_transaction_costs']:.2f}\n"
        message += f"• 거래 횟수: {new_sim['total_trades']}회\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 차이 분석
    if old_result and new_result and 'simulation' in old_result and 'simulation' in new_result:
        old_sim = old_result['simulation']
        new_sim = new_result['simulation']
        
        return_diff = new_sim['total_return'] - old_sim['total_return']
        sharpe_diff = new_sim['sharpe_ratio'] - old_sim['sharpe_ratio']
        
        message += "📊 *차이 분석*\n"
        message += f"• 수익률 차이: {return_diff:+.2f}%p\n"
        message += f"• 샤프비율 차이: {sharpe_diff:+.2f}\n\n"
        
        if return_diff < 0:
            diff_pct = (abs(return_diff) / old_sim['total_return'] * 100) if old_sim['total_return'] != 0 else 0
            message += f"⚠️ 개선 버전의 수익률이 {abs(return_diff):.2f}%p 낮습니다.\n"
            message += f"(기존 대비 {diff_pct:.1f}% 감소)\n\n"
            message += "💡 이것이 *현실적인* 수익률입니다!\n"
        else:
            message += f"✅ 개선 버전이 {return_diff:.2f}%p 높습니다.\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "💡 *결론*\n"
    message += "• 기존 방식: 과도하게 낙관적\n"
    message += "• 개선 방식: 실제 투자에 가까움\n"
    message += "• 실전 투자는 개선 버전 기준으로 판단!\n"
    
    return message


def main():
    """메인 실행 함수"""
    logger.info("="*60)
    logger.info("백테스팅 비교 분석 시작")
    logger.info("="*60)
    
    # 테스트 설정
    test_months = 3
    initial_capital = 10000
    screener_type = "large"
    
    results = {}
    
    # 1. 기존 방식 백테스팅
    logger.info("\n" + "="*60)
    logger.info("1. 기존 방식 백테스팅 (Look-Ahead Bias 있음)")
    logger.info("="*60)
    
    try:
        old_result = run_historical_backtest(
            screener_type=screener_type,
            initial_capital=initial_capital,
            lookback_days=test_months * 30,
            top_n=10
        )
        
        if old_result:
            results['old'] = old_result
            logger.info("✅ 기존 방식 백테스팅 완료")
        else:
            logger.error("❌ 기존 방식 백테스팅 실패")
    except Exception as e:
        logger.error(f"기존 방식 백테스팅 중 오류: {e}", exc_info=True)
    
    # 2. 개선된 방식 백테스팅
    logger.info("\n" + "="*60)
    logger.info("2. 개선된 방식 백테스팅 (Look-Ahead Bias 제거 + 거래비용)")
    logger.info("="*60)
    
    try:
        new_result = run_realistic_backtest(
            screener_type=screener_type,
            initial_capital=initial_capital,
            test_period_months=test_months,
            lookback_months=3,
            lag_months=1,
            rebalance_frequency='monthly'
        )
        
        if new_result:
            results['new'] = new_result
            logger.info("✅ 개선된 방식 백테스팅 완료")
        else:
            logger.error("❌ 개선된 방식 백테스팅 실패")
    except Exception as e:
        logger.error(f"개선된 방식 백테스팅 중 오류: {e}", exc_info=True)
    
    # 3. 결과 비교
    logger.info("\n" + "="*60)
    logger.info("3. 결과 비교")
    logger.info("="*60)
    
    if 'old' in results and 'new' in results:
        old_sim = results['old']['simulation']
        new_sim = results['new']['simulation']
        
        logger.info("\n📊 [기존 방식 - Look-Ahead Bias 있음]")
        logger.info(f"총 수익률: {old_sim['total_return']:+.2f}%")
        logger.info(f"연환산 수익률: {old_sim['annualized_return']:+.2f}%")
        logger.info(f"MDD: {old_sim['mdd']:.2f}%")
        logger.info(f"샤프비율: {old_sim['sharpe_ratio']:.2f}")
        logger.info(f"승률: {old_sim['win_rate']:.2f}%")
        
        logger.info("\n📊 [개선 방식 - Look-Ahead Bias 제거 + 거래비용]")
        logger.info(f"총 수익률: {new_sim['total_return']:+.2f}%")
        logger.info(f"연환산 수익률: {new_sim['annualized_return']:+.2f}%")
        logger.info(f"MDD: {new_sim['mdd']:.2f}%")
        logger.info(f"샤프비율: {new_sim['sharpe_ratio']:.2f}")
        logger.info(f"승률: {new_sim['win_rate']:.2f}%")
        logger.info(f"거래 비용: ${new_sim['total_transaction_costs']:.2f} ({new_sim['transaction_cost_pct']:.2f}%)")
        
        logger.info("\n📊 [차이 분석]")
        return_diff = new_sim['total_return'] - old_sim['total_return']
        ann_return_diff = new_sim['annualized_return'] - old_sim['annualized_return']
        sharpe_diff = new_sim['sharpe_ratio'] - old_sim['sharpe_ratio']
        
        logger.info(f"수익률 차이: {return_diff:+.2f}%p")
        logger.info(f"연환산 수익률 차이: {ann_return_diff:+.2f}%p")
        logger.info(f"샤프비율 차이: {sharpe_diff:+.2f}")
        
        if return_diff < 0:
            diff_pct = (abs(return_diff) / old_sim['total_return'] * 100) if old_sim['total_return'] != 0 else 0
            logger.info(f"\n⚠️ 개선 버전이 {abs(return_diff):.2f}%p 낮습니다 (기존 대비 {diff_pct:.1f}% 감소)")
            logger.info(f"💡 이것이 실제 투자 시 예상되는 현실적인 수익률입니다!")
        else:
            logger.info(f"\n✅ 개선 버전이 {return_diff:.2f}%p 높습니다")
        
        # Telegram 전송
        logger.info(f"\nTelegram으로 비교 결과 전송 중...")
        try:
            message = create_comparison_message(results['old'], results['new'])
            success = send_to_telegram(message)
            if success:
                logger.info("✅ Telegram 전송 성공!")
            else:
                logger.warning("⚠️ Telegram 전송 실패")
        except Exception as e:
            logger.error(f"Telegram 전송 중 오류: {e}")
        
        # JSON 저장
        output_path = Path('daily_data') / 'backtest_comparison.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'comparison_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'old_method': results['old'],
                'new_method': results['new'],
                'differences': {
                    'total_return_diff': return_diff,
                    'annualized_return_diff': ann_return_diff,
                    'sharpe_diff': sharpe_diff
                }
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"\n비교 결과 저장: {output_path}")
    
    else:
        logger.error("비교할 결과가 충분하지 않습니다.")
    
    logger.info("\n" + "="*60)
    logger.info("백테스팅 비교 분석 완료")
    logger.info("="*60)
    
    return results


if __name__ == "__main__":
    try:
        results = main()
        
        if results and 'old' in results and 'new' in results:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        sys.exit(1)

