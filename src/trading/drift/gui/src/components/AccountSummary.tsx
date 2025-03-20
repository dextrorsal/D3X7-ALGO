import React from 'react';
import {
  Box,
  Text,
  VStack,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useWallet } from '../contexts/WalletContext';

export function AccountSummary() {
  const { selectedWallet, accountData, isLoading, error } = useWallet();
  const bgColor = useColorModeValue('gray.700', 'gray.800');
  const borderColor = useColorModeValue('gray.600', 'gray.700');

  if (isLoading) {
    return (
      <Box
        p={4}
        bg={bgColor}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <VStack spacing={4} align="center">
          <Spinner size="xl" color="drift.500" />
          <Text>Loading account data...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="lg">
        <AlertIcon />
        {error}
      </Alert>
    );
  }

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
            Account Summary
          </Text>
          <Text color="drift.500" fontWeight="semibold">
            {selectedWallet}
          </Text>
        </HStack>

        <VStack spacing={6} align="stretch">
          <Stat>
            <StatLabel>Total Balance</StatLabel>
            <StatNumber fontSize="2xl" color="drift.500">
              ${accountData?.balance?.toLocaleString() ?? '0.00'}
            </StatNumber>
            <StatHelpText>Updated just now</StatHelpText>
          </Stat>

          {/* Add more stats here as needed */}
        </VStack>
      </VStack>
    </Box>
  );
} 