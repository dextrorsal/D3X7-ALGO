"""
Compatibility shim for pyserum which uses the older solana package structure.
This file provides compatibility between the newer solders-based package and the older solana structure.
"""

import sys
import logging
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.types import TxOpts

logger = logging.getLogger(__name__)

# Create a mock module for solana.keypair
class KeypairModule:
    def __init__(self):
        self.Keypair = Keypair

# Create a mock module for solana.publickey
class PublicKeyModule:
    def __init__(self):
        self.PublicKey = Pubkey

# Create a mock module for solana.rpc.types
class RPCTypesModule:
    def __init__(self):
        self.TxOpts = TxOpts
        # Add the missing RPCResponse class
        class RPCResponse:
            def __init__(self, value=None):
                self.value = value
            
            def __repr__(self):
                return f"RPCResponse(value={self.value})"
        
        self.RPCResponse = RPCResponse

# Create a mock module for solana.sysvar
class SysvarModule:
    def __init__(self):
        # Create a constant for SYSVAR_RENT_PUBKEY
        # This is a well-known address in Solana
        self.SYSVAR_RENT_PUBKEY = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# Install the mock modules
sys.modules['solana.keypair'] = KeypairModule()
sys.modules['solana.publickey'] = PublicKeyModule()
sys.modules['solana.sysvar'] = SysvarModule()
# We don't want to completely override the existing module, just add to it
if 'solana.rpc.types' in sys.modules:
    sys.modules['solana.rpc.types'].RPCResponse = RPCTypesModule().RPCResponse
else:
    sys.modules['solana.rpc.types'] = RPCTypesModule()

logger.info("Solana compatibility shim installed for pyserum library.") 