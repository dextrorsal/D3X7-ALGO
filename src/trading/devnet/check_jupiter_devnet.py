#!/usr/bin/env python3
"""
Script to check Jupiter account details on Devnet
"""

import asyncio
import logging
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from src.utils.wallet.sol_rpc import get_network, NETWORK_URLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token configuration for Devnet
# Note: Some tokens might have different mint addresses on devnet
TOKEN_INFO = {
    "SOL": {
        "mint": "So11111111111111111111111111111111111111112",  # Same on all networks
        "decimals": 9
    },
    "USDC": {
        "mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # Devnet USDC
        "decimals": 6
    }
    # Note: BTC and ETH tokens might need different devnet addresses
    # Add them once you have the correct devnet mint addresses
}

async def get_token_balance(client, wallet_pubkey, token_mint, decimals):
    """Get balance for a specific token"""
    try:
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
    """Check Jupiter/Solana account details on Devnet"""
    
    # Get network and RPC URL from sol_rpc
    network = get_network()
    rpc_url = NETWORK_URLS[network]
    logger.info(f"Using network: {network} with RPC URL: {rpc_url}")
    
    # Initialize Solana client with configured endpoint
    client = AsyncClient(rpc_url)
    
    # Convert wallet address to Pubkey
    wallet_pubkey = Pubkey.from_string(wallet_address)
    
    print("\nJupiter Account Summary (DEVNET)")
    print("================================")
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
                
        print(f"\nNote: This is checking balances on {network}!")
        print("Use 'solana airdrop 1' to get some devnet SOL if needed.")
                
    except Exception as e:
        logger.error(f"Error checking account: {str(e)}")
        raise
    finally:
        await client.close()

async def main():
    """Main entry point"""
    # You can replace this with your devnet wallet address
    wallet_address = "wgfSHTWx1woRXhsWijj1kcpCP8tmbmK2KnouFVAuoc6"
    await check_account(wallet_address)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")