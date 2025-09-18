import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tools.currency_tools import CurrencyTools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["currency"])

# Global currency tools instance (will be set by main.py)
currency_tools: CurrencyTools = None


class ConvertCurrencyRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: float


class FormatMoneyRequest(BaseModel):
    amount: float
    currency_code: str


def set_currency_tools(tools: CurrencyTools):
    """Set the currency tools instance."""
    global currency_tools
    currency_tools = tools


@router.get("/supported-currencies")
async def get_supported_currencies() -> Dict[str, Any]:
    """Get list of all supported currency codes."""
    try:
        result = currency_tools.get_supported_currencies()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error in get_supported_currencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert")
async def convert_currency(request: ConvertCurrencyRequest) -> Dict[str, Any]:
    """Convert currency from one type to another."""
    try:
        result = currency_tools.convert_currency(
            request.from_currency,
            request.to_currency, 
            request.amount
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error in convert_currency: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exchange-rates")
async def get_exchange_rates() -> Dict[str, Any]:
    """Get current exchange rates for all supported currencies."""
    try:
        result = currency_tools.get_exchange_rates()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error in get_exchange_rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/format-money")
async def format_money(request: FormatMoneyRequest) -> Dict[str, Any]:
    """Format money amount with currency symbol."""
    try:
        formatted = currency_tools.format_money(request.amount, request.currency_code)
        return {
            "success": True,
            "formatted_amount": formatted,
            "original_amount": request.amount,
            "currency_code": request.currency_code
        }
    except Exception as e:
        logger.error(f"Error in format_money: {e}")
        raise HTTPException(status_code=400, detail=str(e)) 