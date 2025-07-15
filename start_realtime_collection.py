"""
Start real-time collection with automatic backfill
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.realtime.collection_manager import main

if __name__ == "__main__":
    print("="*60)
    print("XRPL REAL-TIME COLLECTION")
    print("="*60)
    print("This will:")
    print("1. Check for data gaps and backfill if needed")
    print("2. Start real-time monitoring of all AMM pools")
    print("3. Automatically recover from disconnections")
    print("4. Run periodic gap checks every hour")
    print("\nPress Ctrl+C to stop")
    print("="*60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)