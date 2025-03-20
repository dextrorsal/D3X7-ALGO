import React from 'react';
import {
  ChakraProvider,
  Box,
  VStack,
  Text,
  Spinner,
  useToast,
  extendTheme,
} from '@chakra-ui/react';
import { WalletProvider } from './contexts/WalletContext';
import { SubaccountList } from './components/SubaccountList';

// Define the theme
const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    drift: {
      50: '#f7fafc',
      500: '#3182ce',
      600: '#2b6cb0',
    },
  },
});

function App() {
  return (
    <ChakraProvider theme={theme}>
      <Box minH="100vh" bg="gray.900" color="white" p={4}>
        <WalletProvider>
          <VStack spacing={8} align="stretch" maxW="1200px" mx="auto">
            <Text fontSize="2xl" fontWeight="bold">
              Drift Account Manager
            </Text>
            <SubaccountList />
          </VStack>
        </WalletProvider>
      </Box>
    </ChakraProvider>
  );
}

export default App; 