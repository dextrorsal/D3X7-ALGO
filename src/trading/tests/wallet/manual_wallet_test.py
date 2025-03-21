"""
Manual test script for wallet functionality.
This script tests core wallet and RPC functionality without pytest dependencies.
"""
import asyncio
import os
from pathlib import Path
from solana.rpc.async_api import AsyncClient
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import get_solana_client, set_solana_network
from src.utils.wallet.encryption import WalletEncryption

async def test_rpc_connection():
    """Test basic RPC connection"""
    print("\n1. Testing RPC Connection...")
    try:
        client = await get_solana_client("devnet")
        version = await client.get_version()
        print(f"✅ RPC Connection successful: {version}")
    except Exception as e:
        print(f"❌ RPC Connection failed: {str(e)}")

async def test_network_switching():
    """Test network switching capabilities"""
    print("\n2. Testing Network Switching...")
    networks = ["devnet", "testnet"]
    
    for network in networks:
        try:
            set_solana_network(network)
            client = await get_solana_client()
            version = await client.get_version()
            print(f"✅ Connected to {network}: {version}")
        except Exception as e:
            print(f"❌ Failed to connect to {network}: {str(e)}")

async def test_wallet_operations():
    """Test basic wallet operations"""
    print("\n3. Testing Wallet Operations...")
    
    try:
        # Initialize wallet manager
        wallet_manager = WalletManager()
        
        # Test wallet listing
        wallets = wallet_manager.list_wallets()
        print(f"✅ Available wallets: {wallets}")
        
        # Get current wallet
        current_wallet = wallet_manager.get_current_wallet()
        if current_wallet:
            print(f"✅ Current wallet: {current_wallet.name}")
            
            # Test encryption using WalletEncryption
            password = os.getenv("WALLET_PASSWORD")
            if password:
                encryption = WalletEncryption(password)
                test_data = {"test": "message"}
                try:
                    encrypted = encryption.encrypt_wallet_config(test_data)
                    decrypted = encryption.decrypt_wallet_config(encrypted)
                    if decrypted == test_data:
                        print("✅ Encryption/Decryption working correctly")
                    else:
                        print("❌ Encryption/Decryption failed - data mismatch")
                except Exception as e:
                    print(f"❌ Encryption/Decryption failed: {str(e)}")
            else:
                print("❌ WALLET_PASSWORD environment variable not set")
        else:
            print("❌ No current wallet set")
            
    except Exception as e:
        print(f"❌ Wallet operations failed: {str(e)}")

async def main():
    """Run all tests"""
    print("Starting Manual Wallet Tests...")
    
    await test_rpc_connection()
    await test_network_switching()
    await test_wallet_operations()
    
    print("\nManual Wallet Tests Complete!")

if __name__ == "__main__":
    asyncio.run(main()) 