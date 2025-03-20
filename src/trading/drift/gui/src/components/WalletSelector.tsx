import React from 'react';
import {
  Select,
  Box,
  Text,
  VStack,
  HStack,
  useColorModeValue,
} from '@chakra-ui/react';
import { useWallet } from '../contexts/WalletContext';

export function WalletSelector() {
  const { selectedWallet, setSelectedWallet, walletList } = useWallet();
  const bgColor = useColorModeValue('gray.700', 'gray.800');
  const borderColor = useColorModeValue('gray.600', 'gray.700');

  return (
    <Box
      p={4}
      bg={bgColor}
      borderRadius="lg"
      borderWidth="1px"
      borderColor={borderColor}
    >
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="bold">
            Select Wallet
          </Text>
        </HStack>
        <Select
          value={selectedWallet}
          onChange={(e) => setSelectedWallet(e.target.value)}
          bg="gray.900"
          borderColor="gray.600"
          _hover={{ borderColor: 'drift.500' }}
        >
          {walletList.map((wallet) => (
            <option key={wallet} value={wallet}>
              {wallet}
            </option>
          ))}
        </Select>
      </VStack>
    </Box>
  );
} 