import asyncio
import sys
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from loguru import logger
import argparse

from src.config.settings import get_settings
from src.bot.backtest_engine import BacktestEngine
from src.strategies.simple_momentum import SimpleMomentumStrategy
from src.utils.data_fetcher import DataFetcher
from src.utils.logger import setup_logger


async def run_backtest(args):
    """Run backtest with specified parameters"""
    # Setup
    settings = get_settings()
    setup_logger()
    
    logger.info("=== XRPL Trading Bot Backtest ===")
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Period: {args.days} days")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Initial Balance: {args.balance}")
    
    # Initialize components
    data_fetcher = DataFetcher(settings)
    
    # Create strategy
    if args.strategy == "simple_momentum":
        strategy = SimpleMomentumStrategy()
    else:
        logger.error(f"Unknown strategy: {args.strategy}")
        return
    
    # Fetch historical data
    try:
        logger.info("Fetching historical data...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        # Check if we have cached data
        cache_file = f"xrp_usdt_{args.timeframe}_{args.days}d.csv"
        
        if args.use_cache:
            historical_data = await data_fetcher.load_data(cache_file)
        
        if args.use_cache and not historical_data.empty:
            logger.info("Using cached data")
        else:
            historical_data = await data_fetcher.fetch_historical_data(
                symbol="XRP/USDT",
                timeframe=args.timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            # Save for future use
            if not historical_data.empty and args.save_cache:
                await data_fetcher.save_data(historical_data, cache_file)
        
        if historical_data.empty:
            logger.error("No historical data available")
            return
        
        # Initialize backtest engine
        engine = BacktestEngine(
            settings=settings,
            strategy=strategy,
            initial_balance=Decimal(str(args.balance)),
            commission=Decimal(str(args.commission))
        )
        
        # Run backtest
        logger.info("Running backtest...")
        results = await engine.run_backtest(
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Display results
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Initial Balance: ${results.initial_balance:,.2f}")
        print(f"Final Balance: ${results.final_balance:,.2f}")
        print(f"Total P&L: ${results.total_pnl:,.2f} ({results.total_pnl_percent:.2f}%)")
        print(f"Total Trades: {results.total_trades}")
        print(f"Win Rate: {results.win_rate:.2%}")
        print(f"Winning Trades: {results.winning_trades}")
        print(f"Losing Trades: {results.losing_trades}")
        print(f"Average Win: ${results.average_win:,.2f}")
        print(f"Average Loss: ${results.average_loss:,.2f}")
        print(f"Profit Factor: {results.profit_factor:.2f}")
        print(f"Max Drawdown: ${results.max_drawdown:,.2f} ({results.max_drawdown_percent:.2f}%)")
        print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print("="*60)
        
        # Save detailed results if requested
        if args.save_results:
            # Save trades
            trades_df = pd.DataFrame(results.trades)
            trades_file = f"backtest_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            trades_df.to_csv(f"data/{trades_file}", index=False)
            logger.info(f"Saved trades to data/{trades_file}")
            
            # Save equity curve
            equity_df = pd.DataFrame(results.equity_curve)
            equity_file = f"backtest_equity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            equity_df.to_csv(f"data/{equity_file}", index=False)
            logger.info(f"Saved equity curve to data/{equity_file}")
        
        # Plot results if requested
        if args.plot:
            await plot_results(results)
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise
    finally:
        await data_fetcher.close()


async def plot_results(results):
    """Plot backtest results"""
    try:
        import matplotlib.pyplot as plt
        
        # Create equity curve
        equity_df = pd.DataFrame(results.equity_curve)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot equity curve
        ax1.plot(equity_df['timestamp'], equity_df['total_equity'], label='Total Equity')
        ax1.plot(equity_df['timestamp'], equity_df['balance'], label='Cash Balance', alpha=0.7)
        ax1.set_title('Equity Curve')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Value ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot drawdown
        equity_df['peak'] = equity_df['total_equity'].cummax()
        equity_df['drawdown'] = (equity_df['peak'] - equity_df['total_equity']) / equity_df['peak'] * 100
        
        ax2.fill_between(equity_df['timestamp'], 0, equity_df['drawdown'], 
                        color='red', alpha=0.3, label='Drawdown')
        ax2.set_title('Drawdown %')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Drawdown %')
        ax2.set_ylim(top=0)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_file = f"backtest_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(f"data/{plot_file}")
        logger.info(f"Saved plot to data/{plot_file}")
        
        # Show plot if not in headless mode
        if not args.no_display:
            plt.show()
        
    except ImportError:
        logger.warning("Matplotlib not installed. Skipping plots.")
    except Exception as e:
        logger.error(f"Error plotting results: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run XRPL Trading Bot Backtest")
    
    parser.add_argument(
        "--strategy",
        type=str,
        default="simple_momentum",
        help="Trading strategy to use"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to backtest"
    )
    
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1h",
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        help="Candle timeframe"
    )
    
    parser.add_argument(
        "--balance",
        type=float,
        default=10000.0,
        help="Initial balance"
    )
    
    parser.add_argument(
        "--commission",
        type=float,
        default=0.001,
        help="Commission rate (0.001 = 0.1%)"
    )
    
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cached historical data if available"
    )
    
    parser.add_argument(
        "--save-cache",
        action="store_true",
        default=True,
        help="Save fetched data to cache"
    )
    
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save detailed results to CSV"
    )
    
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Plot backtest results"
    )
    
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Don't display plots (save only)"
    )
    
    args = parser.parse_args()
    
    # Run backtest
    asyncio.run(run_backtest(args))