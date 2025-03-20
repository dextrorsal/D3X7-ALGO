import React, { createContext, useContext, useState, useEffect } from 'react';

interface WalletContextType {
  wallets: string[];
  selectedWallet: string | null;
  setSelectedWallet: (wallet: string) => void;
  loading: boolean;
  error: string | null;
}

const WalletContext = createContext<WalletContextType | undefined>(undefined);

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [wallets, setWallets] = useState<string[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWallets = async () => {
      try {
        console.log('Fetching wallets...');
        const response = await fetch('http://127.0.0.1:8000/api/wallets');
        console.log('Response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Failed to fetch wallets:', errorText);
          throw new Error(`Failed to fetch wallets: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Received wallets:', data);
        
        setWallets(data.wallets);
        if (data.wallets.length > 0) {
          setSelectedWallet(data.wallets[0]);
        }
      } catch (err) {
        console.error('Error fetching wallets:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch wallets');
      } finally {
        setLoading(false);
      }
    };

    fetchWallets();
  }, []);

  const value = {
    wallets,
    selectedWallet,
    setSelectedWallet,
    loading,
    error,
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const context = useContext(WalletContext);
  if (context === undefined) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
} 