# Google Photos 備份服務

將 Google 相簿的照片和影片備份到本地電腦，並依年月自動分類整理。

## 功能特色

- 🔐 **Google OAuth 認證** - 安全地連接您的 Google 帳號
- 📊 **年月統計** - 顯示照片依年月分類的統計表
- 📥 **批次下載** - 並行下載，顯示即時進度
- 📁 **自動整理** - 下載後自動整理到 `YYYY/MM/` 目錄結構

## 前置準備

### 1. 設定 Google Cloud Console

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 前往「API 和服務」→「資料庫」
4. 搜尋並啟用 **Google Photos Library API**
5. 前往「API 和服務」→「憑證」
6. 點擊「建立憑證」→「OAuth 用戶端 ID」
7. 應用程式類型選擇「**桌面應用程式**」
8. 下載 JSON 檔案，重新命名為 `client_secret.json`
9. 將 `client_secret.json` 放到 `credentials/` 目錄

### 2. 安裝依賴

```bash
cd /home/ives/Documents/GphotoBackup

# 如果沒有 pip，請先安裝
# Ubuntu/Debian:
sudo apt install python3-pip

# 安裝專案依賴
pip3 install -r requirements.txt
```

## 使用方式

### 完整備份流程

```bash
python main.py
```

程式會：
1. 開啟瀏覽器進行 Google 登入授權
2. 獲取所有照片並顯示年月統計
3. 等待您確認後開始下載
4. 自動整理到 `backup/YYYY/MM/` 目錄

### 其他選項

```bash
# 只執行認證（測試 OAuth 設定）
python main.py --auth-only

# 只顯示照片統計（不下載）
python main.py --list-only

# 指定備份目錄
python main.py --dest /path/to/backup

# 調整並行下載數（預設 4）
python main.py --workers 8
```

## 目錄結構

```
GphotoBackup/
├── gphotos_backup/       # 程式模組
│   ├── auth.py           # OAuth 認證
│   ├── api.py            # API 封裝
│   ├── downloader.py     # 下載管理
│   └── organizer.py      # 照片整理
├── credentials/          # 認證檔案
│   └── client_secret.json  ← 放這裡
├── downloads/            # 下載暫存
├── backup/               # 備份目錄
│   ├── 2024/
│   │   ├── 01/
│   │   ├── 02/
│   │   └── ...
│   └── unknown/          # 無法識別日期的照片
├── main.py               # 主程式
└── requirements.txt      # 依賴清單
```

## 注意事項

⚠️ **API 限制**
- Google Photos API 的下載連結有效期為 60 分鐘
- 影片可能會被轉檔，無法保證原始畫質
- 部分 RAW 格式照片可能被轉換

⚠️ **首次使用**
- 首次登入時，Google 可能會顯示「這個應用程式未經驗證」的警告
- 點擊「進階」→「前往 (您的專案名稱)」即可繼續

## 授權

MIT License
