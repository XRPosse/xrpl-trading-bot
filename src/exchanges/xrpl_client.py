import asyncio
from typing import Optional, Dict, Any, List
from decimal import Decimal
from xrpl.asyncio.clients import AsyncWebsocketClient, AsyncJsonRpcClient
from xrpl.models import AccountInfo, AccountTx, Subscribe, Unsubscribe
from xrpl.models.requests import BookOffers, Transaction
from xrpl.models.transactions import Payment, OfferCreate, OfferCancel
from xrpl.wallet import Wallet
from xrpl.utils import xrp_to_drops, drops_to_xrp
from xrpl.asyncio.transaction import safe_sign_and_autofill_transaction, send_reliable_submission
from loguru import logger

from src.config.settings import Settings
from src.config.constants import MIN_XRP_BALANCE, DROPS_PER_XRP


class XRPLClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ws_url, self.json_rpc_url = settings.get_network_urls()
        self.ws_client: Optional[AsyncWebsocketClient] = None
        self.json_client: Optional[AsyncJsonRpcClient] = None
        self.wallet: Optional[Wallet] = None
        self._connected = False
        
    async def connect(self) -> None:
        try:
            # Initialize WebSocket client
            self.ws_client = AsyncWebsocketClient(self.ws_url)
            await self.ws_client.open()
            
            # Initialize JSON-RPC client
            self.json_client = AsyncJsonRpcClient(self.json_rpc_url)
            
            # Initialize wallet if seed is provided
            if self.settings.wallet_seed:
                self.wallet = Wallet.from_seed(self.settings.wallet_seed)
                logger.info(f"Wallet initialized with address: {self.wallet.address}")
            
            self._connected = True
            logger.info(f"Connected to XRPL network: {self.ws_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to XRPL: {e}")
            raise
    
    async def disconnect(self) -> None:
        if self.ws_client and self.ws_client.is_open():
            await self.ws_client.close()
        self._connected = False
        logger.info("Disconnected from XRPL network")
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self.ws_client and self.ws_client.is_open()
    
    async def get_account_info(self, address: Optional[str] = None) -> Dict[str, Any]:
        if not address and not self.wallet:
            raise ValueError("No address provided and no wallet initialized")
        
        target_address = address or self.wallet.address
        
        try:
            request = AccountInfo(account=target_address)
            response = await self.json_client.request(request)
            
            if response.is_successful():
                account_data = response.result["account_data"]
                return {
                    "address": target_address,
                    "balance": drops_to_xrp(account_data["Balance"]),
                    "sequence": account_data["Sequence"],
                    "flags": account_data.get("Flags", 0),
                    "owner_count": account_data.get("OwnerCount", 0),
                }
            else:
                logger.error(f"Failed to get account info: {response.result}")
                raise Exception(f"Account info request failed: {response.result}")
                
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    async def get_xrp_balance(self, address: Optional[str] = None) -> Decimal:
        account_info = await self.get_account_info(address)
        return Decimal(str(account_info["balance"]))
    
    async def subscribe_to_transactions(self, accounts: List[str]) -> None:
        if not self.ws_client:
            raise RuntimeError("WebSocket client not connected")
        
        subscribe_request = Subscribe(
            accounts=accounts,
            streams=["transactions"]
        )
        
        await self.ws_client.send(subscribe_request)
        logger.info(f"Subscribed to transactions for accounts: {accounts}")
    
    async def unsubscribe_from_transactions(self, accounts: List[str]) -> None:
        if not self.ws_client:
            raise RuntimeError("WebSocket client not connected")
        
        unsubscribe_request = Unsubscribe(
            accounts=accounts,
            streams=["transactions"]
        )
        
        await self.ws_client.send(unsubscribe_request)
        logger.info(f"Unsubscribed from transactions for accounts: {accounts}")
    
    async def get_order_book(self, base: str, quote: str, limit: int = 20) -> Dict[str, Any]:
        try:
            # For XRP pairs, we need to handle the special case
            taker_gets = {"currency": "XRP"} if base == "XRP" else {
                "currency": base,
                "issuer": self._get_issuer_address(base)
            }
            
            taker_pays = {"currency": "XRP"} if quote == "XRP" else {
                "currency": quote,
                "issuer": self._get_issuer_address(quote)
            }
            
            request = BookOffers(
                taker_gets=taker_gets,
                taker_pays=taker_pays,
                limit=limit
            )
            
            response = await self.json_client.request(request)
            
            if response.is_successful():
                offers = response.result.get("offers", [])
                return self._format_order_book(offers)
            else:
                logger.error(f"Failed to get order book: {response.result}")
                return {"bids": [], "asks": []}
                
        except Exception as e:
            logger.error(f"Error getting order book: {e}")
            return {"bids": [], "asks": []}
    
    def _format_order_book(self, offers: List[Dict]) -> Dict[str, List]:
        bids = []
        asks = []
        
        for offer in offers:
            # Determine if this is a bid or ask based on the offer direction
            price = self._calculate_price(offer)
            amount = self._get_amount(offer)
            
            order_entry = {
                "price": price,
                "amount": amount,
                "total": price * amount
            }
            
            # Add to appropriate list based on offer flags
            if offer.get("Flags", 0) & 0x00020000:  # Sell flag
                asks.append(order_entry)
            else:
                bids.append(order_entry)
        
        # Sort bids descending, asks ascending
        bids.sort(key=lambda x: x["price"], reverse=True)
        asks.sort(key=lambda x: x["price"])
        
        return {"bids": bids, "asks": asks}
    
    def _calculate_price(self, offer: Dict) -> Decimal:
        # Calculate price based on taker_gets and taker_pays
        taker_gets = offer.get("TakerGets", offer.get("taker_gets", {}))
        taker_pays = offer.get("TakerPays", offer.get("taker_pays", {}))
        
        if isinstance(taker_gets, str):  # XRP amount in drops
            gets_amount = Decimal(taker_gets) / DROPS_PER_XRP
        else:
            gets_amount = Decimal(taker_gets.get("value", "0"))
        
        if isinstance(taker_pays, str):  # XRP amount in drops
            pays_amount = Decimal(taker_pays) / DROPS_PER_XRP
        else:
            pays_amount = Decimal(taker_pays.get("value", "0"))
        
        if gets_amount == 0:
            return Decimal("0")
        
        return pays_amount / gets_amount
    
    def _get_amount(self, offer: Dict) -> Decimal:
        taker_gets = offer.get("TakerGets", offer.get("taker_gets", {}))
        
        if isinstance(taker_gets, str):  # XRP amount in drops
            return Decimal(taker_gets) / DROPS_PER_XRP
        else:
            return Decimal(taker_gets.get("value", "0"))
    
    def _get_issuer_address(self, currency: str) -> str:
        # This would normally come from a configuration or database
        # For now, returning a placeholder
        # In production, you'd map currency codes to their issuers
        return "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"  # Example issuer
    
    async def create_offer(
        self,
        taker_gets: Dict[str, Any],
        taker_pays: Dict[str, Any],
        flags: int = 0
    ) -> Dict[str, Any]:
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            offer = OfferCreate(
                account=self.wallet.address,
                taker_gets=taker_gets,
                taker_pays=taker_pays,
                flags=flags
            )
            
            # Sign and submit the transaction
            signed_tx = await safe_sign_and_autofill_transaction(
                offer, self.wallet, self.json_client
            )
            
            response = await send_reliable_submission(signed_tx, self.json_client)
            
            if response.is_successful():
                logger.info(f"Offer created successfully: {response.result}")
                return response.result
            else:
                logger.error(f"Failed to create offer: {response.result}")
                raise Exception(f"Offer creation failed: {response.result}")
                
        except Exception as e:
            logger.error(f"Error creating offer: {e}")
            raise
    
    async def cancel_offer(self, offer_sequence: int) -> Dict[str, Any]:
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            cancel = OfferCancel(
                account=self.wallet.address,
                offer_sequence=offer_sequence
            )
            
            signed_tx = await safe_sign_and_autofill_transaction(
                cancel, self.wallet, self.json_client
            )
            
            response = await send_reliable_submission(signed_tx, self.json_client)
            
            if response.is_successful():
                logger.info(f"Offer cancelled successfully: {response.result}")
                return response.result
            else:
                logger.error(f"Failed to cancel offer: {response.result}")
                raise Exception(f"Offer cancellation failed: {response.result}")
                
        except Exception as e:
            logger.error(f"Error cancelling offer: {e}")
            raise
    
    async def get_transaction_history(
        self,
        address: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        if not address and not self.wallet:
            raise ValueError("No address provided and no wallet initialized")
        
        target_address = address or self.wallet.address
        
        try:
            request = AccountTx(
                account=target_address,
                limit=limit
            )
            
            response = await self.json_client.request(request)
            
            if response.is_successful():
                transactions = response.result.get("transactions", [])
                return [self._format_transaction(tx) for tx in transactions]
            else:
                logger.error(f"Failed to get transaction history: {response.result}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []
    
    def _format_transaction(self, tx_data: Dict) -> Dict[str, Any]:
        tx = tx_data.get("tx", {})
        meta = tx_data.get("meta", {})
        
        return {
            "hash": tx.get("hash"),
            "type": tx.get("TransactionType"),
            "account": tx.get("Account"),
            "destination": tx.get("Destination"),
            "amount": self._format_amount(tx.get("Amount")),
            "fee": drops_to_xrp(tx.get("Fee", "0")),
            "date": tx.get("date"),
            "result": meta.get("TransactionResult"),
            "validated": tx_data.get("validated", False)
        }
    
    def _format_amount(self, amount: Any) -> Dict[str, Any]:
        if isinstance(amount, str):  # XRP amount in drops
            return {
                "currency": "XRP",
                "value": str(drops_to_xrp(amount))
            }
        elif isinstance(amount, dict):
            return {
                "currency": amount.get("currency"),
                "value": amount.get("value"),
                "issuer": amount.get("issuer")
            }
        else:
            return {"currency": "XRP", "value": "0"}