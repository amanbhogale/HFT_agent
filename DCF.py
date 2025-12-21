import yfinance as yf
import pandas as pd
import numpy as np
t = yf.Ticker("RELIANCE.NS")  # Example ticker for Reliance Industries
print("INCOME\n" , t.financials.head())
print("CASHFLOW\n" , t.cashflow.head())
print("BALANCE SHEET\n" , t.balance_sheet.head())

def fetch_financials(symbol: str):
    """
    symbol: e.g. 'RELIANCE.NS', 'TCS.NS'
    returns: dict with last 4y financial statements
    """
    t = yf.Ticker(symbol)
    # yfinance gives most recent columns first
    income = t.financials      # EBIT, Tax, etc.
    cashflow = t.cashflow      # Dep, CapEx
    balance = t.balance_sheet  # Debt, cash
    info = t.info

    return {
        "income": income,
        "cashflow": cashflow,
        "balance": balance,
        "info": info,
    }

def estimate_fcf_series(financials: dict, years: int = 4) -> pd.Series:
    """
    Compute historical FCFF from statements (rough approximation).
    FCFF = EBIT*(1-T) + D&A - CapEx - ΔNWC
    """
    cf = financials["cashflow"]
    if "Free Cash Flow" in cf.index:
        raise ValueError("No 'Free cash flow' row in cashflow statement")
    fcff = cf.loc["Free cash flow"].astype(float)
    fcff = fcff.dropna().iloc[:years]
    if fcff.empty:
        raise ValueError("No Free Cash Flow data available")
    return fcff.sort_index()

def dcf_intrinsic_value(
    last_fcf: float,
    growth_years: int = 5,
    growth_rate: float = 0.08,
    terminal_growth: float = 0.03,
    wacc: float = 0.11,
) -> float:
    """
    Very simplified FCFF DCF → enterprise value (no net-debt adjustment).
    """
    years = np.arange(1, growth_years + 1)
    fcfs = last_fcf * (1 + growth_rate) ** years

    # discount factors
    disc = 1 / (1 + wacc) ** years
    pv_fcfs = np.sum(fcfs * disc)

    # terminal value (Gordon growth on FCFF in year N+1)
    tv = fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_tv = tv / (1 + wacc) ** growth_years

    enterprise_value = pv_fcfs + pv_tv
    return enterprise_value


def intrinsic_value_per_share(symbol: str,
                              growth_rate: float = 0.08,
                              wacc: float = 0.11,
                              terminal_growth: float = 0.03):
    fin = fetch_financials(symbol)
    fcff_series = estimate_fcf_series(fin)
    if fcff_series.empty:
        raise ValueError("No FCFF data computed")

    last_fcf = fcff_series.iloc[-1]
    ev = dcf_intrinsic_value(
        last_fcf,
        growth_years=5,
        growth_rate=growth_rate,
        wacc=wacc,
        terminal_growth=terminal_growth,
    )

    info = fin["info"]
    net_debt = (info.get("totalDebt", 0) or 0) - (info.get("totalCash", 0) or 0)
    equity_value = ev - net_debt

    shares = info.get("sharesOutstanding") or info.get("floatShares")
    if not shares:
        raise ValueError("No share count available")

    value_per_share = equity_value / shares
    return {
        "symbol": symbol,
        "last_fcf": float(last_fcf),
        "enterprise_value": float(ev),
        "equity_value": float(equity_value),
        "value_per_share": float(value_per_share),
    }
if __name__ == "__main__":
    res = intrinsic_value_per_share("RELIANCE.NS",
                                    growth_rate=0.10,
                                    wacc=0.12,
                                    terminal_growth=0.04)
    print(res)


