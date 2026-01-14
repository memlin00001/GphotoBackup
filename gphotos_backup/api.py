"""
Google Photos API 封裝模組

提供簡化的 Google Photos API 存取介面，包含：
- 列出所有媒體項目
- 依日期範圍篩選
- 取得下載連結
"""

from typing import Generator, Optional, Dict, Any, List
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class GooglePhotosAPI:
    """Google Photos API 封裝類別"""
    
    API_SERVICE_NAME = 'photoslibrary'
    API_VERSION = 'v1'
    
    def __init__(self, credentials: Credentials):
        """
        初始化 API 客戶端
        
        Args:
            credentials: Google OAuth2 憑證
        """
        self.credentials = credentials
        self._service = None
    
    @property
    def service(self):
        """延遲載入 API 服務"""
        if self._service is None:
            self._service = build(
                self.API_SERVICE_NAME,
                self.API_VERSION,
                credentials=self.credentials,
                static_discovery=False
            )
        return self._service
    
    def list_all_media_items(self, page_size: int = 100) -> Generator[Dict[str, Any], None, None]:
        """
        列出所有媒體項目（照片和影片）
        
        使用 Generator 避免記憶體問題，每次 yield 一個媒體項目。
        
        Args:
            page_size: 每次 API 請求的項目數量（最大 100）
            
        Yields:
            媒體項目的字典，包含 id, filename, mimeType, mediaMetadata 等
        """
        page_token = None
        
        while True:
            request_body = {'pageSize': min(page_size, 100)}
            if page_token:
                request_body['pageToken'] = page_token
            
            response = self.service.mediaItems().list(**request_body).execute()
            
            media_items = response.get('mediaItems', [])
            for item in media_items:
                yield item
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
    
    def get_media_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        page_size: int = 100
    ) -> Generator[Dict[str, Any], None, None]:
        """
        依日期範圍篩選媒體項目
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            page_size: 每次 API 請求的項目數量
            
        Yields:
            符合日期範圍的媒體項目
        """
        page_token = None
        
        filters = {
            'dateFilter': {
                'ranges': [{
                    'startDate': {
                        'year': start_date.year,
                        'month': start_date.month,
                        'day': start_date.day
                    },
                    'endDate': {
                        'year': end_date.year,
                        'month': end_date.month,
                        'day': end_date.day
                    }
                }]
            }
        }
        
        while True:
            request_body = {
                'pageSize': min(page_size, 100),
                'filters': filters
            }
            if page_token:
                request_body['pageToken'] = page_token
            
            response = self.service.mediaItems().search(body=request_body).execute()
            
            media_items = response.get('mediaItems', [])
            for item in media_items:
                yield item
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
    
    def get_media_item(self, media_id: str) -> Dict[str, Any]:
        """
        取得單一媒體項目的詳細資訊
        
        Args:
            media_id: 媒體項目 ID
            
        Returns:
            媒體項目的完整資訊
        """
        return self.service.mediaItems().get(mediaItemId=media_id).execute()
    
    @staticmethod
    def get_download_url(media_item: Dict[str, Any], original_quality: bool = True) -> str:
        """
        取得媒體項目的下載連結
        
        注意：baseUrl 只有 60 分鐘有效期
        
        Args:
            media_item: 媒體項目字典（必須包含 baseUrl）
            original_quality: 是否下載原始畫質
            
        Returns:
            可用於下載的 URL
        """
        base_url = media_item.get('baseUrl', '')
        
        if not base_url:
            return ''
        
        # 判斷是照片還是影片
        mime_type = media_item.get('mimeType', '')
        
        if mime_type.startswith('video/'):
            # 影片：使用 =dv 下載原始影片
            return f"{base_url}=dv" if original_quality else base_url
        else:
            # 照片：使用 =d 下載原始照片
            return f"{base_url}=d" if original_quality else base_url
    
    @staticmethod
    def parse_creation_time(media_item: Dict[str, Any]) -> Optional[datetime]:
        """
        解析媒體項目的建立時間
        
        Args:
            media_item: 媒體項目字典
            
        Returns:
            datetime 物件，如果解析失敗則返回 None
        """
        try:
            metadata = media_item.get('mediaMetadata', {})
            creation_time = metadata.get('creationTime', '')
            
            if creation_time:
                # Google Photos API 返回 ISO 8601 格式
                # 例如: "2023-05-15T10:30:00Z"
                return datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
        except Exception:
            pass
        
        return None
    
    def get_albums(self, page_size: int = 50) -> Generator[Dict[str, Any], None, None]:
        """
        列出所有相簿
        
        Args:
            page_size: 每次 API 請求的項目數量
            
        Yields:
            相簿資訊字典
        """
        page_token = None
        
        while True:
            request_body = {'pageSize': min(page_size, 50)}
            if page_token:
                request_body['pageToken'] = page_token
            
            response = self.service.albums().list(**request_body).execute()
            
            albums = response.get('albums', [])
            for album in albums:
                yield album
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
