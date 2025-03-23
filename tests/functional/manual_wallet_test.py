"""
Manual test script for wallet functionality.
This script tests core wallet and RPC functionality without pytest dependencies.
"""
import asyncio
import os
import json
from pathlib import Path
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
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
    networks = ["devnet", "mainnet"]
    
    for network in networks:
        try:
            set_solana_network(network)
            client = await get_solana_client()
            version = await client.get_version()
            print(f"✅ Connected to {network}: {version}")
        except Exception as e:
            print(f"❌ Failed to connect to {network}: {str(e)}")

async def test_wallet_operations():
    """Test basic wallet operations and balances"""
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
            print(f"✅ Wallet pubkey: {current_wallet.pubkey}")
            
            # Test balance checking on both networks
            for network in ["devnet", "mainnet"]:
                try:
                    set_solana_network(network)
                    client = await get_solana_client()
                    balance = await client.get_balance(current_wallet.pubkey)
                    print(f"✅ {network} Balance: {balance.value / 1e9} SOL")
                except Exception as e:
                    print(f"❌ Failed to get {network} balance: {str(e)}")
            
            # Test loading keypair directly with detailed inspection
            keypair_path = os.getenv('MAIN_KEY_PATH', '/home/dex/.config/solana/keys/id.json')
            print(f"\nAnalyzing keypair at: {keypair_path}")
            print("-" * 50)
            
            if os.path.exists(keypair_path):
                print("✅ Keypair file found!")
                try:
                    # Read raw file content first
                    with open(keypair_path, 'rb') as f:
                        raw_content = f.read()
                    print(f"Raw file size: {len(raw_content)} bytes")
                    print(f"First few bytes (hex): {raw_content[:8].hex()}")
                    
                    # Try as text
                    try:
                        text_content = raw_content.decode('utf-8')
                        print("File appears to be text/JSON")
                        # Try parsing as JSON
                        try:
                            keypair_data = json.loads(text_content)
                            print("✅ Successfully parsed as JSON")
                            print(f"JSON data length: {len(keypair_data)}")
                            print(f"JSON data type: {type(keypair_data)}")
                            if isinstance(keypair_data, list):
                                print(f"List length: {len(keypair_data)}")
                                print(f"First few elements: {keypair_data[:4]}...")
                                # Try creating Keypair from JSON array
                                keypair = Keypair.from_bytes(bytes(keypair_data))
                                print(f"\n✅ Successfully created Keypair from JSON array!")
                            else:
                                print("❌ JSON data is not an array")
                        except json.JSONDecodeError:
                            print("❌ Not valid JSON")
                    except UnicodeDecodeError:
                        print("File appears to be binary")
                        # Try direct binary loading
                        try:
                            keypair = Keypair.from_bytes(raw_content)
                            print(f"\n✅ Successfully created Keypair from binary!")
                        except Exception as e:
                            print(f"❌ Failed to create Keypair from binary: {str(e)}")
                            # Try converting binary to list
                            try:
                                keypair_data = list(raw_content)
                                keypair = Keypair.from_bytes(bytes(keypair_data))
                                print(f"\n✅ Successfully created Keypair from binary list!")
                            except Exception as e:
                                print(f"❌ Failed to create Keypair from binary list: {str(e)}")
                    
                    # If we got a keypair, verify it
                    if 'keypair' in locals():
                        print(f"Pubkey: {keypair.pubkey()}")
                        if str(keypair.pubkey()) == str(current_wallet.pubkey):
                            print("✅ Keypair pubkey matches wallet manager!")
                            print("Found the correct keypair!")
                        else:
                            print("❌ Keypair pubkey does NOT match wallet manager")
                            print(f"Expected: {current_wallet.pubkey}")
                            print(f"Got: {keypair.pubkey()}")
                    
                except Exception as e:
                    print(f"❌ Failed to analyze keypair: {str(e)}")
                    print(f"Error details: {str(e.__class__.__name__)}")
                    import traceback
                    print(traceback.format_exc())
            else:
                print(f"❌ Keypair file not found at: {keypair_path}")
            
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