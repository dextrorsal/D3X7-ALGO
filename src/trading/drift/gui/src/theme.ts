import { extendTheme } from '@chakra-ui/react'

export const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      primary: '#00C097',
      secondary: '#7C3AED',
    },
    drift: {
      50: '#E6FFFA',
      100: '#B2F5EA',
      500: '#00C097',
      600: '#00A67E',
      700: '#008C65',
    },
  },
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'drift',
      },
    },
  },
  styles: {
    global: {
      body: {
        bg: 'gray.900',
        color: 'white',
      },
    },
  },
}) 