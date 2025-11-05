#!/usr/bin/env python3
"""
Telegram 연결 테스트 스크립트
"""

import sys
import os

# src 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from telegram_notifier import send_test_message

if __name__ == "__main__":
    print("Telegram 연결 테스트 중...")
    success = send_test_message()
    
    if success:
        print("✅ 테스트 성공! Telegram으로 메시지를 확인하세요.")
    else:
        print("❌ 테스트 실패! config.py에서 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 확인하세요.")
        print("\n=== Telegram Bot 설정 방법 ===")
        print("1. Telegram에서 @BotFather와 대화")
        print("2. /newbot 명령어로 새 봇 생성")
        print("3. Bot Token 복사")
        print("4. 생성한 봇과 대화 시작 (메시지 보내기)")
        print("5. https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates 접속하여 Chat ID 확인")
        print("6. config.py 또는 환경변수에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 설정")
    
    sys.exit(0 if success else 1)

