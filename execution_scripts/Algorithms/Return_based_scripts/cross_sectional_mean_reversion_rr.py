"""
Cross-Sectional Mean Reversion Backtest (Relative Return Strategy)
====================================================================
Strategy Logic:
  - Universe: S&P 500 sector ETFs (or any basket of tickers)
  - Signal:   Each period, rank all assets by their lookback return
              relative to the cross-sectional mean (z-score of returns)
  - Position: Short top-N overperformers, Long bottom-N underperformers
              (i.e., bet on reversion toward the cross-sectional mean)
  - Rebalance: Weekly or Monthly

Dependencies (install before running):
    pip install yfinance pandas numpy matplotlib seaborn
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 0.  CONFIGURATION
# ─────────────────────────────────────────────
USE_LIVE_DATA = True       # Set False to use synthetic data (no internet needed)

TICKERS = [
    'RELIANCE.NS', 'HDFCBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'ICICIBANK.NS',
    'TCS.NS', 'BAJFINANCE.NS', 'LT.NS', 'HINDUNILVR.NS', 'INFY.NS',
    'MARUTI.NS', 'AXISBANK.NS', 'SUNPHARMA.NS', 'KOTAKBANK.NS', 'M&M.NS',
    'ITC.NS', 'TITAN.NS', 'HCLTECH.NS', 'ULTRACEMCO.NS', 'NTPC.NS',
    'ASIANPAINT.NS', 'NESTLEIND.NS', 'POWERGRID.NS', 'TECHM.NS', 'ONGC.NS',
    'TATACONSUM.NS', 'HCLTECH.NS', 'DIVISLAB.NS', 'COALINDIA.NS', 'JSWSTEEL.NS',
    'WIPRO.NS', 'DRREDDY.NS', 'APOLLOHOSP.NS', 'TMCV.NS', 'EICHERMOT.NS',
    'HEROMOTOCO.NS', 'BRITANNIA.NS', 'SHRIRAMFIN.NS', 'CIPLA.NS', 'GRASIM.NS',
    'HDFCLIFE.NS', 'BPCL.NS', 'LTIM.NS', 'ADANIPORTS.NS', 'INDUSINDBK.NS'
]

START_DATE     = "2015-01-01"
END_DATE       = "2026-03-03"
LOOKBACK       = 2          # weeks: formation period for ranking
HOLDING        = 1          # weeks: holding period
N_LONGS        = 10         # number of assets to go long
N_SHORTS       = 10         # number of assets to go short
TRANSACTION_COST = 0.0005    # 5 bps per side
INITIAL_CAPITAL  = 1_000_000


# ─────────────────────────────────────────────
# 1.  DATA DOWNLOAD  (or synthetic fallback)
# ─────────────────────────────────────────────
path = "data/sp500_sector_etfs.csv"  # local cache path for downloaded data


def download_prices(tickers, start, end, path=None):
    """Download adjusted close prices via yfinance."""
    try:
        import yfinance as yf
        print(f"Downloading data for {len(tickers)} tickers from Yahoo Finance...")
        raw = yf.download(tickers, start=start, end=end,
                          auto_adjust=True, progress=False)["Close"]
        raw = raw.dropna(how="all")
        print(f"  Downloaded {len(raw)} daily rows, "
              f"{raw.shape[1]} tickers ({raw.isna().mean().mean()*100:.1f}% NaN)")
        if path:
            os.makedirs(os.path.dirname(path) , exist_ok=True)
            raw.to_csv(path)
            print(f"  Saved raw data to {path}")
        return raw
    except Exception as e:
        print(f"  yfinance failed ({e}). Falling back to synthetic data.")
        return None


def synthetic_prices(tickers, start, end, seed=42):
    """Generate correlated GBM price paths for testing."""
    rng   = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    n, k  = len(dates), len(tickers)
    mu    = 0.07 / 252          # 7% annual drift
    sigma = 0.15 / np.sqrt(252) # 15% annual vol

    # Induce moderate cross-sectional correlation
    corr  = 0.5 * np.ones((k, k)) + (1 - 0.5) * np.eye(k)
    L     = np.linalg.cholesky(corr)
    z     = rng.standard_normal((n, k)) @ L.T
    log_r = mu - 0.5 * sigma**2 + sigma * z
    prices = 100 * np.exp(np.cumsum(log_r, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ─────────────────────────────────────────────
# 2.  STRATEGY ENGINE
# ─────────────────────────────────────────────
def resample_weekly(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.resample("W-FRI").last().dropna(how="all")


def compute_cross_sectional_zscore(returns: pd.DataFrame) -> pd.DataFrame:
    """Z-score each row (time period) across assets."""
    mu  = returns.mean(axis=1)
    std = returns.std(axis=1).replace(0, np.nan)
    return returns.sub(mu, axis=0).div(std, axis=0)


def build_signals(weekly_prices: pd.DataFrame,
                  lookback: int, n_long: int, n_short: int) -> pd.DataFrame:
    """
    For every rebalance date compute long/short weights.
    Weights are equal-weighted within the long and short legs,
    normalized so gross exposure = 1 (each leg = 0.5 gross).
    """
    # Formation-period return (lookback weeks)
    form_ret = weekly_prices.pct_change(lookback).shift(1)  # no look-ahead

    # Cross-sectional z-score
    zscores  = compute_cross_sectional_zscore(form_ret)

    weights  = pd.DataFrame(0.0, index=zscores.index, columns=zscores.columns)

    for date in zscores.index:
        row = zscores.loc[date].dropna()
        if len(row) < n_long + n_short:
            continue
        ranked  = row.rank()
        longs   = ranked.nsmallest(n_long).index    # lowest z-score → long
        shorts  = ranked.nlargest(n_short).index    # highest z-score → short
        weights.loc[date, longs]  =  1.0 / n_long  * 0.5
        weights.loc[date, shorts] = -1.0 / n_short * 0.5

    return weights


def backtest(weekly_prices: pd.DataFrame,
             weights: pd.DataFrame,
             transaction_cost: float,
             initial_capital: float) -> dict:
    """
    Simulate portfolio P&L with transaction costs.
    Returns a dict with equity curve, trades, and analytics.
    """
    # Weekly forward returns for each asset
    fwd_ret = weekly_prices.pct_change().shift(-1)  # return earned next week

    port_ret = (weights * fwd_ret).sum(axis=1)

    # Transaction costs: cost applies on turnover
    turnover = weights.diff().abs().sum(axis=1) / 2   # one-way turnover
    cost     = turnover * transaction_cost

    net_ret  = port_ret - cost

    # Equity curve
    equity   = initial_capital * (1 + net_ret).cumprod()
    equity.iloc[0] = initial_capital

    return {
        "gross_returns": port_ret,
        "net_returns":   net_ret,
        "costs":         cost,
        "turnover":      turnover,
        "equity":        equity,
        "weights":       weights,
    }


# ─────────────────────────────────────────────
# 3.  PERFORMANCE METRICS
# ─────────────────────────────────────────────
def performance_metrics(net_ret: pd.Series,
                         equity:  pd.Series,
                         freq:    int = 52) -> pd.Series:
    r = net_ret.dropna()

    total_ret  = equity.iloc[-1] / equity.iloc[0] - 1
    ann_ret    = (1 + r.mean()) ** freq - 1
    ann_vol    = r.std() * np.sqrt(freq)
    sharpe     = ann_ret / ann_vol if ann_vol else np.nan

    roll_max   = equity.cummax()
    drawdown   = equity / roll_max - 1
    max_dd     = drawdown.min()

    calmar     = ann_ret / abs(max_dd) if max_dd else np.nan
    win_rate   = (r > 0).mean()
    avg_win    = r[r > 0].mean()
    avg_loss   = r[r < 0].mean()
    profit_fac = abs(avg_win / avg_loss) if avg_loss else np.nan

    years      = len(r) / freq
    n_trades   = (r != 0).sum()

    return pd.Series({
        "Period":               f"{equity.index[0].date()} → {equity.index[-1].date()}",
        "Years":                f"{years:.1f}",
        "Total Return":         f"{total_ret*100:.1f}%",
        "Ann. Return":          f"{ann_ret*100:.1f}%",
        "Ann. Volatility":      f"{ann_vol*100:.1f}%",
        "Sharpe Ratio":         f"{sharpe:.2f}",
        "Max Drawdown":         f"{max_dd*100:.1f}%",
        "Calmar Ratio":         f"{calmar:.2f}",
        "Win Rate":             f"{win_rate*100:.1f}%",
        "Avg Win":              f"{avg_win*100:.2f}%",
        "Avg Loss":             f"{avg_loss*100:.2f}%",
        "Profit Factor":        f"{profit_fac:.2f}",
        "Active Weeks":         str(n_trades),
    })


# ─────────────────────────────────────────────
# 4.  VISUALISATION
# ─────────────────────────────────────────────
COLORS = {
    "equity":   "#2196F3",
    "dd":       "#F44336",
    "bar_pos":  "#4CAF50",
    "bar_neg":  "#F44336",
    "heat":     "RdYlGn",
}

def plot_results(results: dict, metrics: pd.Series,
                 weekly_prices: pd.DataFrame, title: str = ""):

    eq  = results["equity"]
    nr  = results["net_returns"].dropna()
    wts = results["weights"]
    dd  = eq / eq.cummax() - 1

    fig = plt.figure(figsize=(18, 20), facecolor="#0f1117")
    fig.patch.set_facecolor("#0f1117")
    gs  = gridspec.GridSpec(4, 2, figure=fig,
                            hspace=0.50, wspace=0.35,
                            left=0.07, right=0.97,
                            top=0.93, bottom=0.05)

    def ax_style(ax, title_text=""):
        ax.set_facecolor("#1a1d27")
        ax.tick_params(colors="#cccccc", labelsize=9)
        ax.spines[:].set_color("#333344")
        ax.xaxis.label.set_color("#aaaaaa")
        ax.yaxis.label.set_color("#aaaaaa")
        if title_text:
            ax.set_title(title_text, color="#e0e0e0", fontsize=11, pad=8)

    # ── 4.1  Equity Curve ──────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(eq.index, eq / 1e6, color=COLORS["equity"], lw=1.8, label="Strategy NAV")
    ax1.fill_between(eq.index, eq / 1e6, alpha=0.15, color=COLORS["equity"])
    ax1.set_ylabel("NAV ($ millions)", color="#aaaaaa")
    ax1_style_title = (f"Cross-Sectional Mean Reversion  |  "
                       f"Lookback={LOOKBACK}W  Hold={HOLDING}W  "
                       f"Long/Short {N_LONGS}/{N_SHORTS}")
    ax_style(ax1, ax1_style_title)
    ax1.legend(facecolor="#1a1d27", labelcolor="#cccccc", fontsize=9)

    # ── 4.2  Drawdown ──────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, :])
    ax2.fill_between(dd.index, dd * 100, 0, color=COLORS["dd"], alpha=0.7)
    ax2.set_ylabel("Drawdown (%)", color="#aaaaaa")
    ax_style(ax2, "Drawdown")

    # ── 4.3  Weekly Return Distribution ───────────────────────────────
    ax3 = fig.add_subplot(gs[2, 0])
    colors_bar = [COLORS["bar_pos"] if x >= 0 else COLORS["bar_neg"]
                  for x in nr]
    ax3.bar(nr.index, nr * 100, color=colors_bar, width=5, alpha=0.8)
    ax3.axhline(0, color="#555555", lw=0.8)
    ax3.set_ylabel("Return (%)", color="#aaaaaa")
    ax_style(ax3, "Weekly Net Returns")

    # ── 4.4  Return Histogram ──────────────────────────────────────────
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.hist(nr * 100, bins=40, color=COLORS["equity"],
             edgecolor="#0f1117", alpha=0.85)
    ax4.axvline(0, color="white", lw=1, ls="--")
    ax4.set_xlabel("Weekly Return (%)", color="#aaaaaa")
    ax4.set_ylabel("Frequency", color="#aaaaaa")
    ax_style(ax4, "Return Distribution")

    # Add normal overlay
    mu_r, sd_r = nr.mean() * 100, nr.std() * 100
    x_pdf = np.linspace(nr.min() * 100 - 1, nr.max() * 100 + 1, 200)
    pdf   = (np.exp(-0.5 * ((x_pdf - mu_r) / sd_r) ** 2)
             / (sd_r * np.sqrt(2 * np.pi)))
    n_obs = len(nr)
    bin_w = (nr.max() - nr.min()) * 100 / 40
    ax4.plot(x_pdf, pdf * n_obs * bin_w,
             color="#FF9800", lw=1.5, ls="--", label="Normal fit")
    ax4.legend(facecolor="#1a1d27", labelcolor="#cccccc", fontsize=8)

    # ── 4.5  Average Weight Heatmap ────────────────────────────────────
    ax5 = fig.add_subplot(gs[3, 0])
    monthly_wts = (wts
                   .resample("ME").mean()
                   .iloc[-24:]          # last 24 months
                   .T)
    monthly_wts.columns = monthly_wts.columns.strftime("%b %y")
    sns.heatmap(monthly_wts, ax=ax5, cmap=COLORS["heat"],
                center=0, linewidths=0.3,
                cbar_kws={"shrink": 0.7},
                annot=False, fmt=".2f")
    ax5.set_title("Avg Weekly Weights (last 24 months)",
                  color="#e0e0e0", fontsize=11, pad=8)
    ax5.tick_params(colors="#cccccc", labelsize=7.5)
    ax5.set_facecolor("#1a1d27")

    # ── 4.6  Metrics Table ─────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[3, 1])
    ax6.axis("off")
    ax_style(ax6, "Performance Summary")

    rows = [[k, v] for k, v in metrics.items()]
    col_labels = ["Metric", "Value"]
    tbl = ax6.table(cellText=rows,
                    colLabels=col_labels,
                    cellLoc="left",
                    loc="center",
                    bbox=[0.0, 0.0, 1.0, 1.0])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)

    for (r_idx, c_idx), cell in tbl.get_celld().items():
        cell.set_facecolor("#1a1d27" if r_idx > 0 else "#2a2d3e")
        cell.set_edgecolor("#333344")
        cell.set_text_props(color="#e0e0e0" if r_idx > 0 else "#ffffff")

    fig.suptitle("Cross-Sectional Mean Reversion Backtest  ·  Yahoo Finance",
                 color="white", fontsize=14, y=0.97, fontweight="bold")

    out_path = "cross_sectional_mr_backtest.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"\nChart saved → {out_path}")
    return out_path


# ─────────────────────────────────────────────
# 5.  SENSITIVITY ANALYSIS  (optional)
# ─────────────────────────────────────────────
def sensitivity_analysis(weekly_prices: pd.DataFrame,
                          lookbacks=(2, 4, 8, 13, 26),
                          n_sides=(2, 3, 4, 5)):
    """Grid search over lookback × portfolio-size combinations."""
    print("\nRunning sensitivity analysis …")
    rows = []
    for lb in lookbacks:
        for n in n_sides:
            if 2 * n > len(weekly_prices.columns):
                continue
            wts = build_signals(weekly_prices, lb, n, n)
            res = backtest(weekly_prices, wts,
                           TRANSACTION_COST, INITIAL_CAPITAL)
            m   = performance_metrics(res["net_returns"], res["equity"])
            rows.append({
                "Lookback (W)":  lb,
                "N Long/Short":  n,
                "Ann. Return":   float(m["Ann. Return"].strip("%")),
                "Sharpe":        float(m["Sharpe Ratio"]),
                "Max DD":        float(m["Max Drawdown"].strip("%")),
            })
    df = pd.DataFrame(rows)
    # Pivot for Sharpe
    pivot = df.pivot(index="Lookback (W)",
                     columns="N Long/Short",
                     values="Sharpe")
    print("\nSharpe Ratio Grid (Lookback × N Long/Short):")
    print(pivot.to_string())

    # Heatmap
    fig, axes = plt.subplots(1, 3, figsize=(16, 5),
                             facecolor="#0f1117")
    fig.patch.set_facecolor("#0f1117")
    for ax, metric, cmap in zip(
            axes,
            ["Ann. Return", "Sharpe", "Max DD"],
            ["RdYlGn",      "RdYlGn", "RdYlGn_r"]):
        pv = df.pivot(index="Lookback (W)", columns="N Long/Short", values=metric)
        sns.heatmap(pv, ax=ax, cmap=cmap, annot=True, fmt=".1f",
                    linewidths=0.5, cbar_kws={"shrink": 0.8})
        ax.set_title(metric, color="white", pad=6)
        ax.set_facecolor("#1a1d27")
        ax.tick_params(colors="#cccccc")

    fig.suptitle("Sensitivity Analysis", color="white",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    out = "sensitivity_analysis.png"
    plt.savefig(out, dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"Sensitivity chart saved → {out}")


# ─────────────────────────────────────────────
# 6.  MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Cross-Sectional Mean Reversion Backtest")
    print("=" * 60)

    # ── Data ──────────────────────────────────────────────────────────
    if USE_LIVE_DATA:
        prices = download_prices(TICKERS, START_DATE, END_DATE)

    if not USE_LIVE_DATA or prices is None:
        print("Using synthetic price data …")
        prices = synthetic_prices(TICKERS, START_DATE, END_DATE)

    weekly = resample_weekly(prices)
    print(f"\nWeekly bars: {len(weekly)} rows  |  Tickers: {list(weekly.columns)}")

    # ── Strategy ──────────────────────────────────────────────────────
    weights = build_signals(weekly, LOOKBACK, N_LONGS, N_SHORTS)
    results = backtest(weekly, weights, TRANSACTION_COST, INITIAL_CAPITAL)

    # ── Metrics ───────────────────────────────────────────────────────
    metrics = performance_metrics(results["net_returns"], results["equity"])
    print("\n── Performance Summary ──────────────────────────────────")
    for k, v in metrics.items():
        print(f"  {k:<22} {v}")

    # ── Turnover ──────────────────────────────────────────────────────
    avg_turn = results["turnover"].mean()
    print(f"\n  Avg Weekly Turnover      {avg_turn*100:.1f}%")
    print(f"  Avg Weekly Tcost         {results['costs'].mean()*100:.3f}%")

    # ── Plots ─────────────────────────────────────────────────────────
    chart_path = plot_results(results, metrics, weekly)

    # ── Sensitivity (optional — comment out to skip) ──────────────────
    sensitivity_analysis(weekly)

    print("\nDone ✓")
    return results, metrics


if __name__ == "__main__":
    main()
