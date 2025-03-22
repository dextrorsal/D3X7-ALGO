#!/usr/bin/env python3
"""
Simple test script for SOL transfer
"""
import asyncio
import os
import sys
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import set_network, get_network
from solana.rpc.async_api import AsyncClient

async def transfer_sol():
    """Transfer a small amount of SOL between two wallets"""
    print("Testing SOL transfer on devnet...")
    
    # Initialize wallet manager
    wallet_manager = WalletManager()
    
    # Ensure we're on devnet and using correct RPC
    devnet_url = os.getenv("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com")
    client = AsyncClient(devnet_url)
    
    # List available wallets
    wallets = wallet_manager.list_wallets()
    if len(wallets) < 2:
        print("Need at least 2 wallets for transfer test! Only found:", wallets)
        return
    
    # Set source wallet to MAIN
    source_wallet_name = "MAIN"
    source_wallet = wallet_manager.get_wallet(source_wallet_name)
    if not source_wallet:
        print(f"Source wallet '{source_wallet_name}' not found!")
        return
    
    # Set destination wallet to AG_TRADE
    destination_wallet_name = "AG_TRADE"
    destination_wallet = wallet_manager.get_wallet(destination_wallet_name)
    if not destination_wallet:
        print(f"Destination wallet '{destination_wallet_name}' not found!")
        return
    
    # Check balances directly using RPC
    print("\nChecking balances using direct RPC calls...")
    source_balance_info = await client.get_balance(source_wallet.pubkey)
    dest_balance_info = await client.get_balance(destination_wallet.pubkey)
    
    source_balance = source_balance_info.value / 1e9  # Convert lamports to SOL
    dest_balance = dest_balance_info.value / 1e9  # Convert lamports to SOL
    
    print(f"Source wallet ({source_wallet_name}) public key: {source_wallet.pubkey}")
    print(f"Source wallet balance: {source_balance} SOL")
    print(f"Destination wallet ({destination_wallet_name}) public key: {destination_wallet.pubkey}")
    print(f"Destination wallet balance: {dest_balance} SOL")
    
    # Set fixed amount
    amount = 0.01  # Transfer 0.01 SOL
    
    if source_balance < amount + 0.001:  # Add some for fees
        print(f"Insufficient balance in source wallet! Need at least {amount + 0.001} SOL")
        print("Requesting airdrop of 1 SOL...")
        try:
            await source_wallet.request_airdrop(1.0)
            print("Airdrop requested. Checking new balance...")
            await asyncio.sleep(2)  # Wait for airdrop to process
            source_balance = await source_wallet.get_balance()
            print(f"New source wallet balance: {source_balance} SOL")
            
            if source_balance < amount + 0.001:
                print("Still insufficient balance after airdrop. Please try again later.")
                return
        except Exception as e:
            print(f"Airdrop failed: {str(e)}")
            return
    
    # Confirm transfer
    print(f"\nPreparing to transfer {amount} SOL from {source_wallet_name} to {destination_wallet_name}...")
    confirm = input(f"Proceed with transfer? (y/n): ")
    if confirm.lower() != 'y':
        print("Transfer cancelled.")
        return
    
    # Perform transfer
    print(f"\nTransferring {amount} SOL...")
    try:
        # Create and send transfer transaction
        tx = await source_wallet.create_transfer_tx(
            destination_wallet.pubkey,
            amount
        )
        
        # Send transaction
        await source_wallet.init_client()  # Ensure client is initialized
        result = await source_wallet.client.send_transaction(tx)
        signature = result.value
        
        print(f"Transfer sent! Signature: {signature}")
        print("Waiting for confirmation...")
        
        # Wait for confirmation
        for _ in range(30):  # Try for 30 seconds
            try:
                confirm_result = await source_wallet.client.confirm_transaction(signature)
                if confirm_result.value:
                    print("Transaction confirmed!")
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
            print(".", end="", flush=True)
        print("\n")
        
        # Wait a moment before checking final balances
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"Transfer failed: {str(e)}")
        return
    
    # Check balances after transfer
    print("\nChecking balances after transfer...")
    source_balance = await source_wallet.get_balance()
    dest_balance = await destination_wallet.get_balance()
    
    print(f"Source wallet ({source_wallet_name}) balance: {source_balance} SOL")
    print(f"Destination wallet ({destination_wallet_name}) balance: {dest_balance} SOL")

if __name__ == "__main__":
    asyncio.run(transfer_sol())