#!/usr/bin/env python3
"""
알림 채널 테스트 스크립트
"""

import sys
import os

# src 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from slack_notifier import send_test_message
from email_notifier import send_test_email
from discord_notifier import send_test_message as send_test_discord
from config import ENABLE_EMAIL_NOTIFICATIONS, ENABLE_DISCORD_NOTIFICATIONS
from logger import get_logger

logger = get_logger()

def main():
    print("알림 채널 테스트를 시작합니다...")
    
    # Slack 테스트
    print("\n1. Slack 테스트...")
    slack_success = send_test_message()
    if slack_success:
        print("O Slack 연결 테스트 성공!")
    else:
        print("X Slack 연결 테스트 실패!")
        print("config.py에서 SLACK_WEBHOOK_URL을 확인해주세요.")
    
    # 이메일 테스트
    if ENABLE_EMAIL_NOTIFICATIONS:
        print("\n2. 이메일 테스트...")
        email_success = send_test_email()
        if email_success:
            print("O 이메일 연결 테스트 성공!")
        else:
            print("X 이메일 연결 테스트 실패!")
            print("이메일 설정을 확인해주세요.")
    else:
        print("\n2. 이메일 테스트 건너뜀 (비활성화됨)")
        email_success = True
    
    # Discord 테스트
    if ENABLE_DISCORD_NOTIFICATIONS:
        print("\n3. Discord 테스트...")
        discord_success = send_test_discord()
        if discord_success:
            print("O Discord 연결 테스트 성공!")
        else:
            print("X Discord 연결 테스트 실패!")
            print("Discord 웹훅 URL을 확인해주세요.")
    else:
        print("\n3. Discord 테스트 건너뜀 (비활성화됨)")
        discord_success = True
    
    # 전체 결과
    all_success = slack_success and email_success and discord_success
    if all_success:
        print("\n완료! 모든 알림 채널 테스트 성공!")
    else:
        print("\n주의! 일부 알림 채널 테스트 실패!")
    
    return all_success

if __name__ == "__main__":
    main()
