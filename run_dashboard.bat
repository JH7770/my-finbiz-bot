@echo off
echo ============================================================
echo Finviz 주식 분석 대시보드 시작
echo ============================================================
echo.
echo 브라우저에서 자동으로 열립니다.
echo 수동으로 접속: http://localhost:8501
echo.
echo 종료하려면 Ctrl+C를 누르세요.
echo ============================================================
echo.

python -m streamlit run src/dashboard/app.py

pause

