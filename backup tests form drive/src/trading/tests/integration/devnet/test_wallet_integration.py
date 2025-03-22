"""
Integration tests for wallet functionality in devnet environment.
Tests both keypair and general wallet operations.
"""
import pytest
import asyncio
import json
import os
import base64
from pathlib import Path
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from src.utils.wallet import WalletManager
from src.utils.wallet.sol_wallet import SolanaWallet
from src.utils.wallet.encryption import WalletEncryption

@pytest.mark.asyncio
class TestWalletIntegration:
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment with devnet connection."""
        self.rpc_client = AsyncClient("https://api.devnet.solana.com")
        self.test_keypair = Keypair()
        self.wallet_path = Path.home() / ".config/solana/test-devnet.json"
        
        # Create test wallet configuration
        self.wallet_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.wallet_path, 'w') as f:
            json.dump([x for x in self.test_keypair.secret()], f)
        
        # Set up environment variables for testing
        os.environ["PRIVATE_KEY_PATH"] = str(self.wallet_path)
        os.environ["WALLET_PASSWORD"] = "test_password"
        
        # Initialize encryption
        self.encryption = WalletEncryption(os.environ["WALLET_PASSWORD"])
        
        yield
        
        # Cleanup
        if self.wallet_path.exists():
            self.wallet_path.unlink()
        await self.rpc_client.close()

    async def test_wallet_creation(self):
        """Test wallet creation and initialization."""
        wallet = WalletManager()
        assert wallet is not None
        
        # Create a new wallet
        wallet.add_wallet("MAIN", str(self.wallet_path))
        main_wallet = wallet.get_wallet("MAIN")
        assert main_wallet is not None
        await wallet.close()

    async def test_keypair_operations(self):
        """Test basic keypair operations."""
        wallet = SolanaWallet(
            keypair_path=str(self.wallet_path),
            name="TEST",
            keypair=self.test_keypair
        )
        assert str(wallet.get_public_key()) == str(self.test_keypair.pubkey())
        
        # Test message signing
        message = b"Test message"
        signature = wallet.sign_message(message)
        assert signature is not None

    async def test_wallet_balance(self):
        """Test balance checking functionality."""
        wallet = WalletManager()
        wallet.add_wallet("MAIN", str(self.wallet_path))
        main_wallet = wallet.get_wallet("MAIN")
        assert main_wallet is not None
        balance = await main_wallet.get_balance()
        assert isinstance(balance, float)
        assert balance >= 0
        await wallet.close()

    async def test_transaction_signing(self):
        """Test transaction signing capabilities."""
        wallet = WalletManager()
        wallet.add_wallet("MAIN", str(self.wallet_path))
        main_wallet = wallet.get_wallet("MAIN")
        assert main_wallet is not None
        
        # Create a simple transfer instruction
        recipient = Keypair().pubkey()
        tx = await main_wallet.create_transfer_tx(
            recipient=recipient,
            amount=0.001
        )
        assert tx is not None
        
        # Verify signature
        assert len(tx.signatures) > 0
        await wallet.close()

    async def test_wallet_encryption(self):
        """Test wallet encryption and decryption."""
        wallet = WalletManager()
        wallet.add_wallet("MAIN", str(self.wallet_path))
        main_wallet = wallet.get_wallet("MAIN")
        assert main_wallet is not None
        
        # Test config encryption
        test_config = {"test": "data"}
        encrypted = self.encryption.encrypt_wallet_config(test_config)
        decrypted = self.encryption.decrypt_wallet_config(encrypted)
        assert decrypted == test_config
        await wallet.close()

    async def test_multiple_wallets(self):
        """Test handling multiple wallet instances."""
        wallet_manager = WalletManager()
        
        # Add main wallet
        wallet_manager.add_wallet("MAIN", str(self.wallet_path))
        
        # Create and add a second wallet
        second_keypair = Keypair()
        second_wallet_path = Path.home() / ".config/solana/test-devnet2.json"
        second_wallet_path.parent.mkdir(parents=True, exist_ok=True)
        with open(second_wallet_path, 'w') as f:
            json.dump([x for x in second_keypair.secret()], f)
        
        wallet_manager.add_wallet("TEST", str(second_wallet_path))
        
        assert wallet_manager.get_wallet("MAIN") is not None
        assert wallet_manager.get_wallet("TEST") is not None
        
        # Cleanup
        if second_wallet_path.exists():
            second_wallet_path.unlink()
        await wallet_manager.close()

    async def test_error_handling(self):
        """Test wallet error handling."""
        # Test invalid keypair path
        with pytest.raises(Exception):
            wallet = WalletManager()
            wallet.add_wallet("INVALID", "invalid/path.json")

    async def test_wallet_persistence(self):
        """Test wallet data persistence."""
        wallet = WalletManager()
        wallet.add_wallet("MAIN", str(self.wallet_path))
        main_wallet = wallet.get_wallet("MAIN")
        assert main_wallet is not None
        
        # Save and reload wallet
        config = {"name": "MAIN", "path": str(self.wallet_path)}
        encrypted = self.encryption.encrypt_wallet_config(config)
        decrypted = self.encryption.decrypt_wallet_config(encrypted)
        assert decrypted == config
        await wallet.close()

    async def test_devnet_airdrop(self):
        """Test SOL airdrop on devnet."""
        wallet = WalletManager()
        wallet.add_wallet("MAIN", str(self.wallet_path))
        main_wallet = wallet.get_wallet("MAIN")
        assert main_wallet is not None
        
        # Request airdrop
        initial_balance = await main_wallet.get_balance()
        await main_wallet.request_airdrop(0.1)  # Request 0.1 SOL
        await asyncio.sleep(2)  # Wait for confirmation
        
        # Verify balance increased
        new_balance = await main_wallet.get_balance()
        assert new_balance > initial_balance
        await wallet.close()

    async def test_network_switching(self):
        """Test RPC network switching capabilities."""
        networks = [
            "https://api.devnet.solana.com",
            "https://api.testnet.solana.com"
        ]
        
        for network in networks:
            client = AsyncClient(network)
            try:
                # Test basic connection
                response = await client.get_version()
                assert response.version is not None
                await client.close()
            except Exception as e:
                await client.close()
                raise e 