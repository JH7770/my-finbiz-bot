#!/usr/bin/env python3
"""
Finviz Daily Report - 메인 실행 파일
매일 아침마다 Finviz 대형주 3개월 수익률 상위 10개 종목을 분석하고 Telegram으로 보고
"""

import sys
import os
from datetime import datetime

# src 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from finviz_scraper import scrape_finviz_screener
from data_manager import save_daily_data, load_previous_data, load_last_business_day_data
from analyzer import compare_data, get_top_performers, calculate_portfolio_allocation, calculate_summary_stats
from telegram_notifier import create_telegram_message, send_to_telegram
from email_notifier import create_email_message, send_email
from discord_notifier import create_discord_message, send_to_discord
from technical_analyzer import analyze_top10_technical, load_technical_snapshot
from backtester import run_backtest
from config import (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM_NOTIFICATIONS, 
                    ENABLE_EMAIL_NOTIFICATIONS, ENABLE_DISCORD_NOTIFICATIONS, ENABLE_BACKTESTING,
                    FINVIZ_URL_LARGE, FINVIZ_URL_MEGA, SCREENER_TYPES, ENABLE_MARKET_FILTER,
                    DATA_DIR)
from logger import get_logger

# 로거 초기화
logger = get_logger()

def process_screener(screener_type, today):
    """
    특정 스크리너 타입의 데이터를 처리
    
    Args:
        screener_type: 'large' 또는 'mega'
        today: 현재 날짜 문자열
    
    Returns:
        bool: 성공 여부
    """
    screener_name = "대형주" if screener_type == "large" else "초대형주"
    screener_url = FINVIZ_URL_LARGE if screener_type == "large" else FINVIZ_URL_MEGA
    
    logger.info(f"=== Finviz {screener_name} 3개월 수익률 분석 시작 - {today} ===")
    
    try:
        # 1) 데이터 수집
        logger.info("1. 데이터 수집 중...")
        df = scrape_finviz_screener(screener_url)
        if df is None:
            logger.error(f"{screener_name} 데이터 수집에 실패했습니다.")
            return False
        
        logger.info(f"{screener_name} 데이터를 성공적으로 가져왔습니다.")
        
        # 2) 현재 데이터 저장 (파일명에 screener_type 포함)
        logger.info("2. 데이터 저장 중...")
        filename = f"finviz_data_{screener_type}_{today}.csv"
        save_daily_data(df, today, filename_prefix=f"{screener_type}_")
        
        # 3) 이전 데이터 로드 및 비교
        logger.info("3. 이전 데이터 분석 중...")
        # 영업일 기준으로 전날 데이터 로드 (주말/월요일은 금요일 데이터)
        yesterday_df, yesterday_date = load_last_business_day_data(
            filename_prefix=f"{screener_type}_", return_date=True
        )
        week_ago_df = load_previous_data(7, filename_prefix=f"{screener_type}_")  # 7일 전
        
        # 4) 비교 분석
        yesterday_analysis = None
        week_analysis = None
        
        if yesterday_df is not None:
            yesterday_analysis = compare_data(df, yesterday_df, "전날")
            logger.info("전날 대비 분석 완료")
        
        if week_ago_df is not None:
            week_analysis = compare_data(df, week_ago_df, "일주일 전")
            logger.info("일주일 전 대비 분석 완료")
        
        # 5) 현재 상위 5개 출력
        logger.info(f"=== {screener_name} 3개월 수익률 상위 5개 종목 ===")
        top10 = get_top_performers(df, 5)
        print(top10)
        
        # 6) 요약 통계 출력
        stats = calculate_summary_stats(df)
        logger.info(f"평균 수익률: {stats['avg_performance']:.1f}%")
        logger.info(f"최고 수익률: {stats['max_performance']:.1f}%")
        
        # 7) 포트폴리오 할당 계산
        alloc = calculate_portfolio_allocation(len(top10))
        logger.info(f"동일비중 할당: {alloc:.1%} (각 종목당)")
        
        # 8) 기술적 분석 (이동평균선)
        logger.info("4. 기술적 분석 중...")
        technical_analysis = None
        technical_snapshot = None
        previous_technical_analysis = None
        previous_snapshot = None
        ma60_breaks = []
        trailing_stops = []
        breakout_highs = []

        try:
            technical_dir = os.path.join(DATA_DIR, 'technical')
            technical_result = analyze_top10_technical(
                df,
                as_of_date=today,
                screener_type=screener_type,
                output_dir=technical_dir,
                return_snapshot=True,
            )
            if isinstance(technical_result, tuple):
                technical_analysis, technical_snapshot = technical_result
            else:
                technical_analysis = technical_result
            logger.info("기술적 분석 완료")

            # 전날 데이터가 있으면 전날 기술적 분석도 수행하여 MA60 이탈 감지
            if yesterday_date:
                from technical_analyzer import detect_ma60_breaks

                previous_snapshot = load_technical_snapshot(
                    screener_type,
                    yesterday_date,
                    base_dir=technical_dir,
                )

                if previous_snapshot:
                    previous_technical_analysis = previous_snapshot
                elif yesterday_df is not None:
                    logger.warning(
                        f"전날({yesterday_date}) 기술 분석 스냅샷을 찾을 수 없습니다. 즉시 재계산합니다."
                    )
                    previous_technical_analysis = analyze_top10_technical(yesterday_df)
                else:
                    logger.warning(
                        f"전날({yesterday_date}) 기술 분석 스냅샷을 찾을 수 없고 원본 데이터도 없습니다."
                    )

                if previous_technical_analysis:
                    ma60_breaks = detect_ma60_breaks(
                        technical_snapshot or technical_analysis,
                        previous_technical_analysis,
                    )

                    if ma60_breaks:
                        logger.warning(f"⚠️ MA60 이탈 종목 {len(ma60_breaks)}개 감지!")
                    else:
                        logger.info("MA60 이탈 종목 없음")

            # 신고가 돌파 감지 (3개월 최고가 경신)
            from technical_analyzer import detect_trailing_stops, detect_breakout_highs
            breakout_highs = detect_breakout_highs(df)
            
            # 트레일링 스탑 감지 (MA20 2일 이상 하향 이탈)
            if previous_technical_analysis is not None:
                trailing_stops = detect_trailing_stops(
                    technical_snapshot or technical_analysis,
                    previous_technical_analysis,
                )
            else:
                logger.warning("전날 기술 분석 데이터 없음: 트레일링 스탑 분석 스킵")
            
        except Exception as e:
            logger.error(f"기술적 분석 실패: {e}", exc_info=True)
            logger.warning("기술적 분석 없이 계속 진행합니다.")
        
        # 9) 시장 필터 체크
        logger.info("5. 시장 상태 분석 중...")
        market_regime = None
        if ENABLE_MARKET_FILTER:
            try:
                from market_filter import check_market_regime
                market_regime = check_market_regime()
                if market_regime:
                    if market_regime.get('hold_cash', False):
                        logger.warning(f"⚠️ 약세장 감지: {market_regime.get('reason', '')}")
                    else:
                        logger.info(f"✅ 강세장: {market_regime.get('reason', '')}")
            except Exception as e:
                logger.error(f"시장 필터 체크 실패: {e}", exc_info=True)
                logger.warning("시장 필터 없이 계속 진행합니다.")
        else:
            logger.info("시장 필터가 비활성화되어 있습니다.")
        
        # 10) 백테스팅 (매일 리밸런싱)
        logger.info("6. 백테스팅 수행 중...")
        backtest_result = None
        if ENABLE_BACKTESTING:
            try:
                backtest_result = run_backtest(screener_type=screener_type)
                logger.info("백테스팅 완료")
            except Exception as e:
                logger.error(f"백테스팅 실패: {e}", exc_info=True)
                logger.warning("백테스팅 없이 계속 진행합니다.")
        else:
            logger.info("백테스팅이 비활성화되어 있습니다.")
        
        # 11) 알림 메시지 생성 및 전송
        logger.info("7. 알림 메시지 전송 중...")
        
        # Telegram 메시지
        if ENABLE_TELEGRAM_NOTIFICATIONS:
            if TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE" and TELEGRAM_CHAT_ID != "YOUR_TELEGRAM_CHAT_ID_HERE":
                telegram_message = create_telegram_message(
                    df, yesterday_analysis, week_analysis, 
                    technical_analysis,
                    screener_name=screener_name,
                    ma60_breaks=ma60_breaks,
                    trailing_stops=trailing_stops,
                    market_regime=market_regime
                )
                success = send_to_telegram(telegram_message, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                if success:
                    logger.info(f"{screener_name} Telegram 메시지 전송 완료")
                else:
                    logger.error(f"{screener_name} Telegram 메시지 전송 실패")
            else:
                logger.warning("Telegram Bot Token 또는 Chat ID를 설정해주세요.")
        
        # 이메일 메시지
        if ENABLE_EMAIL_NOTIFICATIONS:
            email_content = create_email_message(df, yesterday_analysis, week_analysis)
            if email_content:
                success = send_email(email_content)
                if success:
                    logger.info("이메일 전송 완료")
                else:
                    logger.error("이메일 전송 실패")
        
        # Discord 메시지
        if ENABLE_DISCORD_NOTIFICATIONS:
            discord_message = create_discord_message(df, yesterday_analysis, week_analysis)
            if discord_message:
                success = send_to_discord(discord_message)
                if success:
                    logger.info("Discord 메시지 전송 완료")
                else:
                    logger.error("Discord 메시지 전송 실패")
        
        # 디버그 모드에서만 콘솔 출력
        if os.getenv('DEBUG', 'False').lower() == 'true':
            try:
                print("\n=== 메시지 내용 (디버그) ===")
                telegram_message = create_telegram_message(
                    df, yesterday_analysis, week_analysis, 
                    technical_analysis,
                    screener_name=screener_name,
                    ma60_breaks=ma60_breaks,
                    trailing_stops=trailing_stops,
                    breakout_highs=breakout_highs,
                    market_regime=market_regime
                )
                # Windows 콘솔 인코딩 문제 해결
                print(telegram_message.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore'))
            except Exception as e:
                logger.warning(f"디버그 메시지 출력 실패 (인코딩 문제): {e}")
        
        logger.info(f"완료! {screener_name} 일일 보고서 완료 - {today}")
        return True
        
    except Exception as e:
        logger.error(f"{screener_name} 실행 중 오류 발생: {e}", exc_info=True)
        
        # 에러 발생 시 Telegram으로 알림
        if ENABLE_TELEGRAM_NOTIFICATIONS and TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE" and TELEGRAM_CHAT_ID != "YOUR_TELEGRAM_CHAT_ID_HERE":
            error_message = f"❌ *Finviz {screener_name} Report 오류 발생*\n\n"
            error_message += f"*날짜:* {today}\n"
            error_message += f"*오류:* {str(e)}\n"
            error_message += f"*시간:* {datetime.now().strftime('%H:%M:%S')}"
            
            send_to_telegram(error_message, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        
        return False

def main():
    """메인 실행 함수"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_weekday = datetime.now().weekday()  # 0=월, 1=화, ..., 5=토, 6=일
    
    # 주말과 월요일에 대한 메시지
    if today_weekday == 5:  # 토요일
        logger.info("토요일입니다. 금요일 종가 기준으로 분석을 실행합니다.")
    elif today_weekday == 6:  # 일요일
        logger.info("일요일입니다. 금요일 종가 기준으로 분석을 실행합니다.")
    elif today_weekday == 0:  # 월요일
        logger.info("월요일입니다. 금요일 종가와 비교하여 분석합니다.")
    
    success_count = 0
    total_count = 0
    
    # 분석할 스크리너 타입 결정
    screeners_to_process = []
    if SCREENER_TYPES == 'both':
        screeners_to_process = ['large', 'mega']
    elif SCREENER_TYPES == 'large':
        screeners_to_process = ['large']
    elif SCREENER_TYPES == 'mega':
        screeners_to_process = ['mega']
    else:
        logger.error(f"잘못된 SCREENER_TYPES 설정: {SCREENER_TYPES}")
        return False
    
    # 각 스크리너 타입별로 처리
    for screener_type in screeners_to_process:
        total_count += 1
        if process_screener(screener_type, today):
            success_count += 1
        
        # 다음 스크리너 처리 전 약간의 지연
        if len(screeners_to_process) > 1 and screener_type != screeners_to_process[-1]:
            import time
            logger.info("다음 스크리너 처리를 위해 5초 대기...")
            time.sleep(5)
    
    logger.info(f"=== 전체 완료: {success_count}/{total_count} 성공 ===")
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
