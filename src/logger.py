# 통합 로깅 모듈
import os
import logging
from datetime import datetime
from config import DATA_DIR

def setup_logger(name="finviz_daily_report", level=None):
    """로거 설정"""
    # 환경변수에서 로그 레벨 가져오기
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # 디버그 모드 확인
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # 로그 레벨 설정
    log_level = getattr(logging, level, logging.INFO)
    if debug_mode:
        log_level = logging.DEBUG
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 이미 핸들러가 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (로그 디렉토리 생성)
    log_dir = os.path.join(DATA_DIR, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일명 (날짜별)
    log_filename = os.path.join(log_dir, f"finviz_report_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def get_logger(name="finviz_daily_report"):
    """기존 로거 가져오기 또는 새로 생성"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger

# 기본 로거 인스턴스
logger = get_logger()

