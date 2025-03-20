# Drift Protocol GUI

A modern, responsive interface for managing multiple Drift wallets and their subaccounts.

## Features

- Multi-wallet support (MAIN, KP, AG)
- Real-time account summaries
- Subaccount management
- Interactive balance displays
- Modern dark theme UI
- Responsive design

## Quick Start

```bash
# Install dependencies
npm install

# Start the development server
npm run dev

# Build for production
npm run build
```

## Structure

```
/gui
├── components/           # React components
│   ├── WalletSelector/  # Wallet selection UI
│   ├── AccountSummary/  # Account overview
│   ├── SubAccounts/     # Subaccount list
│   └── shared/          # Shared components
├── hooks/               # Custom React hooks
├── styles/             # CSS modules
└── utils/              # Helper functions
```

## Development

### Environment Setup

1. Create `.env` file:
```env
VITE_DRIFT_API_URL=http://localhost:8000
ENABLE_ENCRYPTION=true
```

2. Install dependencies:
```bash
npm install @chakra-ui/react @emotion/react @emotion/styled framer-motion
npm install @solana/web3.js driftpy
```

### Running the Development Server

```bash
npm run dev
```

The GUI will be available at `http://localhost:5173` 