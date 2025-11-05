#!/usr/bin/env python3
"""
대시보드 실행 준비 확인 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import DATA_DIR

def check_data_availability():
    """데이터 가용성 확인"""
    data_path = Path(DATA_DIR)
    
    print("=" * 60)
    print("대시보드 실행 준비 상태 확인")
    print("=" * 60)
    print()
    
    # 데이터 디렉토리 확인
    if not data_path.exists():
        print("❌ 데이터 디렉토리가 없습니다.")
        print(f"   경로: {data_path}")
        print()
        print("해결방법: python main.py를 먼저 실행하세요.")
        return False
    
    print(f"✅ 데이터 디렉토리 존재: {data_path}")
    print()
    
    # 대형주 데이터 확인
    large_files = sorted(data_path.glob('finviz_data_large_*.csv'))
    if large_files:
        print(f"✅ 대형주 데이터: {len(large_files)}개 파일")
        print(f"   최신: {large_files[-1].name}")
    else:
        print("⚠️  대형주 데이터 없음")
    
    print()
    
    # 초대형주 데이터 확인
    mega_files = sorted(data_path.glob('finviz_data_mega_*.csv'))
    if mega_files:
        print(f"✅ 초대형주 데이터: {len(mega_files)}개 파일")
        print(f"   최신: {mega_files[-1].name}")
    else:
        print("⚠️  초대형주 데이터 없음")
    
    print()
    
    # 백테스팅 캐시 확인
    cache_file = data_path / 'backtest_cache.json'
    if cache_file.exists():
        print("✅ 백테스팅 캐시 존재")
    else:
        print("⚠️  백테스팅 캐시 없음 (선택사항)")
    
    print()
    print("=" * 60)
    
    # 종합 판단
    if large_files or mega_files:
        print("✅ 대시보드 실행 준비 완료!")
        print()
        print("대시보드 실행 명령:")
        print("  streamlit run src/dashboard/app.py")
        print("또는:")
        print("  run_dashboard.bat  (Windows)")
        print("  python run_dashboard.py  (macOS/Linux)")
        print()
        return True
    else:
        print("❌ 데이터가 없습니다!")
        print()
        print("먼저 데이터를 수집하세요:")
        print("  python main.py")
        print()
        return False

def check_dependencies():
    """의존성 확인"""
    print("=" * 60)
    print("필수 패키지 확인")
    print("=" * 60)
    print()
    
    required_packages = [
        ('streamlit', 'Streamlit'),
        ('plotly', 'Plotly'),
        ('pandas', 'Pandas'),
        ('yfinance', 'yfinance')
    ]
    
    all_installed = True
    
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - 설치 필요")
            all_installed = False
    
    print()
    
    if not all_installed:
        print("누락된 패키지를 설치하세요:")
        print("  pip install -r requirements.txt")
        print()
        return False
    
    print("✅ 모든 필수 패키지가 설치되었습니다.")
    print()
    return True

if __name__ == "__main__":
    print()
    
    # 의존성 확인
    deps_ok = check_dependencies()
    
    # 데이터 확인
    data_ok = check_data_availability()
    
    print("=" * 60)
    
    if deps_ok and data_ok:
        print("🎉 모든 준비가 완료되었습니다!")
        print()
        sys.exit(0)
    else:
        print("⚠️  일부 항목을 확인해주세요.")
        print()
        sys.exit(1)


