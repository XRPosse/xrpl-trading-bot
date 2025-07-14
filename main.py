import asyncio
import signal
import sys
from typing import Optional
from loguru import logger

from src.config.settings import get_settings
from src.bot.trading_bot import TradingBot
from src.strategies.simple_momentum import SimpleMomentumStrategy
from src.utils.logger import setup_logger


class BotManager:
    def __init__(self):
        self.bot: Optional[TradingBot] = None
        self.settings = get_settings()
        self.logger = setup_logger()
        
    async def start(self):
        try:
            logger.info("=== XRPL Trading Bot Starting ===")
            logger.info(f"Mode: {self.settings.bot_mode.value}")
            logger.info(f"Network: {self.settings.xrpl_network.value}")
            logger.info(f"Strategy: {self.settings.strategy.value}")
            logger.info(f"Trading Pair: {self.settings.trading_pair}")
            
            # Initialize strategy
            strategy = self._create_strategy()
            
            # Initialize trading bot
            self.bot = TradingBot(self.settings, strategy)
            
            # Start bot
            await self.bot.start()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    async def stop(self):
        logger.info("Shutting down trading bot...")
        if self.bot:
            await self.bot.stop()
        logger.info("Bot shutdown complete")
    
    def _create_strategy(self):
        if self.settings.strategy.value == "simple_momentum":
            return SimpleMomentumStrategy()
        else:
            raise ValueError(f"Unknown strategy: {self.settings.strategy}")


async def main():
    manager = BotManager()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(manager.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)