# Solana Wallet CLI

A modern, user-friendly CLI tool for managing multiple Solana wallets with beautiful terminal output, comprehensive token support, real-time monitoring, and secure encryption.

## 🚀 Quick Start

```bash
# 1. Check your current wallet balances
python -m utils.wallet.wallet_cli balance

# 2. Switch to devnet for testing
python -m utils.wallet.wallet_cli network devnet

# 3. Request an airdrop (devnet only)
python -m utils.wallet.wallet_cli airdrop 2 --wallet MAIN

# 4. Launch the GUI Watch Mode
python -m utils.wallet.wallet_cli watch
```

## 🌟 Features

- Beautiful, color-coded terminal output for better readability
- Multi-wallet management with support for trading strategies
- Network switching between mainnet, devnet, and testnet
- Balance checking for SOL and SPL tokens with formatted numbers
- Secure keypair handling with encryption and permissions validation
- Easy-to-use transfer functionality between wallets
- Real-time GUI monitoring with multi-wallet support
- Multi-currency display (SOL, USD, CAD) with live price updates
- Modern dark-themed GUI with transaction history

## 💻 GUI Watch Mode

The new GUI watch mode provides real-time monitoring of your wallets:

- **Multi-Wallet Dashboard**: Monitor multiple wallets simultaneously
- **Live Balance Updates**: See your balances in SOL, USD, and CAD
- **Transaction History**: View recent transactions with status indicators
- **Modern Dark Theme**: Professional-grade UI with sleek design
- **Interactive Features**:
  - Wallet selector dropdown
  - Closeable wallet tabs
  - Real-time refresh button
  - Color-coded transaction status

```bash
# Launch GUI Watch Mode
python -m utils.wallet.wallet_cli watch          # Monitor all wallets
python -m utils.wallet.wallet_cli watch MAIN     # Monitor specific wallet
```

## 💡 Common Use Cases

1. **Managing Multiple Trading Wallets**
   ```bash
   # Set up trading wallets
   python -m utils.wallet.wallet_cli add KP_TRADE ~/.config/solana/trading/kp_trade.json
   python -m utils.wallet.wallet_cli add AG_TRADE ~/.config/solana/trading/ag_trade.json
   
   # Check all wallet balances at once
   python -m utils.wallet.wallet_cli balance
   
   # Transfer SOL between wallets
   python -m utils.wallet.wallet_cli transfer 1 AG_TRADE --from-wallet MAIN
   
   # Monitor wallets in real-time with GUI
   python -m utils.wallet.wallet_cli watch
   ```

2. **Network Management**
   ```bash
   # Start with devnet for testing
   python -m utils.wallet.wallet_cli network devnet
   
   # Get some test SOL
   python -m utils.wallet.wallet_cli airdrop 2 --wallet KP_TRADE
   
   # Check balances
   python -m utils.wallet.wallet_cli balance
   
   # Switch to mainnet when ready
   python -m utils.wallet.wallet_cli network mainnet
   ```

3. **Wallet Operations**
   ```bash
   # List all configured wallets
   python -m utils.wallet.wallet_cli list
   
   # Check specific wallet balance
   python -m utils.wallet.wallet_cli balance
   
   # Transfer between wallets
   python -m utils.wallet.wallet_cli transfer 0.1 KP_TRADE --from-wallet MAIN
   ```

## 📚 Core Components

### 1. Wallet CLI (`wallet_cli.py`)
Your main interface for all wallet operations:

```bash
# Basic Operations
python -m utils.wallet.wallet_cli balance                               # Check all wallet balances
python -m utils.wallet.wallet_cli add KP_TRADE ~/.config/solana/trading/kp_trade.json
python -m utils.wallet.wallet_cli transfer 1 AG_TRADE --from-wallet KP_TRADE
python -m utils.wallet.wallet_cli airdrop 1 --wallet MAIN              # Devnet only

# Network Operations
python -m utils.wallet.wallet_cli network devnet                       # Switch to devnet
python -m utils.wallet.wallet_cli network mainnet                      # Switch to mainnet

# GUI Operations
python -m utils.wallet.wallet_cli watch                               # Launch GUI monitor
```

### 2. Balance Display
The balance command shows a beautiful, formatted output with multi-currency support:
```
═══════════════════════════════════════════════════════════════════════
💫 SOLANA DEVNET WALLET BALANCES
═══════════════════════════════════════════════════════════════════════

🔑 Wallet: MAIN
📍 Address: wgfSHT...VAuoc6
💰 Balances:
   ◎ 15.4541 Solana
   $ 1,236.33 USD
   $ 1,669.04 CAD

🔑 Wallet: KP_TRADE
📍 Address: 5mN4XG...dRp3r5
💰 Balances:
   ◎ 6.0000 Solana
   $ 480.00 USD
   $ 648.00 CAD
```

## 📁 Configuration

### 1. Environment Setup
Create a `.env` file:
```env
# Your wallet paths
PRIVATE_KEY_PATH=~/.config/solana/id.json

# RPC endpoints (optional - defaults to public endpoints)
MAINNET_RPC_URL=https://api.mainnet-beta.solana.com
DEVNET_RPC_URL=https://api.devnet.solana.com
TESTNET_RPC_URL=https://api.testnet.solana.com

# Optional: Custom encryption key for wallet files
WALLET_ENCRYPTION_KEY=your-secure-encryption-key
```

### 2. Wallet Directory Structure
```
~/.config/solana/
├── id.json                  # Main wallet (encrypted)
└── trading/                 # Trading wallets
    ├── kp_trade.json       # (encrypted)
    └── ag_trade.json       # (encrypted)
```

## 🔒 Security Best Practices

1. **Keypair Protection**
   ```bash
   # Set correct permissions for all wallet files
   chmod 600 ~/.config/solana/id.json
   chmod 600 ~/.config/solana/trading/*.json
   
   # Ensure wallet files are encrypted
   python -m utils.wallet.wallet_cli verify-encryption
   ```

2. **Safe Testing Process**
   ```bash
   # 1. Always start on devnet
   python -m utils.wallet.wallet_cli network devnet
   
   # 2. Test your operations
   python -m utils.wallet.wallet_cli airdrop 1 --wallet MAIN
   python -m utils.wallet.wallet_cli transfer 0.1 KP_TRADE --from-wallet MAIN
   
   # 3. Verify balances in GUI
   python -m utils.wallet.wallet_cli watch
   
   # 4. Switch to mainnet only when ready
   python -m utils.wallet.wallet_cli network mainnet
   ```

## 🐛 Troubleshooting

Common issues and solutions:

1. **GUI Not Launching**
   ```bash
   # Install required dependencies
   pip install PyQt6
   
   # Verify Python path
   export PYTHONPATH=/path/to/your/project
   ```

2. **Balance Not Showing**
   ```bash
   # Verify network connection
   python -m utils.wallet.wallet_cli network devnet
   
   # Check wallet permissions and encryption
   python -m utils.wallet.wallet_cli verify-encryption
   ```

3. **Transfer Failed**
   ```bash
   # Check source wallet has enough balance
   python -m utils.wallet.wallet_cli balance
   
   # Verify you're on the right network
   python -m utils.wallet.wallet_cli network devnet  # for testing
   ```

4. **Airdrop Failed**
   ```bash
   # Ensure you're on devnet
   python -m utils.wallet.wallet_cli network devnet
   
   # Try smaller amounts (1-2 SOL)
   python -m utils.wallet.wallet_cli airdrop 1 --wallet MAIN
   ```

## 📋 Testing

```bash
# 1. Switch to devnet
python -m utils.wallet.wallet_cli network devnet

# 2. Get test SOL
python -m utils.wallet.wallet_cli airdrop 1 --wallet MAIN

# 3. Test transfers
python -m utils.wallet.wallet_cli transfer 0.1 KP_TRADE --from-wallet MAIN

# 4. Monitor in GUI
python -m utils.wallet.wallet_cli watch

# 5. Verify balances
python -m utils.wallet.wallet_cli balance
```

## 🎨 GUI Customization

The watch mode GUI can be customized through environment variables:

```env
# GUI Theme Colors
GUI_PRIMARY_COLOR=#03E1FF    # Solana blue
GUI_BACKGROUND=#2b2b2b       # Dark background
GUI_TEXT_COLOR=#FFFFFF       # White text

# Update Intervals (milliseconds)
GUI_BALANCE_UPDATE=5000      # Balance update interval
GUI_PRICE_UPDATE=60000       # Price update interval
```