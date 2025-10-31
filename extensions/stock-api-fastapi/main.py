# -*- coding: utf-8 -*-
import os
from datetime import date
from typing import List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

prices = pd.read_csv(
    os.path.join(os.path.dirname(__file__), "prices.csv"),
    index_col=0,
    parse_dates=True,
)


def validate_ticker(ticker):
    if ticker not in prices["ticker"].unique():
        raise HTTPException(status_code=404, detail="Ticker not found")


class Tickers(BaseModel):
    tickers: list = Field(title="All available stock tickers")


class Stock(BaseModel):
    ticker: str = Field(..., title="Ticker of the stock")
    price: float = Field(..., title="Latest price of the stock")
    volatility: float = Field(..., title="Latest volatility of the stock price")


class Price(BaseModel):
    date: date
    high: float = Field(..., title="High price for this date")
    low: float = Field(..., title="Low price for this date")
    close: float = Field(..., title="Closing price for this date")
    volume: int = Field(..., title="Daily volume for this date")
    adjusted: float = Field(..., title="Split-adjusted price for this date")


app = FastAPI(
    title="Stocks API",
    description="The Stocks API provides pricing and volatility data for a "
    "limited number of US equities from 2010-2018",
)

resource = Resource.create({
    "service.name": "stock-fastapi-app",
    "service.version": "1.0.0",
    "deployment.environment": "dev"
})

# tracer provider
provider = TracerProvider(resource=resource)

# OTLP exporter
# at the very least OTEL_EXPORTER_OTLP_ENDPOINT should be set in the environment for the app.
otlp_exporter = OTLPSpanExporter()

# span processor
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

trace.set_tracer_provider(provider)

FastAPIInstrumentor.instrument_app(app)


@app.get("/stocks", response_model=Tickers)
async def tickers():
    tickers = prices["ticker"].unique().tolist()
    return {"tickers": tickers}


@app.get("/stocks/{ticker}", response_model=Stock)
async def ticker(ticker: str):
    validate_ticker(ticker)

    latest = prices.last_valid_index()
    ticker_prices = prices[prices["ticker"] == ticker]
    current_price = ticker_prices["close"][latest:].iloc[0].round(2)
    current_volatility = np.log(
        ticker_prices["adjusted"] / ticker_prices["adjusted"].shift(1)
    ).var()

    return {
        "ticker": ticker,
        "price": current_price,
        "volatility": current_volatility,
    }


@app.get("/stocks/{ticker}/history", response_model=List[Price])
async def history(ticker: str):
    validate_ticker(ticker)

    ticker_prices = prices[prices["ticker"] == ticker]
    ticker_prices.loc[:, "date"] = ticker_prices.index.to_numpy()
    return ticker_prices.to_dict("records")
