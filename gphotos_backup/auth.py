"""
Google OAuth 2.0 認證模組

處理 Google Photos API 的 OAuth 認證流程，包含：
- 首次認證（開啟瀏覽器）
- Token 儲存與載入
- 自動刷新過期的 access token
"""

import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Google Photos API 的唯讀權限
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']


class GoogleAuthManager:
    """Google OAuth 2.0 認證管理器"""
    
    def __init__(self, credentials_dir: str = None):
        """
        初始化認證管理器
        
        Args:
            credentials_dir: 存放認證檔案的目錄路徑
        """
        if credentials_dir is None:
            credentials_dir = Path(__file__).parent.parent / 'credentials'
        self.credentials_dir = Path(credentials_dir)
        self.token_path = self.credentials_dir / 'token.json'
        self.client_secret_path = self.credentials_dir / 'client_secret.json'
        self._credentials = None
    
    def get_credentials(self) -> Credentials:
        """
        取得有效的認證憑證
        
        如果已有有效的 token 則載入，否則執行認證流程。
        如果 token 過期則自動刷新。
        
        Returns:
            有效的 Google OAuth2 憑證
            
        Raises:
            FileNotFoundError: 找不到 client_secret.json
        """
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        # 嘗試載入已存在的 token
        if self.token_path.exists():
            self._credentials = Credentials.from_authorized_user_file(
                str(self.token_path), SCOPES
            )
        
        # 檢查 token 是否有效
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        # 如果 token 過期但有 refresh token，嘗試刷新
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_credentials()
                return self._credentials
            except Exception as e:
                print(f"⚠️  Token 刷新失敗: {e}")
                # 刷新失敗，需要重新認證
                self._credentials = None
        
        # 需要執行完整的認證流程
        self._credentials = self._authenticate()
        return self._credentials
    
    def _authenticate(self) -> Credentials:
        """
        執行 OAuth 認證流程
        
        顯示認證 URL 讓使用者在瀏覽器開啟並授權。
        
        Returns:
            新的 Google OAuth2 憑證
            
        Raises:
            FileNotFoundError: 找不到 client_secret.json
        """
        if not self.client_secret_path.exists():
            raise FileNotFoundError(
                f"❌ 找不到 client_secret.json！\n"
                f"請將 OAuth 憑證檔案放到: {self.client_secret_path}\n\n"
                f"取得方式:\n"
                f"1. 前往 Google Cloud Console (https://console.cloud.google.com/)\n"
                f"2. 啟用 Google Photos Library API\n"
                f"3. 建立 OAuth 2.0 Client ID (桌面應用程式)\n"
                f"4. 下載 JSON 檔案並重新命名為 client_secret.json"
            )
        
        print("🔐 Google 認證")
        print("=" * 50)
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_path), SCOPES
        )
        
        # 使用 console 模式，顯示 URL 讓使用者手動開啟
        flow.run_local_server(
            port=8080,
            prompt='consent',
            open_browser=False,
            authorization_prompt_message='📋 請在瀏覽器開啟以下網址進行認證:\n\n{url}\n',
            success_message='✅ 認證成功！您可以關閉此視窗。'
        )
        
        credentials = flow.credentials
        
        # 儲存 token 以便下次使用
        self._credentials = credentials
        self._save_credentials()
        
        print("✅ 認證成功！Token 已儲存。")
        return credentials
    
    def _save_credentials(self):
        """儲存認證憑證到檔案"""
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.token_path, 'w') as f:
            f.write(self._credentials.to_json())
    
    def revoke(self):
        """撤銷認證（刪除 token）"""
        if self.token_path.exists():
            self.token_path.unlink()
            self._credentials = None
            print("🔓 已撤銷認證，token 已刪除。")
    
    @property
    def is_authenticated(self) -> bool:
        """檢查是否已認證"""
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except FileNotFoundError:
            return False
