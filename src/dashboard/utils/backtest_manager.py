"""
백테스팅 결과 관리 모듈
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config import DATA_DIR


class BacktestManager:
    """백테스팅 결과를 관리하는 클래스"""
    
    def __init__(self, cache_dir=None):
        """
        Args:
            cache_dir: 캐시 디렉토리 경로 (기본값: DATA_DIR)
        """
        self.cache_dir = Path(cache_dir or DATA_DIR)
        self.cache_file = self.cache_dir / 'backtest_experiments.json'
        self.favorites_file = self.cache_dir / 'backtest_favorites.json'
        
        # 캐시 파일 초기화
        if not self.cache_file.exists():
            self._save_cache({})
        
        if not self.favorites_file.exists():
            self._save_favorites([])
    
    def _generate_id(self, params):
        """파라미터로부터 고유 ID 생성"""
        # 파라미터를 정렬된 문자열로 변환
        param_str = json.dumps(params, sort_keys=True)
        # 해시 생성
        hash_obj = hashlib.md5(param_str.encode())
        return hash_obj.hexdigest()[:16]
    
    def _load_cache(self):
        """캐시 로드"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_cache(self, cache):
        """캐시 저장"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    
    def _load_favorites(self):
        """즐겨찾기 로드"""
        try:
            with open(self.favorites_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_favorites(self, favorites):
        """즐겨찾기 저장"""
        with open(self.favorites_file, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)
    
    def save_result(self, params, result, label=None):
        """
        백테스팅 결과 저장
        
        Args:
            params: 백테스팅 파라미터 딕셔너리
            result: 백테스팅 결과 딕셔너리
            label: 사용자 정의 라벨 (옵션)
        
        Returns:
            str: 백테스트 ID
        """
        backtest_id = self._generate_id(params)
        
        cache = self._load_cache()
        
        # 결과 저장
        cache[backtest_id] = {
            'id': backtest_id,
            'label': label or f"Backtest {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'params': params,
            'result': result,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'favorite': False
        }
        
        self._save_cache(cache)
        return backtest_id
    
    def get_result(self, backtest_id):
        """
        백테스팅 결과 조회
        
        Args:
            backtest_id: 백테스트 ID
        
        Returns:
            dict: 백테스팅 결과 또는 None
        """
        cache = self._load_cache()
        return cache.get(backtest_id)
    
    def check_cache(self, params):
        """
        파라미터로 캐시 확인
        
        Args:
            params: 백테스팅 파라미터 딕셔너리
        
        Returns:
            dict: 캐시된 결과 또는 None
        """
        backtest_id = self._generate_id(params)
        return self.get_result(backtest_id)
    
    def get_all_results(self, limit=None):
        """
        모든 백테스팅 결과 조회
        
        Args:
            limit: 최대 개수 (최신순)
        
        Returns:
            list: 백테스팅 결과 리스트
        """
        cache = self._load_cache()
        results = list(cache.values())
        
        # 최신순 정렬
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def delete_result(self, backtest_id):
        """
        백테스팅 결과 삭제
        
        Args:
            backtest_id: 백테스트 ID
        
        Returns:
            bool: 삭제 성공 여부
        """
        cache = self._load_cache()
        
        if backtest_id in cache:
            del cache[backtest_id]
            self._save_cache(cache)
            return True
        
        return False
    
    def toggle_favorite(self, backtest_id):
        """
        즐겨찾기 토글
        
        Args:
            backtest_id: 백테스트 ID
        
        Returns:
            bool: 새로운 즐겨찾기 상태
        """
        cache = self._load_cache()
        
        if backtest_id in cache:
            cache[backtest_id]['favorite'] = not cache[backtest_id].get('favorite', False)
            self._save_cache(cache)
            return cache[backtest_id]['favorite']
        
        return False
    
    def get_favorites(self):
        """
        즐겨찾기 결과만 조회
        
        Returns:
            list: 즐겨찾기 백테스팅 결과 리스트
        """
        cache = self._load_cache()
        favorites = [v for v in cache.values() if v.get('favorite', False)]
        
        # 최신순 정렬
        favorites.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return favorites
    
    def clear_old_results(self, keep_count=50):
        """
        오래된 결과 삭제 (즐겨찾기 제외)
        
        Args:
            keep_count: 유지할 개수
        
        Returns:
            int: 삭제된 개수
        """
        cache = self._load_cache()
        
        # 즐겨찾기가 아닌 것만 필터링
        non_favorites = [
            (k, v) for k, v in cache.items()
            if not v.get('favorite', False)
        ]
        
        # 최신순 정렬
        non_favorites.sort(key=lambda x: x[1]['timestamp'], reverse=True)
        
        # 유지할 개수를 초과하는 것만 삭제
        if len(non_favorites) > keep_count:
            to_delete = non_favorites[keep_count:]
            
            for backtest_id, _ in to_delete:
                del cache[backtest_id]
            
            self._save_cache(cache)
            return len(to_delete)
        
        return 0
    
    def update_label(self, backtest_id, label):
        """
        백테스트 라벨 업데이트
        
        Args:
            backtest_id: 백테스트 ID
            label: 새로운 라벨
        
        Returns:
            bool: 업데이트 성공 여부
        """
        cache = self._load_cache()
        
        if backtest_id in cache:
            cache[backtest_id]['label'] = label
            self._save_cache(cache)
            return True
        
        return False
    
    def compare_results(self, backtest_ids):
        """
        여러 백테스팅 결과 비교
        
        Args:
            backtest_ids: 비교할 백테스트 ID 리스트
        
        Returns:
            dict: 비교 데이터
        """
        cache = self._load_cache()
        
        results = []
        for bid in backtest_ids:
            if bid in cache:
                results.append(cache[bid])
        
        if not results:
            return None
        
        # 비교 데이터 생성
        comparison = {
            'results': results,
            'metrics': {
                'total_return': [r['result']['total_return'] for r in results],
                'annualized_return': [r['result']['annualized_return'] for r in results],
                'mdd': [r['result']['mdd'] for r in results],
                'sharpe_ratio': [r['result']['sharpe_ratio'] for r in results],
                'win_rate': [r['result']['win_rate'] for r in results]
            },
            'best_by_sharpe': max(results, key=lambda x: x['result']['sharpe_ratio']),
            'best_by_return': max(results, key=lambda x: x['result']['total_return']),
            'lowest_mdd': min(results, key=lambda x: abs(x['result']['mdd']))
        }
        
        return comparison


# 싱글톤 인스턴스
_manager_instance = None

def get_backtest_manager():
    """백테스트 매니저 싱글톤 인스턴스 반환"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = BacktestManager()
    return _manager_instance

