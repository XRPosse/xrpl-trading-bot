"""
Visualize AMM pool history
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
from src.database.models import AMMSnapshot, get_session, init_database
from src.config.settings import get_settings
from sqlalchemy import select


def visualize_amm_history():
    """Create visualizations of AMM pool history"""
    settings = get_settings()
    engine = init_database(settings.database_url)
    session = get_session(engine)
    
    # Load token config
    tokens_file = Path("src/config/tokens.json")
    with open(tokens_file) as f:
        tokens = json.load(f)
    
    # Create output directory
    output_dir = Path("data/amm_visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create a figure with subplots for top tokens
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('AMM Pool Reserves Over Time', fontsize=16)
        
        # Select top tokens to visualize
        top_tokens = ["RLUSD", "UGA", "BEAR", "CULT"]
        
        for idx, (ax, token_name) in enumerate(zip(axes.flat, top_tokens)):
            if token_name not in tokens:
                continue
                
            amm_address = tokens[token_name]["amm_address"]
            
            # Get snapshots
            snapshots = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == amm_address
            ).order_by(AMMSnapshot.timestamp).all()
            
            if not snapshots:
                ax.text(0.5, 0.5, f'No data for {token_name}', 
                       ha='center', va='center', transform=ax.transAxes)
                continue
                
            # Prepare data
            timestamps = [s.timestamp for s in snapshots]
            xrp_reserves = [float(s.asset1_amount) for s in snapshots]
            token_reserves = [float(s.asset2_amount) for s in snapshots]
            
            # Create dual y-axis plot
            ax2 = ax.twinx()
            
            # Plot XRP reserves
            line1 = ax.plot(timestamps, xrp_reserves, 'b-', label='XRP Reserve')
            ax.set_ylabel('XRP Reserve', color='b')
            ax.tick_params(axis='y', labelcolor='b')
            
            # Plot token reserves
            line2 = ax2.plot(timestamps, token_reserves, 'r-', label=f'{token_name} Reserve')
            ax2.set_ylabel(f'{token_name} Reserve', color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            
            # Format
            ax.set_title(f'{token_name} AMM Pool')
            ax.set_xlabel('Date')
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels
            ax.tick_params(axis='x', rotation=45)
            
            # Add legend
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax.legend(lines, labels, loc='upper left')
            
        plt.tight_layout()
        plt.savefig(output_dir / 'amm_reserves_overview.png', dpi=300, bbox_inches='tight')
        print(f"Saved overview chart to {output_dir / 'amm_reserves_overview.png'}")
        
        # Create detailed charts for each token
        for token_name, token_info in tokens.items():
            amm_address = token_info["amm_address"]
            
            # Get snapshots
            snapshots = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == amm_address
            ).order_by(AMMSnapshot.timestamp).all()
            
            if len(snapshots) < 2:
                continue
                
            # Create detailed figure
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'{token_name} AMM Pool Analysis', fontsize=16)
            
            # Prepare data
            df = pd.DataFrame([{
                'timestamp': s.timestamp,
                'xrp_reserve': float(s.asset1_amount),
                'token_reserve': float(s.asset2_amount),
                'price': float(s.price_asset2_per_asset1),
                'k_constant': float(s.k_constant) if s.k_constant else None,
                'tvl_xrp': float(s.tvl_xrp) if s.tvl_xrp else None
            } for s in snapshots])
            
            # 1. Reserves over time
            ax1_2 = ax1.twinx()
            ax1.plot(df['timestamp'], df['xrp_reserve'], 'b-', label='XRP')
            ax1_2.plot(df['timestamp'], df['token_reserve'], 'r-', label=token_name)
            ax1.set_title('Pool Reserves')
            ax1.set_ylabel('XRP Reserve', color='b')
            ax1_2.set_ylabel(f'{token_name} Reserve', color='r')
            ax1.grid(True, alpha=0.3)
            
            # 2. Price over time
            ax2.plot(df['timestamp'], df['price'], 'g-', linewidth=2)
            ax2.set_title(f'Price ({token_name}/XRP)')
            ax2.set_ylabel('Price')
            ax2.grid(True, alpha=0.3)
            
            # 3. K constant (should be relatively stable)
            if df['k_constant'].notna().any():
                ax3.plot(df['timestamp'], df['k_constant'], 'm-')
                ax3.set_title('K Constant (x*y)')
                ax3.set_ylabel('K Value')
                ax3.grid(True, alpha=0.3)
            
            # 4. TVL in XRP
            if df['tvl_xrp'].notna().any():
                ax4.plot(df['timestamp'], df['tvl_xrp'], 'orange', linewidth=2)
                ax4.set_title('Total Value Locked (XRP)')
                ax4.set_ylabel('TVL (XRP)')
                ax4.grid(True, alpha=0.3)
                
            # Format all x-axes
            for ax in [ax1, ax2, ax3, ax4]:
                ax.tick_params(axis='x', rotation=45)
                
            plt.tight_layout()
            output_file = output_dir / f'{token_name}_amm_analysis.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved {token_name} analysis to {output_file}")
            
            # Also save data as CSV
            csv_file = output_dir / f'{token_name}_amm_history.csv'
            df.to_csv(csv_file, index=False)
            print(f"Saved {token_name} data to {csv_file}")
            
        # Create summary statistics
        print("\n=== AMM Pool Statistics ===")
        for token_name, token_info in tokens.items():
            amm_address = token_info["amm_address"]
            
            snapshots = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == amm_address
            ).all()
            
            if not snapshots:
                continue
                
            xrp_reserves = [float(s.asset1_amount) for s in snapshots]
            token_reserves = [float(s.asset2_amount) for s in snapshots]
            prices = [float(s.price_asset2_per_asset1) for s in snapshots]
            
            print(f"\n{token_name}:")
            print(f"  Snapshots: {len(snapshots)}")
            print(f"  XRP Reserve: {min(xrp_reserves):,.2f} - {max(xrp_reserves):,.2f} (avg: {sum(xrp_reserves)/len(xrp_reserves):,.2f})")
            print(f"  Token Reserve: {min(token_reserves):,.2f} - {max(token_reserves):,.2f}")
            print(f"  Price Range: {min(prices):.6f} - {max(prices):.6f} {token_name}/XRP")
            
            # Calculate volatility
            if len(prices) > 1:
                price_changes = [(prices[i] - prices[i-1]) / prices[i-1] * 100 
                               for i in range(1, len(prices))]
                if price_changes:
                    avg_change = sum(abs(c) for c in price_changes) / len(price_changes)
                    print(f"  Avg Price Change: {avg_change:.2f}% between snapshots")
                    
    finally:
        session.close()
        plt.close('all')


if __name__ == "__main__":
    visualize_amm_history()