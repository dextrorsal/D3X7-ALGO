import os
import json
import click
from pathlib import Path
import subprocess
from src.utils.wallet.encryption import WalletEncryption

TEST_CONFIG_DIR = os.path.expanduser("~/test_wallets")

def create_test_keypair():
    """Create a test Solana keypair"""
    result = subprocess.run(
        ["solana-keygen", "new", "--no-bip39-passphrase", "--force"],
        capture_output=True,
        text=True,
        cwd=TEST_CONFIG_DIR
    )
    if result.returncode == 0:
        return os.path.join(TEST_CONFIG_DIR, "id.json")
    return None

def setup_test_environment():
    """Set up test environment with dummy wallets"""
    # Create test directory if it doesn't exist
    os.makedirs(TEST_CONFIG_DIR, exist_ok=True)
    
    # Create test wallets
    test_wallets = {
        "test_wallet_1": {"strategy": "test_strategy_1"},
        "test_wallet_2": {"strategy": "test_strategy_2"},
    }
    
    for name, config in test_wallets.items():
        # Create keypair for each wallet
        keypair_path = os.path.join(TEST_CONFIG_DIR, f"{name}.json")
        result = subprocess.run(
            ["solana-keygen", "new", "--no-bip39-passphrase", "--force", "-o", keypair_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Save wallet config
            config["keypair_path"] = keypair_path
            config_path = os.path.join(TEST_CONFIG_DIR, f"{name}_config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            click.echo(f"✅ Created test wallet: {name}")
        else:
            click.echo(f"❌ Failed to create test wallet: {name}")

def test_encryption():
    """Test wallet encryption functionality"""
    # Test password
    test_password = "test_password123"
    
    try:
        # Initialize encryption
        encryption = WalletEncryption(test_password)
        
        # Test encrypting each wallet config
        for config_file in Path(TEST_CONFIG_DIR).glob("*_config.json"):
            try:
                # Load original config
                with open(config_file, 'r') as f:
                    original_config = json.load(f)
                
                # Encrypt config
                encrypted_path = config_file.with_suffix('.enc')
                if encryption.save_encrypted_config(original_config, str(encrypted_path)):
                    click.echo(f"✅ Successfully encrypted: {config_file.name}")
                    
                    # Test decryption
                    decrypted_config = encryption.load_encrypted_config(str(encrypted_path))
                    if decrypted_config == original_config:
                        click.echo(f"✅ Successfully decrypted: {encrypted_path.name}")
                    else:
                        click.echo(f"❌ Decryption verification failed: {encrypted_path.name}")
                else:
                    click.echo(f"❌ Failed to encrypt: {config_file.name}")
                    
            except Exception as e:
                click.echo(f"❌ Error testing encryption for {config_file.name}: {e}")
                
    except Exception as e:
        click.echo(f"❌ Error in encryption test: {e}")

def cleanup_test_environment():
    """Clean up test files"""
    try:
        # Remove all files in test directory
        for file in Path(TEST_CONFIG_DIR).glob("*"):
            file.unlink()
        click.echo("✅ Cleaned up test files")
    except Exception as e:
        click.echo(f"❌ Error cleaning up test files: {e}")

@click.group()
def cli():
    """Test script for wallet encryption"""
    pass

@cli.command()
def setup():
    """Set up test environment"""
    setup_test_environment()

@cli.command()
def test():
    """Run encryption tests"""
    test_encryption()

@cli.command()
def cleanup():
    """Clean up test environment"""
    cleanup_test_environment()

if __name__ == '__main__':
    cli() 