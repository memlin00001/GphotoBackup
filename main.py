#!/usr/bin/env python3
"""
Google Photos 備份服務

主程式入口，提供命令列介面來備份 Google 相簿。

使用方式:
    python main.py              # 完整備份流程
    python main.py --auth-only  # 只執行認證
    python main.py --list-only  # 只顯示照片統計
    python main.py --dest /path # 指定備份目錄
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from gphotos_backup.auth import GoogleAuthManager
from gphotos_backup.api import GooglePhotosAPI
from gphotos_backup.downloader import PhotoDownloader
from gphotos_backup.organizer import PhotoOrganizer


console = Console()


def show_welcome():
    """顯示歡迎訊息"""
    welcome_text = """
[bold cyan]Google Photos 備份服務[/bold cyan]

此工具將協助您：
1. 🔐 連接 Google 帳號
2. 📊 顯示照片統計（依年月分類）
3. 📥 下載所有照片/影片
4. 📁 自動整理到備份目錄
    """
    console.print(Panel(welcome_text.strip(), border_style="cyan"))


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description='Google Photos 備份服務',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--auth-only',
        action='store_true',
        help='只執行認證，不下載照片'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='只顯示照片統計，不下載'
    )
    parser.add_argument(
        '--dest',
        type=str,
        default=None,
        help='備份目標目錄（預設為 ./backup）'
    )
    parser.add_argument(
        '--credentials-dir',
        type=str,
        default=None,
        help='認證檔案目錄（預設為 ./credentials）'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='並行下載的執行緒數（預設為 4）'
    )
    
    args = parser.parse_args()
    
    # 設定路徑
    base_dir = Path(__file__).parent
    credentials_dir = Path(args.credentials_dir) if args.credentials_dir else base_dir / 'credentials'
    backup_dir = Path(args.dest) if args.dest else base_dir / 'backup'
    download_dir = base_dir / 'downloads'
    
    # 顯示歡迎訊息
    show_welcome()
    
    # 步驟 1: OAuth 認證
    console.print("\n[bold]步驟 1/4: Google 認證[/bold]")
    console.print("─" * 40)
    
    try:
        auth_manager = GoogleAuthManager(credentials_dir)
        credentials = auth_manager.get_credentials()
        console.print("[green]✅ 認證成功！[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ 認證失敗: {e}[/red]")
        sys.exit(1)
    
    if args.auth_only:
        console.print("\n[dim]--auth-only 模式，認證完成後結束。[/dim]")
        return
    
    # 步驟 2: 獲取照片列表
    console.print("\n[bold]步驟 2/4: 獲取照片列表[/bold]")
    console.print("─" * 40)
    
    api = GooglePhotosAPI(credentials)
    
    console.print("📡 正在從 Google Photos 獲取資料...")
    console.print("[dim]（這可能需要一些時間，取決於您的照片數量）[/dim]")
    
    # 收集所有媒體項目
    media_items = []
    try:
        for item in api.list_all_media_items():
            media_items.append(item)
            if len(media_items) % 100 == 0:
                console.print(f"[dim]已獲取 {len(media_items)} 張...[/dim]", end="\r")
        
        console.print(f"[green]✅ 共獲取 {len(media_items)} 張照片/影片[/green]")
    except Exception as e:
        console.print(f"[red]❌ 獲取照片列表失敗: {e}[/red]")
        sys.exit(1)
    
    if not media_items:
        console.print("[yellow]⚠️  您的 Google Photos 中沒有照片。[/yellow]")
        return
    
    # 步驟 3: 分類與統計
    console.print("\n[bold]步驟 3/4: 依年月分類[/bold]")
    console.print("─" * 40)
    
    organizer = PhotoOrganizer(backup_dir)
    organizer.categorize_by_date(media_items)
    organizer.display_summary()
    
    if args.list_only:
        console.print("\n[dim]--list-only 模式，顯示統計後結束。[/dim]")
        return
    
    # 確認是否開始下載
    console.print()
    if not Confirm.ask("🤔 是否開始備份？", default=True):
        console.print("[yellow]已取消備份。[/yellow]")
        return
    
    # 步驟 4: 下載與整理
    console.print("\n[bold]步驟 4/4: 下載與整理[/bold]")
    console.print("─" * 40)
    
    downloader = PhotoDownloader(
        api=api,
        download_dir=download_dir,
        max_workers=args.workers
    )
    
    # 開始下載
    console.print(f"\n📥 開始下載到暫存目錄: {download_dir}")
    download_stats = downloader.download_batch(media_items, show_progress=True)
    
    # 整理到備份目錄
    console.print(f"\n📁 整理照片到備份目錄: {backup_dir}")
    organize_stats = organizer.organize_to_backup(download_dir)
    
    # 顯示完成報告
    console.print()
    organizer.display_completion_report(download_stats, organize_stats)


if __name__ == '__main__':
    main()
