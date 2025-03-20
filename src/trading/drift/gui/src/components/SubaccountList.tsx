import React, { useEffect, useState } from 'react';
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  Badge,
  useToast,
} from '@chakra-ui/react';
import { useWallet } from '../contexts/WalletContext';

interface Subaccount {
  wallet_name: string;
  subaccount_id: number;
  name: string;
  network: string;
  status: string;
  balance?: {
    spot_collateral: number;
    unrealized_pnl: number;
    total_collateral: number;
  };
}

export function SubaccountList() {
  const { selectedWallet } = useWallet();
  const [subaccounts, setSubaccounts] = useState<Subaccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const bgColor = useColorModeValue('gray.700', 'gray.800');
  const borderColor = useColorModeValue('gray.600', 'gray.700');

  useEffect(() => {
    const fetchSubaccounts = async () => {
      if (!selectedWallet) return;
      
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:8000/api/subaccounts/${selectedWallet}`);
        if (!response.ok) {
          throw new Error('Failed to fetch subaccounts');
        }
        const data = await response.json();
        
        // Fetch balance for each subaccount
        const subaccountsWithBalance = await Promise.all(
          data.subaccounts.map(async (subaccount: Subaccount) => {
            try {
              const balanceResponse = await fetch(
                `http://localhost:8000/api/balance/${subaccount.wallet_name}/${subaccount.subaccount_id}`
              );
              if (balanceResponse.ok) {
                const balanceData = await balanceResponse.json();
                return {
                  ...subaccount,
                  balance: {
                    spot_collateral: balanceData.spot_collateral,
                    unrealized_pnl: balanceData.unrealized_pnl,
                    total_collateral: balanceData.total_collateral,
                  },
                };
              }
              return subaccount;
            } catch (err) {
              console.error(`Failed to fetch balance for subaccount ${subaccount.subaccount_id}:`, err);
              return subaccount;
            }
          })
        );
        
        setSubaccounts(subaccountsWithBalance);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch subaccounts');
        toast({
          title: 'Error',
          description: err instanceof Error ? err.message : 'Failed to fetch subaccounts',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSubaccounts();
    // Set up polling every 10 seconds
    const interval = setInterval(fetchSubaccounts, 10000);
    return () => clearInterval(interval);
  }, [selectedWallet, toast]);

  const handleCreateSubaccount = async () => {
    if (!selectedWallet) return;
    
    try {
      const newId = subaccounts.length;
      const response = await fetch('http://localhost:8000/api/subaccounts/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_name: selectedWallet,
          subaccount_id: newId,
          name: `Subaccount ${newId}`,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create subaccount');
      }

      toast({
        title: 'Success',
        description: 'New subaccount created successfully',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to create subaccount',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  if (loading && subaccounts.length === 0) {
    return (
      <Box p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
        <Text>Loading subaccounts...</Text>
      </Box>
    );
  }

  if (error && subaccounts.length === 0) {
    return (
      <Box p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
        <Text color="red.400">Error: {error}</Text>
      </Box>
    );
  }

  return (
    <Box p={4} bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="bold">
            Subaccounts
          </Text>
          <Button size="sm" colorScheme="drift" onClick={handleCreateSubaccount}>
            New Subaccount
          </Button>
        </HStack>

        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>ID</Th>
                <Th>Name</Th>
                <Th isNumeric>Balance</Th>
                <Th isNumeric>PnL</Th>
                <Th>Network</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {subaccounts.map((subaccount) => (
                <Tr key={subaccount.subaccount_id}>
                  <Td>{subaccount.subaccount_id}</Td>
                  <Td>{subaccount.name}</Td>
                  <Td isNumeric>
                    ${subaccount.balance
                      ? (subaccount.balance.total_collateral / 1e6).toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })
                      : '0.00'}
                  </Td>
                  <Td isNumeric>
                    <Text
                      color={
                        subaccount.balance && subaccount.balance.unrealized_pnl > 0
                          ? 'green.400'
                          : subaccount.balance && subaccount.balance.unrealized_pnl < 0
                          ? 'red.400'
                          : undefined
                      }
                    >
                      ${subaccount.balance
                        ? (subaccount.balance.unrealized_pnl / 1e6).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })
                        : '0.00'}
                    </Text>
                  </Td>
                  <Td>{subaccount.network}</Td>
                  <Td>
                    <Badge colorScheme={subaccount.status === 'active' ? 'green' : 'gray'}>
                      {subaccount.status}
                    </Badge>
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      <Button size="xs" variant="outline">
                        View
                      </Button>
                      <Button size="xs" variant="outline" colorScheme="red">
                        Delete
                      </Button>
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </VStack>
    </Box>
  );
} 