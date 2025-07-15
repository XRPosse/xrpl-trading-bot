"""
Monitor real-time collection status
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

from src.database.storage import DataStorage
from src.database.models import TokenTransaction, DataCollectionLog, AMMSnapshot, get_session
from sqlalchemy import select, func, and_


class CollectionMonitor:
    """Monitor collection status and statistics"""
    
    def __init__(self):
        self.storage = DataStorage()
        self.console = Console()
        self.tokens = self.load_tokens()
        
    def load_tokens(self):
        """Load token configuration"""
        tokens_file = Path("src/config/tokens.json")
        with open(tokens_file) as f:
            return json.load(f)
            
    def get_collection_status(self):
        """Get current collection status"""
        session = get_session(self.storage.engine)
        
        try:
            status = {}
            
            # Get collection logs
            logs = session.query(DataCollectionLog).filter(
                DataCollectionLog.collection_type == "realtime"
            ).all()
            
            for log in logs:
                # Find token name
                token_name = "Unknown"
                for name, info in self.tokens.items():
                    if info["amm_address"] == log.target:
                        token_name = name
                        break
                        
                status[token_name] = {
                    "account": log.target,
                    "last_ledger": log.last_processed_ledger,
                    "last_run": log.last_run,
                    "status": log.status,
                    "records": log.records_collected
                }
                
            return status
            
        finally:
            session.close()
            
    def get_recent_activity(self, minutes: int = 60):
        """Get recent transaction activity"""
        session = get_session(self.storage.engine)
        
        try:
            since = datetime.utcnow() - timedelta(minutes=minutes)
            
            # Get activity by token
            activity = session.execute(
                select(
                    TokenTransaction.wallet_address,
                    func.count(TokenTransaction.id).label('count'),
                    func.max(TokenTransaction.timestamp).label('latest')
                )
                .where(TokenTransaction.timestamp >= since)
                .group_by(TokenTransaction.wallet_address)
            ).all()
            
            results = {}
            for row in activity:
                # Find token name
                token_name = "Unknown"
                for name, info in self.tokens.items():
                    if info["amm_address"] == row.wallet_address:
                        token_name = name
                        break
                        
                results[token_name] = {
                    "count": row.count,
                    "latest": row.latest,
                    "rate_per_min": row.count / minutes
                }
                
            return results
            
        finally:
            session.close()
            
    def create_status_table(self):
        """Create status table"""
        table = Table(title=f"Collection Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        table.add_column("Token", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Last Ledger", justify="right")
        table.add_column("Last Run", style="yellow")
        table.add_column("Gap (min)", justify="right", style="red")
        
        status = self.get_collection_status()
        
        # Estimate current ledger (21600 per day)
        current_ledger = 97478500  # Will be updated from actual data
        
        for token_name in sorted(self.tokens.keys()):
            if token_name in status:
                info = status[token_name]
                
                # Calculate gap
                gap = current_ledger - info["last_ledger"]
                gap_minutes = gap * 4 / 60  # 4 seconds per ledger
                
                # Status emoji
                if info["status"] == "active":
                    status_icon = "🟢"
                elif gap_minutes > 60:
                    status_icon = "🔴"
                elif gap_minutes > 10:
                    status_icon = "🟡"
                else:
                    status_icon = "🟢"
                    
                last_run = info["last_run"].strftime("%H:%M:%S") if info["last_run"] else "Never"
                
                table.add_row(
                    token_name,
                    f"{status_icon} {info['status']}",
                    f"{info['last_ledger']:,}",
                    last_run,
                    f"{gap_minutes:.1f}" if gap_minutes > 0 else "0"
                )
            else:
                table.add_row(
                    token_name,
                    "⚫ Not started",
                    "-",
                    "-",
                    "-"
                )
                
        return table
        
    def create_activity_table(self):
        """Create recent activity table"""
        table = Table(title="Recent Activity (Last Hour)")
        
        table.add_column("Token", style="cyan")
        table.add_column("Transactions", justify="right", style="green")
        table.add_column("Rate/min", justify="right", style="yellow")
        table.add_column("Last Transaction", style="white")
        
        activity = self.get_recent_activity(60)
        
        for token_name in sorted(self.tokens.keys()):
            if token_name in activity:
                info = activity[token_name]
                
                last_tx = info["latest"].strftime("%H:%M:%S") if info["latest"] else "-"
                
                table.add_row(
                    token_name,
                    f"{info['count']:,}",
                    f"{info['rate_per_min']:.2f}",
                    last_tx
                )
            else:
                table.add_row(
                    token_name,
                    "0",
                    "0.00",
                    "-"
                )
                
        return table
        
    def create_summary_panel(self):
        """Create summary panel"""
        session = get_session(self.storage.engine)
        
        try:
            # Get total counts
            total_tx = session.scalar(select(func.count(TokenTransaction.id)))
            
            # Get date range
            earliest = session.scalar(select(func.min(TokenTransaction.timestamp)))
            latest = session.scalar(select(func.max(TokenTransaction.timestamp)))
            
            # Get active collectors
            active_count = session.scalar(
                select(func.count(DataCollectionLog.id))
                .where(DataCollectionLog.status == "active")
            )
            
            # Get AMM snapshot count
            amm_count = session.scalar(select(func.count(AMMSnapshot.id)))
            amm_latest = session.scalar(select(func.max(AMMSnapshot.timestamp)))
            
            summary = f"""
[bold]Database Summary[/bold]
Total Transactions: {total_tx:,}
AMM Snapshots: {amm_count:,}
Date Range: {earliest.date() if earliest else 'N/A'} to {latest.date() if latest else 'N/A'}
Active Collectors: {active_count}

[bold]AMM Tracking[/bold]
Latest Snapshot: {amm_latest.strftime('%H:%M:%S') if amm_latest else 'N/A'}

[bold]Collection Health[/bold]
Use Ctrl+C to stop monitoring
"""
            
            return Panel(summary, title="System Overview", border_style="blue")
            
        finally:
            session.close()
            
    async def run_monitor(self, refresh_seconds: int = 5):
        """Run monitoring loop"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="summary", size=10),
            Layout(name="status", size=15),
            Layout(name="activity", size=15)
        )
        
        with Live(layout, refresh_per_second=1, screen=True) as live:
            while True:
                try:
                    # Update displays
                    layout["summary"].update(self.create_summary_panel())
                    layout["status"].update(self.create_status_table())
                    layout["activity"].update(self.create_activity_table())
                    
                    await asyncio.sleep(refresh_seconds)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(1)


async def main():
    """Main monitoring function"""
    monitor = CollectionMonitor()
    
    print("Starting collection monitor...")
    print("Press Ctrl+C to stop\n")
    
    await monitor.run_monitor(refresh_seconds=5)


if __name__ == "__main__":
    asyncio.run(main())