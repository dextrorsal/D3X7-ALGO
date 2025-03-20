from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))

from src.trading.drift.account_manager import DriftAccountManager
from src.trading.drift.management.drift_wallet_manager import DriftWalletManager

app = FastAPI()

# Configure CORS with specific origins
origins = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
drift_wallet_manager = DriftWalletManager()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/api/wallets")
async def get_wallets():
    """Get list of available wallets"""
    try:
        logger.info("Fetching wallets...")
        wallets = ["MAIN", "TEST"]  # Temporary mock data for testing
        logger.info(f"Retrieved wallets: {wallets}")
        return JSONResponse(content={"wallets": wallets}, status_code=200)
    except Exception as e:
        logger.error(f"Error fetching wallets: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

class SubaccountCreate(BaseModel):
    wallet_name: str
    subaccount_id: int
    name: str

@app.get("/api/subaccounts/{wallet_name}")
async def get_subaccounts(wallet_name: str):
    """Get subaccounts for a wallet"""
    try:
        subaccounts = drift_wallet_manager.list_subaccounts(wallet_name)
        return {"subaccounts": subaccounts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/balance/{wallet_name}/{subaccount_id}")
async def get_balance(wallet_name: str, subaccount_id: int):
    """Get balance for a specific subaccount"""
    try:
        manager = DriftAccountManager(wallet_name)
        await manager.setup(subaccount_id)
        
        # Get user info
        drift_user = manager.drift_client.get_user()
        if not drift_user:
            raise HTTPException(status_code=404, detail="User not found")
            
        user = drift_user.get_user_account()
        
        # Get collateral info
        spot_collateral = drift_user.get_spot_market_asset_value(
            None,
            include_open_orders=True
        )
        unrealized_pnl = drift_user.get_unrealized_pnl(False)
        total_collateral = drift_user.get_total_collateral()
        
        # Get positions
        positions = []
        for position in user.spot_positions:
            if position.scaled_balance != 0:
                market = manager.drift_client.get_spot_market_account(position.market_index)
                if market:
                    token_amount = position.scaled_balance / (10 ** market.decimals)
                    positions.append({
                        "market_index": position.market_index,
                        "amount": token_amount
                    })
        
        return {
            "authority": str(user.authority),
            "subaccount_id": user.sub_account_id,
            "name": user.name.decode() if user.name else None,
            "spot_collateral": spot_collateral,
            "unrealized_pnl": unrealized_pnl,
            "total_collateral": total_collateral,
            "positions": positions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if manager.drift_client:
            await manager.drift_client.unsubscribe()

@app.post("/api/subaccounts/create")
async def create_subaccount(subaccount: SubaccountCreate):
    """Create a new subaccount"""
    try:
        result = drift_wallet_manager.create_subaccount(
            subaccount.wallet_name,
            subaccount.subaccount_id,
            subaccount.name,
            "devnet"
        )
        if result:
            return {"success": True, "message": f"Successfully created subaccount {subaccount.subaccount_id}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create subaccount")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/deposit")
async def deposit(wallet_name: str, subaccount_id: int, amount: float, token: str = "SOL"):
    """Deposit funds into a subaccount"""
    try:
        manager = DriftAccountManager(wallet_name)
        await manager.setup(subaccount_id)
        
        if token.upper() == "SOL":
            tx_sig = await manager.deposit_sol(amount)
            if tx_sig:
                return {"message": f"Successfully deposited {amount} SOL", "tx_sig": tx_sig}
            else:
                raise HTTPException(status_code=500, detail="Deposit failed")
        else:
            raise HTTPException(status_code=400, detail=f"Token {token} deposits not implemented yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if manager.drift_client:
            await manager.drift_client.unsubscribe()

@app.post("/api/withdraw")
async def withdraw(wallet_name: str, subaccount_id: int, amount: float, token: str = "SOL"):
    """Withdraw funds from a subaccount"""
    try:
        manager = DriftAccountManager(wallet_name)
        await manager.setup(subaccount_id)
        
        if token.upper() == "SOL":
            tx_sig = await manager.withdraw_sol(amount)
            if tx_sig:
                return {"message": f"Successfully withdrew {amount} SOL", "tx_sig": tx_sig}
            else:
                raise HTTPException(status_code=500, detail="Withdrawal failed")
        else:
            raise HTTPException(status_code=400, detail=f"Token {token} withdrawals not implemented yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if manager.drift_client:
            await manager.drift_client.unsubscribe()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 