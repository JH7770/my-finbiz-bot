# pip install schedule
import schedule
import time
import subprocess
import sys
from datetime import datetime

def run_daily_report():
    """매일 아침 9시에 실행되는 일일 보고서"""
    print(f"=== 일일 보고서 실행 시작 - {datetime.now()} ===")
    
    try:
        # main.py 실행
        result = subprocess.run([sys.executable, "main.py"], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("일일 보고서 실행 성공!")
            print("출력:")
            print(result.stdout)
        else:
            print("일일 보고서 실행 실패!")
            print("에러:")
            print(result.stderr)
            
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")

def main():
    print("Finviz 일일 보고서 스케줄러 시작")
    print("매일 오전 9시에 실행됩니다.")
    
    # 매일 오전 9시에 실행
    schedule.every().day.at("09:00").do(run_daily_report)
    
    # 테스트용: 1분 후 실행 (개발 시 사용)
    # schedule.every().minute.do(run_daily_report)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    main()
