# Drift Management Tools

This directory contains the management tools for interacting with Drift Protocol accounts, including a CLI interface and wallet management system.

## Quick Start

```bash
# List all available subaccounts
./drift_cli.py subaccount list MAIN

# Check balance for a specific subaccount
./drift_cli.py account balance MAIN 0

# Create a new subaccount
./drift_cli.py subaccount create MAIN 1 --name "Trading-Account"

# Show detailed info for a subaccount
./drift_cli.py subaccount info MAIN 0
```

## Configuration

### Environment Setup

1. **Required Environment Variables:**
   ```bash
   ENABLE_ENCRYPTION=true
   WALLET_PASSWORD=your_secure_password
   ```

2. **Directory Structure:**
   ```
   ~/.config/solana/drift/
   ├── wallets/              # Encrypted wallet files
   │   ├── main.enc         # Main wallet (encrypted)
   │   └── other.enc       # Other wallets
   └── config/              # Configuration files
       └── subaccounts.json # Subaccount configurations
   ```

### Wallet Management

The system supports encrypted wallet files (`.enc`) for enhanced security. Wallets are managed through the `WalletManager` class and can be:
- Encrypted using `WalletEncryption`
- Stored in the Drift directory
- Loaded automatically by the CLI

## Available Commands

### Account Management

```bash
# Balance Operations
./drift_cli.py account balance MAIN 0     # Check balance for main wallet, subaccount 0
./drift_cli.py account deposit MAIN --amount 1.0 --token SOL  # Deposit 1 SOL
./drift_cli.py account withdraw MAIN --amount 0.5 --token USDC  # Withdraw 0.5 USDC

# Options:
--force              # Skip confirmation prompts
--network devnet     # Specify network (default: devnet)
```

### Subaccount Management

```bash
# List Operations
./drift_cli.py subaccount list [WALLET_NAME]  # List all subaccounts
./drift_cli.py subaccount info MAIN 0         # Show detailed info

# Creation/Deletion
./drift_cli.py subaccount create MAIN 1 --name "Trading"  # Create new subaccount
./drift_cli.py subaccount delete MAIN 1 --force          # Delete subaccount config
```

### Wallet Operations

```bash
# List wallets
./drift_cli.py wallet list

# Show wallet details
./drift_cli.py wallet info MAIN
```

## Component Details

### 1. Drift CLI (`drift_cli.py`)

The main CLI interface providing command-line access to Drift functionality.

**Features:**
- Interactive command prompts
- Colored output for better readability
- Automatic wallet loading and decryption
- Transaction confirmation prompts

### 2. Wallet Manager (`drift_wallet_manager.py`)

Handles wallet operations and subaccount management.

**Key Features:**
- Secure wallet encryption/decryption
- Subaccount configuration management
- Network-specific settings

## Security Features

1. **Wallet Encryption:**
   - AES-256 encryption for wallet files
   - Password-protected access
   - Secure memory handling

2. **Transaction Safety:**
   ```bash
   # Safe deposit with confirmation
   ./drift_cli.py account deposit MAIN --amount 1.0 --token SOL

   # Force deposit (use with caution)
   ./drift_cli.py account deposit MAIN --amount 1.0 --token SOL --force
   ```

3. **Configuration Protection:**
   - Encrypted storage of sensitive data
   - Automatic cleanup of temporary files
   - Session-based authentication

## Integration with Drift Protocol

The management tools integrate directly with the Drift Protocol using:
- `DriftClient` for protocol interaction
- `DriftUser` for user account management
- Account subscription for real-time updates

### Market Support

```python
# Available Markets (Devnet)
SPOT_MARKETS = {
    "SOL-USDC": 1,
    "BTC-USDC": 2,
    "ETH-USDC": 3
}

PERP_MARKETS = {
    "SOL-PERP": 0,
    "BTC-PERP": 1,
    "ETH-PERP": 2
}
```

## Troubleshooting

### Common Issues

1. **Wallet Access:**
   ```bash
   Error: Failed to load wallet
   Solution: Check WALLET_PASSWORD environment variable
   ```

2. **Network Connection:**
   ```bash
   Error: Could not connect to Drift
   Solution: Verify network selection (devnet/mainnet)
   ```

3. **Account Initialization:**
   ```bash
   Error: User account not found
   Solution: Run account initialization first
   ```

### Debug Mode

Enable detailed logging:
```bash
export DRIFT_LOG_LEVEL=DEBUG
./drift_cli.py account balance MAIN 0
```

## Examples

### 1. Basic Account Setup
```bash
# Create and fund a new trading account
./drift_cli.py subaccount create MAIN 1 --name "Trading"
./drift_cli.py account deposit MAIN --amount 1.0 --token SOL --subaccount 1
```

### 2. Multi-Account Management
```bash
# List all subaccounts
./drift_cli.py subaccount list MAIN

# Check balances across accounts
for id in 0 1 2; do
    ./drift_cli.py account balance MAIN $id
done
```

### 3. Automated Operations
```bash
# Deposit without confirmation
./drift_cli.py account deposit MAIN --amount 0.5 --token SOL --force
``` 