#!/usr/bin/env python3
"""
Check Drift collateral calculation in detail to understand discrepancies.
"""

import asyncio
import logging
import os
import json
from anchorpy import Wallet
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.keypair import load_keypair
from driftpy.types import TxParams
from solders.keypair import Keypair

# Configure logging - simple format
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Make sure we're using devnet
os.environ["DEVNET_RPC_ENDPOINT"] = "https://api.devnet.solana.com"

async def check_collateral_details():
    """Check Drift collateral calculation in detail"""
    drift_client = None
    
    try:
        # Load wallet from default location
        keypair_path = os.path.expanduser("~/.config/solana/id.json")
        if not os.path.exists(keypair_path):
            raise FileNotFoundError(f"Keypair not found at {keypair_path}")
            
        with open(keypair_path, 'r') as f:
            keypair_bytes = bytes(json.load(f))
            
        keypair = Keypair.from_bytes(keypair_bytes)
        wallet = Wallet(keypair)
        
        print("\n" + "="*60)
        print(f"DETAILED DRIFT COLLATERAL ANALYSIS")
        print("="*60)
        
        print(f"\n🔑 Wallet: {wallet.public_key}")
        
        # Connect to Solana
        rpc_url = os.environ.get("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com")
        connection = AsyncClient(rpc_url)
        
        # Check SOL balance
        balance_resp = await connection.get_balance(wallet.public_key)
        sol_balance = balance_resp.value / 1e9  # Convert lamports to SOL
        print(f"💰 SOL Balance: {sol_balance:.6f} SOL")
        
        # Create Drift client
        drift_client = DriftClient(
            connection,
            wallet,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket"),
            tx_params=TxParams(compute_units_price=85_000, compute_units=1_400_000)
        )
        
        # Subscribe to Drift
        await drift_client.subscribe()
        
        # Get market information
        print("\n📊 MARKET INFORMATION:")
        sol_price = None
        sol_initial_weight = None
        sol_maint_weight = None
        
        spot_markets = drift_client.get_spot_market_accounts()
        for market in spot_markets:
            market_name = bytes(market.name).decode('utf-8').strip()
            if market_name.upper() == "SOL":
                oracle_price = market.historical_oracle_data.last_oracle_price / (10 ** 6)
                sol_price = oracle_price
                sol_initial_weight = market.initial_asset_weight / (2**16)
                sol_maint_weight = market.maintenance_asset_weight / (2**16)
                
                print(f"   SOL Price: ${oracle_price:.2f}")
                print(f"   Market Index: {market.market_index}")
                print(f"   Decimals: {market.decimals}")
                print(f"   Initial Asset Weight: {sol_initial_weight:.4f}")
                print(f"   Maintenance Asset Weight: {sol_maint_weight:.4f}")
                
                # Additional market parameters that might affect collateral
                print(f"   Initial Liability Weight: {market.initial_liability_weight / (2**16):.4f}")
                print(f"   Maintenance Liability Weight: {market.maintenance_liability_weight / (2**16):.4f}")
                
                # Try to access other attributes safely
                try:
                    if hasattr(market, 'optimal_utilization'):
                        print(f"   Optimal Utilization: {market.optimal_utilization / (2**16):.4f}")
                except Exception:
                    pass
                
                break
        
        # Add user to client
        try:
            await drift_client.add_user(0)
        except Exception as e:
            print(f"Note: {e}")
        
        # Get user account data
        drift_user = drift_client.get_user()
        
        if drift_user:
            print("\n👤 USER ACCOUNT DETAILS:")
            
            # Get user account
            user_account = drift_user.get_user_account()
            
            # Show spot positions
            print("\n   Spot Positions:")
            for position in user_account.spot_positions:
                if position.market_index != 0:  # Skip USDC (index 0)
                    market = drift_client.get_spot_market_account(position.market_index)
                    if market:
                        market_name = bytes(market.name).decode('utf-8').strip()
                        
                        # Get detailed position info
                        token_amount = position.scaled_balance / (10 ** market.decimals)
                        oracle_price = market.historical_oracle_data.last_oracle_price / (10 ** 6)
                        
                        # Calculate values
                        raw_token_value = token_amount * oracle_price
                        
                        # Get weights
                        initial_weight = market.initial_asset_weight / (2**16)
                        maint_weight = market.maintenance_asset_weight / (2**16)
                        
                        # Calculate weighted values
                        initial_weighted_value = raw_token_value * initial_weight
                        maint_weighted_value = raw_token_value * maint_weight
                        
                        print(f"   • {market_name}:")
                        print(f"     - Token Amount: {token_amount:.9f}")
                        print(f"     - Oracle Price: ${oracle_price:.2f}")
                        print(f"     - Raw Value: ${raw_token_value:.2f}")
                        print(f"     - Initial Weight: {initial_weight:.4f}")
                        print(f"     - Maintenance Weight: {maint_weight:.4f}")
                        print(f"     - Initial Weighted Value: ${initial_weighted_value:.2f}")
                        print(f"     - Maintenance Weighted Value: ${maint_weighted_value:.2f}")
            
            # Get collateral information
            print("\n💵 COLLATERAL CALCULATION:")
            
            # Get the total collateral value
            total_collateral = drift_user.get_total_collateral() / 1e6
            
            print(f"   Total Collateral: ${total_collateral:.2f}")
            
            # Try to get more detailed collateral info
            try:
                # These methods might not be available in all versions of DriftPy
                print("\n   Detailed Collateral Breakdown:")
                
                # Get spot market account values
                spot_positions_value = 0
                for position in user_account.spot_positions:
                    if position.scaled_balance != 0:
                        market = drift_client.get_spot_market_account(position.market_index)
                        if market:
                            market_name = bytes(market.name).decode('utf-8').strip()
                            token_amount = position.scaled_balance / (10 ** market.decimals)
                            oracle_price = market.historical_oracle_data.last_oracle_price / (10 ** 6)
                            position_value = token_amount * oracle_price
                            spot_positions_value += position_value
                            print(f"     - {market_name} Position Value: ${position_value:.2f}")
                
                print(f"     - Total Spot Positions Value: ${spot_positions_value:.2f}")
                
                # Check if there's any unrealized funding
                try:
                    unrealized_funding = drift_user.get_unrealized_funding_pnl() / 1e6
                    print(f"     - Unrealized Funding PnL: ${unrealized_funding:.2f}")
                except:
                    pass
                
                # Check if there's any unrealized PnL
                try:
                    unrealized_pnl = drift_user.get_unrealized_pnl() / 1e6
                    print(f"     - Unrealized PnL: ${unrealized_pnl:.2f}")
                except:
                    pass
                
            except Exception as e:
                print(f"   Note: Could not get detailed collateral breakdown: {e}")
            
            # Get perp positions if any
            print("\n📈 PERPETUAL POSITIONS:")
            has_perp_positions = False
            for perp_position in user_account.perp_positions:
                if perp_position.base_asset_amount != 0:
                    has_perp_positions = True
                    perp_market = drift_client.get_perp_market_account(perp_position.market_index)
                    if perp_market:
                        market_name = bytes(perp_market.name).decode('utf-8').strip()
                        base_amount = perp_position.base_asset_amount / (10 ** 9)  # Usually 9 decimals
                        quote_amount = perp_position.quote_asset_amount / (10 ** 6)  # Usually 6 decimals
                        
                        print(f"   • {market_name}:")
                        print(f"     - Base Amount: {base_amount:.6f}")
                        print(f"     - Quote Amount: ${quote_amount:.2f}")
                        print(f"     - Unsettled PnL: ${perp_position.unsettled_pnl / 1e6:.2f}")
            
            if not has_perp_positions:
                print("   • No perpetual positions")
            
            # Show the final account value
            print("\n💰 ACCOUNT VALUE:")
            print(f"   Total Account Value (API): ${total_collateral:.2f}")
            
            # Calculate potential leveraged values
            print("\n🔍 POTENTIAL LEVERAGE CALCULATIONS:")
            
            # Common leverage factors
            leverage_factors = [5, 8, 8.3, 10, 20]
            for factor in leverage_factors:
                leveraged_value = total_collateral * factor
                print(f"   With {factor}x leverage: ${leveraged_value:.2f}")
            
            # Calculate the actual factor if UI shows $163.64
            ui_value = 163.64
            actual_factor = ui_value / total_collateral if total_collateral > 0 else 0
            print(f"   Actual factor (if UI shows ${ui_value:.2f}): {actual_factor:.2f}x")
            
            # Check if there are any other factors
            print("\n🔍 ADDITIONAL FACTORS:")
            try:
                free_collateral = drift_user.get_free_collateral() / 1e6
                print(f"   Free Collateral: ${free_collateral:.2f}")
            except:
                pass
                
            try:
                margin_requirement = drift_user.get_margin_requirement() / 1e6
                print(f"   Margin Requirement: ${margin_requirement:.2f}")
            except:
                pass
            
            # Check for any other account properties that might affect collateral
            print("\n🔎 OTHER ACCOUNT PROPERTIES:")
            try:
                # Check if there are any rewards or bonuses
                print(f"   Max Token Amount: {user_account.max_token_amount}")
                print(f"   Last Active Slot: {user_account.last_active_slot}")
                
                # Safely check for other properties
                if hasattr(user_account, 'settled_perp_pnl'):
                    print(f"   Settled Perp PnL: ${user_account.settled_perp_pnl / 1e6:.2f}")
                
                if hasattr(user_account, 'cumulative_spot_fees'):
                    print(f"   Cumulative Spot Fees: ${user_account.cumulative_spot_fees / 1e6:.2f}")
                
                if hasattr(user_account, 'cumulative_perp_fees'):
                    print(f"   Cumulative Perp Fees: ${user_account.cumulative_perp_fees / 1e6:.2f}")
            except Exception as e:
                print(f"   Error getting additional properties: {e}")
            
            # Explain the discrepancy
            print("\n🧩 EXPLAINING THE DISCREPANCY:")
            print(f"   1. The Drift UI shows a Subacct Value of ~$163.64")
            print(f"   2. Our API calculation shows a value of ${total_collateral:.2f}")
            print(f"   3. The difference suggests a leverage factor of ~{actual_factor:.2f}x")
            print(f"   4. This is likely because Drift applies leverage to your collateral for trading")
            print(f"   5. Your actual deposited value is ${total_collateral:.2f}, but you can trade with ~${ui_value:.2f}")
            
        else:
            print("\n❌ Could not retrieve Drift account information")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error checking collateral: {e}")
    finally:
        # Clean up
        if drift_client:
            try:
                await drift_client.unsubscribe()
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(check_collateral_details())