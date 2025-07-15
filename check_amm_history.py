"""
Check AMM pool reserve history
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from src.database.models import AMMSnapshot, get_session, init_database
from src.config.settings import get_settings
from sqlalchemy import select, func
import pandas as pd


def analyze_amm_history():
    """Analyze AMM pool reserve history"""
    settings = get_settings()
    engine = init_database(settings.database_url)
    session = get_session(engine)
    
    # Load token config
    tokens_file = Path("src/config/tokens.json")
    with open(tokens_file) as f:
        tokens = json.load(f)
    
    print("\n=== AMM Pool Reserve History ===\n")
    
    try:
        for token_name, token_info in tokens.items():
            amm_address = token_info["amm_address"]
            
            # Get all snapshots for this AMM
            snapshots = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == amm_address
            ).order_by(AMMSnapshot.timestamp.desc()).all()
            
            if not snapshots:
                print(f"{token_name}: No AMM history found")
                continue
                
            print(f"\n{token_name} ({amm_address[:10]}...):")
            print(f"  Total snapshots: {len(snapshots)}")
            
            # Get latest snapshot
            latest = snapshots[0]
            print(f"  Latest snapshot: {latest.timestamp}")
            print(f"    XRP Reserve: {float(latest.asset1_amount):,.2f}")
            print(f"    Token Reserve: {float(latest.asset2_amount):,.2f}")
            print(f"    Price: {float(latest.price_asset2_per_asset1):.6f} {token_name}/XRP")
            print(f"    TVL: {float(latest.tvl_xrp):,.2f} XRP")
            
            # Calculate changes over time
            if len(snapshots) > 1:
                # 24h change
                day_ago = datetime.utcnow() - timedelta(days=1)
                day_snapshot = next((s for s in snapshots if s.timestamp <= day_ago), None)
                
                if day_snapshot:
                    xrp_change = float(latest.asset1_amount - day_snapshot.asset1_amount)
                    xrp_change_pct = (xrp_change / float(day_snapshot.asset1_amount)) * 100
                    
                    token_change = float(latest.asset2_amount - day_snapshot.asset2_amount)
                    token_change_pct = (token_change / float(day_snapshot.asset2_amount)) * 100
                    
                    print(f"  24h Changes:")
                    print(f"    XRP: {xrp_change:+,.2f} ({xrp_change_pct:+.2f}%)")
                    print(f"    Token: {token_change:+,.2f} ({token_change_pct:+.2f}%)")
                
                # All-time high/low
                xrp_amounts = [float(s.asset1_amount) for s in snapshots]
                token_amounts = [float(s.asset2_amount) for s in snapshots]
                
                print(f"  All-time ranges:")
                print(f"    XRP: {min(xrp_amounts):,.2f} - {max(xrp_amounts):,.2f}")
                print(f"    Token: {min(token_amounts):,.2f} - {max(token_amounts):,.2f}")
        
        # Overall statistics
        print("\n=== Overall Statistics ===")
        total_snapshots = session.scalar(select(func.count(AMMSnapshot.id)))
        unique_amms = session.scalar(select(func.count(func.distinct(AMMSnapshot.amm_address))))
        date_range = session.execute(
            select(func.min(AMMSnapshot.timestamp), func.max(AMMSnapshot.timestamp))
        ).first()
        
        print(f"Total snapshots: {total_snapshots}")
        print(f"Unique AMMs tracked: {unique_amms}")
        print(f"Date range: {date_range[0]} to {date_range[1]}")
        
        # Export sample data
        print("\n=== Exporting Sample Data ===")
        
        # Get RLUSD history for export
        rlusd_amm = tokens.get("RLUSD", {}).get("amm_address")
        if rlusd_amm:
            rlusd_snapshots = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == rlusd_amm
            ).order_by(AMMSnapshot.timestamp).all()
            
            if rlusd_snapshots:
                data = []
                for s in rlusd_snapshots:
                    data.append({
                        "timestamp": s.timestamp,
                        "xrp_reserve": float(s.asset1_amount),
                        "rlusd_reserve": float(s.asset2_amount),
                        "price_rlusd_per_xrp": float(s.price_asset2_per_asset1),
                        "k_constant": float(s.k_constant) if s.k_constant else None,
                        "tvl_xrp": float(s.tvl_xrp) if s.tvl_xrp else None
                    })
                
                df = pd.DataFrame(data)
                output_file = "data/rlusd_amm_history.csv"
                df.to_csv(output_file, index=False)
                print(f"Exported RLUSD AMM history to {output_file}")
                print(f"Records exported: {len(df)}")
                
    finally:
        session.close()


if __name__ == "__main__":
    analyze_amm_history()