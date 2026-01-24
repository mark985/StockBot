"""
Pydantic data models for stock and options data.
Provides validation and type safety for API responses.
"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class StockQuote(BaseModel):
    """Stock quote information."""

    symbol: str = Field(..., description="Stock ticker symbol")
    last_trade_price: float = Field(..., description="Last trade price")
    bid_price: Optional[float] = Field(None, description="Current bid price")
    ask_price: Optional[float] = Field(None, description="Current ask price")
    previous_close: Optional[float] = Field(None, description="Previous closing price")
    volume: Optional[int] = Field(None, description="Trading volume")
    updated_at: Optional[datetime] = Field(None, description="Last update time")

    @validator('last_trade_price', 'bid_price', 'ask_price', 'previous_close')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v


class PortfolioPosition(BaseModel):
    """Portfolio position information."""

    symbol: str = Field(..., description="Stock ticker symbol")
    quantity: float = Field(..., description="Number of shares owned")
    average_buy_price: float = Field(..., description="Average purchase price")
    current_price: Optional[float] = Field(None, description="Current market price")
    equity: Optional[float] = Field(None, description="Current equity value")
    percent_change: Optional[float] = Field(None, description="Percent change")
    equity_change: Optional[float] = Field(None, description="Dollar change")
    type: str = Field(default="stock", description="Position type")

    @property
    def market_value(self) -> Optional[float]:
        """Calculate current market value."""
        if self.current_price is not None:
            return self.quantity * self.current_price
        return None

    @property
    def total_cost(self) -> float:
        """Calculate total cost basis."""
        return self.quantity * self.average_buy_price

    @property
    def unrealized_pl(self) -> Optional[float]:
        """Calculate unrealized profit/loss."""
        if self.current_price is not None:
            return (self.current_price - self.average_buy_price) * self.quantity
        return None

    @property
    def is_covered_call_eligible(self) -> bool:
        """Check if position is eligible for covered calls (100+ shares)."""
        return self.quantity >= 100


class OptionContract(BaseModel):
    """Options contract information."""

    symbol: str = Field(..., description="Underlying stock symbol")
    strike_price: float = Field(..., description="Strike price")
    expiration_date: date = Field(..., description="Expiration date")
    option_type: str = Field(..., description="'call' or 'put'")

    # Pricing
    bid_price: Optional[float] = Field(None, description="Bid price")
    ask_price: Optional[float] = Field(None, description="Ask price")
    mark_price: Optional[float] = Field(None, description="Mark price (mid)")
    last_trade_price: Optional[float] = Field(None, description="Last trade price")

    # Greeks
    delta: Optional[float] = Field(None, description="Delta")
    gamma: Optional[float] = Field(None, description="Gamma")
    theta: Optional[float] = Field(None, description="Theta")
    vega: Optional[float] = Field(None, description="Vega")
    implied_volatility: Optional[float] = Field(None, description="Implied volatility")

    # Volume and interest
    volume: Optional[int] = Field(None, description="Daily volume")
    open_interest: Optional[int] = Field(None, description="Open interest")

    # Contract identifier
    contract_id: Optional[str] = Field(None, description="Unique contract identifier")

    @validator('option_type')
    def validate_option_type(cls, v):
        if v.lower() not in ['call', 'put']:
            raise ValueError("option_type must be 'call' or 'put'")
        return v.lower()

    @property
    def premium(self) -> Optional[float]:
        """Get best available premium (mark price preferred)."""
        return self.mark_price or self.last_trade_price or (
            (self.bid_price + self.ask_price) / 2 if self.bid_price and self.ask_price else None
        )

    @property
    def days_to_expiration(self) -> int:
        """Calculate days until expiration."""
        return (self.expiration_date - date.today()).days

    @property
    def is_liquid(self) -> bool:
        """Check if option has sufficient liquidity."""
        # Basic liquidity check: volume > 10 and open interest > 50
        return (
            self.volume is not None and self.volume > 10 and
            self.open_interest is not None and self.open_interest > 50
        )


class CoveredCallOpportunity(BaseModel):
    """Covered call opportunity with calculated metrics."""

    position: PortfolioPosition = Field(..., description="Underlying position")
    option: OptionContract = Field(..., description="Option contract")

    # Calculated metrics
    total_premium: float = Field(..., description="Total premium income (per contract)")
    roi_percent: float = Field(..., description="Return on investment %")
    annualized_return: float = Field(..., description="Annualized return %")
    max_profit: float = Field(..., description="Maximum profit if assigned")
    breakeven_price: float = Field(..., description="Breakeven stock price")
    downside_protection_percent: float = Field(..., description="Downside protection %")

    # Risk assessment
    assignment_probability: Optional[float] = Field(None, description="Probability of assignment")
    recommendation_score: Optional[float] = Field(None, description="AI recommendation score (1-10)")
    recommendation_reason: Optional[str] = Field(None, description="AI reasoning")

    @property
    def contracts_available(self) -> int:
        """Calculate number of contracts that can be sold."""
        return int(self.position.quantity // 100)


class Portfolio(BaseModel):
    """Complete portfolio information."""

    equity: float = Field(..., description="Total equity value")
    extended_hours_equity: Optional[float] = Field(None, description="Extended hours equity")
    cash: Optional[float] = Field(None, description="Available cash")
    buying_power: Optional[float] = Field(None, description="Buying power")
    positions: List[PortfolioPosition] = Field(default_factory=list, description="All positions")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")

    @property
    def total_value(self) -> float:
        """Calculate total portfolio value."""
        return self.equity + (self.cash or 0)

    @property
    def covered_call_eligible_positions(self) -> List[PortfolioPosition]:
        """Get positions eligible for covered calls (100+ shares)."""
        return [pos for pos in self.positions if pos.is_covered_call_eligible]

    @property
    def position_count(self) -> int:
        """Total number of positions."""
        return len(self.positions)


class MarketData(BaseModel):
    """General market data and conditions."""

    vix: Optional[float] = Field(None, description="VIX volatility index")
    spy_price: Optional[float] = Field(None, description="SPY price")
    market_trend: Optional[str] = Field(None, description="Market trend (bullish/bearish/neutral)")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
