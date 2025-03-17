#!/usr/bin/env python3
"""
Standalone script to check Jupiter account details using RPC directly
"""

import asyncio
import logging
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token configuration with Jupiter's verified token addresses
TOKEN_INFO = {
    "SOL": {
        "mint": "So11111111111111111111111111111111111111112",
        "decimals": 9
    },
    "USDC": {
        "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "decimals": 6
    },
    "BTC": {
        "mint": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
        "decimals": 8
    },
    "ETH": {
        "mint": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
        "decimals": 8
    }
}

async def get_token_balance(client, wallet_pubkey, token_mint, decimals):
    """Get balance for a specific token"""
    try:
        # Get token accounts for this specific mint
        response = await client.get_token_accounts_by_owner_json_parsed(
            wallet_pubkey,
            {'mint': token_mint}
        )
        
        total_balance = 0
        if response.value:
            for account in response.value:
                try:
                    parsed_info = account.account.data.parsed['info']
                    if 'tokenAmount' in parsed_info:
                        amount = float(parsed_info['tokenAmount']['uiAmount'] or 0)
                        total_balance += amount
                except (KeyError, TypeError, ValueError) as e:
                    logger.debug(f"Error parsing token amount: {str(e)}")
                    continue
                    
        return total_balance
        
    except Exception as e:
        logger.debug(f"Error getting token balance: {str(e)}")
        return 0

async def check_account(wallet_address: str):
    """Check Jupiter/Solana account details"""
    
    # Initialize Solana client with Mainnet endpoint
    client = AsyncClient("https://api.mainnet-beta.solana.com")
    
    # Convert wallet address to Pubkey
    wallet_pubkey = Pubkey.from_string(wallet_address)
    
    print("\nJupiter Account Summary")
    print("======================")
    print(f"Wallet Address: {wallet_address}")
    
    try:
        # Get SOL balance
        sol_response = await client.get_balance(wallet_pubkey, commitment=Confirmed)
        sol_balance = sol_response.value / 10**TOKEN_INFO['SOL']['decimals']
        print(f"\nSOL Balance: {sol_balance:.6f} SOL")
        
        # Get token balances
        print("\nToken Balances:")
        for token, info in TOKEN_INFO.items():
            if token == "SOL":  # Skip SOL as we already got it
                continue
                
            balance = await get_token_balance(
                client,
                wallet_pubkey,
                Pubkey.from_string(info['mint']),
                info['decimals']
            )
            
            if balance > 0:
                print(f"{token}: {balance:.6f}")
                
    except Exception as e:
        logger.error(f"Error checking account: {str(e)}")
        raise
    finally:
        await client.close()

async def main():
    """Main entry point"""
    # Your wallet address
    wallet_address = "wgfSHTWx1woRXhsWijj1kcpCP8tmbmK2KnouFVAuoc6"
    await check_account(wallet_address)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")