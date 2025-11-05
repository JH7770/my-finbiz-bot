#!/usr/bin/env python3
"""
웹 대시보드 실행 스크립트
"""
import os
import sys
from pathlib import Path

# 현재 디렉토리 확인
current_dir = Path(__file__).parent
os.chdir(current_dir)

# Streamlit 실행
print("=" * 60)
print("Finviz 주식 분석 대시보드 시작")
print("=" * 60)
print()
print("브라우저에서 자동으로 열립니다.")
print("수동으로 접속: http://localhost:8501")
print()
print("종료하려면 Ctrl+C를 누르세요.")
print("=" * 60)
print()

# Streamlit 실행 (Python 모듈로 실행)
os.system(f"{sys.executable} -m streamlit run src/dashboard/app.py")

