"""
照片整理器模組

負責：
- 依年月分類照片
- 顯示統計資訊
- 整理到備份目錄
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api import GooglePhotosAPI


class PhotoOrganizer:
    """照片整理器"""
    
    def __init__(self, backup_dir: str = None):
        """
        初始化整理器
        
        Args:
            backup_dir: 備份目標目錄
        """
        if backup_dir is None:
            backup_dir = Path(__file__).parent.parent / 'backup'
        self.backup_dir = Path(backup_dir)
        self.console = Console()
        
        # 年月分類的照片統計
        # 格式: {year: {month: [media_items...]}}
        self._categorized: Dict[int, Dict[int, List[Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # 無法解析日期的照片
        self._unknown_date: List[Dict[str, Any]] = []
    
    def categorize_by_date(self, media_items: List[Dict[str, Any]]) -> None:
        """
        依年月分類媒體項目
        
        Args:
            media_items: 媒體項目列表
        """
        self._categorized = defaultdict(lambda: defaultdict(list))
        self._unknown_date = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("📂 正在分類照片...", total=None)
            
            for item in media_items:
                creation_time = GooglePhotosAPI.parse_creation_time(item)
                
                if creation_time:
                    year = creation_time.year
                    month = creation_time.month
                    self._categorized[year][month].append(item)
                else:
                    self._unknown_date.append(item)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        取得統計資訊
        
        Returns:
            包含年月統計的字典
        """
        stats = {
            'by_year_month': {},
            'by_year': {},
            'total': 0,
            'unknown_date': len(self._unknown_date)
        }
        
        for year in sorted(self._categorized.keys()):
            year_total = 0
            stats['by_year_month'][year] = {}
            
            for month in sorted(self._categorized[year].keys()):
                count = len(self._categorized[year][month])
                stats['by_year_month'][year][month] = count
                year_total += count
            
            stats['by_year'][year] = year_total
            stats['total'] += year_total
        
        stats['total'] += stats['unknown_date']
        
        return stats
    
    def display_summary(self) -> None:
        """顯示年月統計表"""
        stats = self.get_statistics()
        
        # 建立表格
        table = Table(
            title="📊 Google 相簿統計",
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("年份", style="bold", justify="center")
        table.add_column("月份", justify="center")
        table.add_column("照片數量", justify="right", style="green")
        
        for year in sorted(stats['by_year_month'].keys(), reverse=True):
            months = stats['by_year_month'][year]
            first_row = True
            
            for month in sorted(months.keys()):
                count = months[month]
                if first_row:
                    table.add_row(
                        str(year),
                        f"{month:02d}月",
                        str(count)
                    )
                    first_row = False
                else:
                    table.add_row(
                        "",
                        f"{month:02d}月",
                        str(count)
                    )
            
            # 年度小計
            table.add_row(
                "",
                "[bold]小計[/bold]",
                f"[bold]{stats['by_year'][year]}[/bold]",
                style="dim"
            )
            table.add_row("", "", "")  # 空行分隔
        
        # 顯示表格
        self.console.print()
        self.console.print(table)
        
        # 顯示總計
        total_panel = Panel(
            f"[bold green]總計: {stats['total']} 張照片/影片[/bold green]\n"
            f"[dim]（無法識別日期: {stats['unknown_date']} 張）[/dim]",
            title="📷 備份摘要",
            border_style="green"
        )
        self.console.print(total_panel)
    
    def get_all_items_flat(self) -> List[Dict[str, Any]]:
        """
        取得所有已分類的媒體項目（扁平化列表）
        
        Returns:
            所有媒體項目的列表
        """
        items = []
        for year in self._categorized:
            for month in self._categorized[year]:
                items.extend(self._categorized[year][month])
        items.extend(self._unknown_date)
        return items
    
    def organize_to_backup(self, source_dir: Path) -> Dict[str, int]:
        """
        將下載的照片整理到備份目錄
        
        依據年月將照片移動到對應的目錄結構：
        backup/YYYY/MM/filename.jpg
        
        Args:
            source_dir: 下載暫存目錄
            
        Returns:
            整理結果統計
        """
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        stats = {'moved': 0, 'failed': 0}
        
        # 建立檔名到媒體項目的映射
        filename_map = {}
        for year in self._categorized:
            for month in self._categorized[year]:
                for item in self._categorized[year][month]:
                    filename = item.get('filename', f"{item['id']}.jpg")
                    filename_map[filename] = (year, month, item)
        
        # 處理無法識別日期的照片
        for item in self._unknown_date:
            filename = item.get('filename', f"{item['id']}.jpg")
            filename_map[filename] = (0, 0, item)  # 0 表示未知
        
        source_dir = Path(source_dir)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            files = list(source_dir.iterdir())
            task = progress.add_task(
                "📁 正在整理照片到備份目錄...", 
                total=len(files)
            )
            
            for file_path in files:
                if not file_path.is_file() or file_path.name == '.gitkeep':
                    progress.update(task, advance=1)
                    continue
                
                filename = file_path.name
                
                if filename in filename_map:
                    year, month, item = filename_map[filename]
                    
                    if year == 0:
                        # 未知日期
                        dest_dir = self.backup_dir / 'unknown'
                    else:
                        dest_dir = self.backup_dir / str(year) / f"{month:02d}"
                    
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / filename
                    
                    try:
                        shutil.move(str(file_path), str(dest_path))
                        stats['moved'] += 1
                    except Exception as e:
                        stats['failed'] += 1
                else:
                    # 找不到對應的媒體項目，移到 unknown
                    dest_dir = self.backup_dir / 'unknown'
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        shutil.move(str(file_path), str(dest_dir / filename))
                        stats['moved'] += 1
                    except Exception:
                        stats['failed'] += 1
                
                progress.update(task, advance=1)
        
        return stats
    
    def display_completion_report(self, download_stats: Dict, organize_stats: Dict) -> None:
        """
        顯示完成報告
        
        Args:
            download_stats: 下載統計
            organize_stats: 整理統計
        """
        from .downloader import PhotoDownloader
        
        report = f"""
[bold green]✅ 備份完成！[/bold green]

[bold]下載統計:[/bold]
  • 成功下載: {download_stats.get('success', 0)} 張
  • 下載失敗: {download_stats.get('failed', 0)} 張
  • 已存在跳過: {download_stats.get('skipped', 0)} 張
  • 總下載大小: {PhotoDownloader.format_bytes(download_stats.get('total_bytes', 0))}

[bold]整理統計:[/bold]
  • 已整理: {organize_stats.get('moved', 0)} 張
  • 整理失敗: {organize_stats.get('failed', 0)} 張

[bold]備份目錄:[/bold] {self.backup_dir}
        """
        
        self.console.print(Panel(
            report.strip(),
            title="📊 備份報告",
            border_style="green"
        ))
