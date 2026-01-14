"""
照片下載管理器

負責批次下載照片，支援：
- 並行下載
- 進度顯示
- 重試機制
- 檔案重複檢查
"""

import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm

from .api import GooglePhotosAPI


class DownloadError(Exception):
    """下載錯誤"""
    pass


class PhotoDownloader:
    """照片下載管理器"""
    
    def __init__(
        self, 
        api: GooglePhotosAPI,
        download_dir: str = None,
        max_workers: int = 4,
        timeout: int = 60
    ):
        """
        初始化下載管理器
        
        Args:
            api: GooglePhotosAPI 實例
            download_dir: 下載暫存目錄
            max_workers: 並行下載的最大執行緒數
            timeout: 下載超時時間（秒）
        """
        self.api = api
        if download_dir is None:
            download_dir = Path(__file__).parent.parent / 'downloads'
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.timeout = timeout
        
        # 統計資訊
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_bytes': 0
        }
    
    def download_single(
        self, 
        media_item: Dict[str, Any],
        dest_path: Optional[Path] = None,
        retries: int = 3
    ) -> Optional[Path]:
        """
        下載單一媒體項目
        
        Args:
            media_item: 媒體項目字典
            dest_path: 目標檔案路徑（如果為 None 則自動生成）
            retries: 重試次數
            
        Returns:
            下載成功的檔案路徑，失敗則返回 None
        """
        if dest_path is None:
            filename = media_item.get('filename', f"{media_item['id']}.jpg")
            dest_path = self.download_dir / filename
        
        # 檢查檔案是否已存在
        if dest_path.exists():
            self.stats['skipped'] += 1
            return dest_path
        
        download_url = GooglePhotosAPI.get_download_url(media_item)
        if not download_url:
            return None
        
        for attempt in range(retries):
            try:
                response = requests.get(download_url, timeout=self.timeout, stream=True)
                response.raise_for_status()
                
                # 確保父目錄存在
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 寫入檔案
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = dest_path.stat().st_size
                self.stats['success'] += 1
                self.stats['total_bytes'] += file_size
                
                return dest_path
                
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                    continue
                else:
                    self.stats['failed'] += 1
                    return None
            except Exception as e:
                self.stats['failed'] += 1
                return None
        
        return None
    
    def download_batch(
        self, 
        media_items: List[Dict[str, Any]],
        dest_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        批次下載多個媒體項目
        
        Args:
            media_items: 媒體項目列表
            dest_dir: 目標目錄
            progress_callback: 進度回調函數 (當前數量, 總數)
            show_progress: 是否顯示進度條
            
        Returns:
            下載結果統計
        """
        if dest_dir is None:
            dest_dir = self.download_dir
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        total = len(media_items)
        
        # 重置統計
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_bytes': 0
        }
        
        # 使用 tqdm 顯示進度
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(
                total=total,
                desc="📥 下載中",
                unit="張",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )
        
        def download_with_path(item):
            filename = item.get('filename', f"{item['id']}.jpg")
            dest_path = dest_dir / filename
            return self.download_single(item, dest_path)
        
        completed = 0
        
        # 使用執行緒池並行下載
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(download_with_path, item): item 
                for item in media_items
            }
            
            for future in as_completed(futures):
                completed += 1
                
                if progress_bar:
                    progress_bar.update(1)
                
                if progress_callback:
                    progress_callback(completed, total)
        
        if progress_bar:
            progress_bar.close()
        
        return {
            'total': total,
            'success': self.stats['success'],
            'failed': self.stats['failed'],
            'skipped': self.stats['skipped'],
            'total_bytes': self.stats['total_bytes']
        }
    
    def clear_download_dir(self):
        """清空下載暫存目錄"""
        for f in self.download_dir.iterdir():
            if f.is_file() and f.name != '.gitkeep':
                f.unlink()
    
    @staticmethod
    def format_bytes(size: int) -> str:
        """格式化位元組大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
