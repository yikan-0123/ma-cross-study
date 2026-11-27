"""Step 5: entry/exit rules backtest vs buy-and-hold, with costs.
Per-stock trend filters on point-in-time S&P 500 members (equal-weight slots, idle slots in cash at 0%),
plus index-level (SPY) timing and an MU single-stock case.
Signal is computed at close t, position held from close t+lag (lag=1 default; lag=2 = one extra day delay).
Usage: python 05_backtest.py <panel_dir> <out_dir>"""
import sys, numpy as np, pandas as pd
P, O = sys.argv[1], sys.argv[2]
adj = pd.read_pickle(f"{P}/adj.pkl"); mem = pd.read_pickle(f"{P}/mem.pkl")
COST = 0.0010            # 10 bp per side (commission + half-spread + impact, large caps)
START = "1996-01-01"
ret = adj.pct_change(fill_method=None)
ma = {N: adj.rolling(N, min_periods=N).mean() for N in (50, 120, 200)}
vol60 = ret.rolling(60, min_periods=40).std() * np.sqrt(252)
spy = adj["SPY"]; spy_ma200 = spy.rolling(200).mean()

def hyst(enter, exit_):
    s = pd.DataFrame(np.nan, index=enter.index, columns=enter.columns)
    s = s.mask(enter, 1.0).mask(exit_, 0.0)
    return s.ffill().fillna(0.0)

above = {N: adj > ma[N] for N in ma}
below = {N: adj < ma[N] for N in ma}
c3a = above[200] & above[200].shift(1, fill_value=False) & above[200].shift(2, fill_value=False)
c3b = below[200] & below[200].shift(1, fill_value=False) & below[200].shift(2, fill_value=False)
mom = adj.shift(21) / adj.shift(252) - 1
signals = {
    "Buy & hold (EW members)": pd.DataFrame(1.0, index=adj.index, columns=adj.columns),
    "Price > MA200": above[200].astype(float),
    "Price > MA120": above[120].astype(float),
    "MA200 ±2% band": hyst(adj > ma[200] * 1.02, adj < ma[200] * 0.98),
    "MA200 3-day confirm": hyst(c3a, c3b),
    "Price > MA200 & MA200 rising": (above[200] & (ma[200] > ma[200].shift(20))).astype(float),
    "MA50 > MA200 (golden cross)": (ma[50] > ma[200]).astype(float),
    "12-1m momentum > 0 (TSMOM)": (mom > 0).astype(float),
    "Index filter: SPY > MA200": pd.DataFrame(np.repeat((spy > spy_ma200).values[:, None], adj.shape[1], 1), index=adj.index, columns=adj.columns).astype(float),
    "Vol-managed: w = min(1, 25%/vol60)": (0.25 / vol60).clip(upper=1.0),
}

def run(sig, lag=1, cost=COST):
    w_slot = sig.shift(lag).where(mem.shift(1, fill_value=False)).fillna(0.0)    # position held over day t
    n = mem.shift(1, fill_value=False).sum(axis=1).replace(0, np.nan)
    r = ret.fillna(0.0)
    gross = (w_slot * r).sum(axis=1) / n
    turn = w_slot.diff().abs().sum(axis=1) / n
    net = gross - turn * cost
    expo = w_slot.sum(axis=1) / n
    return net.loc[START:], turn.loc[START:], expo.loc[START:]

def stats(r, turn=None, expo=None):
    r = r.dropna(); eq = (1 + r).cumprod()
    yrs = len(r) / 252
    out = {"CAGR": eq.iloc[-1] ** (1 / yrs) - 1, "Vol": r.std() * np.sqrt(252),
           "Sharpe(rf=0)": r.mean() / r.std() * np.sqrt(252), "MaxDD": (eq / eq.cummax() - 1).min()}
    out["Calmar"] = out["CAGR"] / -out["MaxDD"]
    if turn is not None: out["Turnover/yr"] = turn.sum() / yrs
    if expo is not None: out["Avg exposure"] = expo.mean()
    return out

rows, curves, sub = [], {}, []
for name, sig in signals.items():
    net, turn, expo = run(sig)
    rows.append({"strategy": name, **stats(net, turn, expo)})
    curves[name] = (1 + net).cumprod()
    net2, _, _ = run(sig, lag=2)
    rows[-1]["CAGR lag+1d"] = stats(net2)["CAGR"]
    net0, _, _ = run(sig, cost=0.0)
    rows[-1]["CAGR no cost"] = stats(net0)["CAGR"]
    for a, b in (("1996", "2007"), ("2008", "2016"), ("2017", "2026")):
        s = stats(net.loc[a:b]); sub.append({"strategy": name, "period": f"{a}-{b}", "CAGR": s["CAGR"], "MaxDD": s["MaxDD"], "Sharpe": s["Sharpe(rf=0)"]})
T = pd.DataFrame(rows).set_index("strategy")
pd.set_option("display.width", 250)
print(T.round(3).to_string()); T.to_csv(f"{O}/backtest.csv")
S = pd.DataFrame(sub).pivot(index="strategy", columns="period")
print(S.round(3).to_string()); S.to_csv(f"{O}/backtest_sub.csv")
pd.DataFrame(curves).to_parquet(f"{O}/curves.parquet")

# ---- index-level and MU single-stock timing
def single(tk, N=None, band=0.0, cost=COST, start=START):
    p = adj[tk].dropna(); r = p.pct_change().fillna(0)
    if N is None:
        pos = pd.Series(1.0, index=p.index)
    else:
        m = p.rolling(N).mean()
        if band:
            pos = pd.Series(np.nan, index=p.index).mask(p > m * (1 + band), 1.0).mask(p < m * (1 - band), 0.0).ffill().fillna(0)
        else:
            pos = (p > m).astype(float)
    pos = pos.shift(1).fillna(0)
    net = pos * r - pos.diff().abs().fillna(0) * cost
    return stats(net.loc[start:], pos.diff().abs().loc[start:], pos.loc[start:]), (1 + net.loc[start:]).cumprod()
srows = []
for tk in ("SPY", "MU"):
    for lab, N, band in (("Buy & hold", None, 0), ("Price>MA200", 200, 0), ("Price>MA120", 120, 0), ("MA200 ±2% band", 200, .02), ("MA120 ±2% band", 120, .02)):
        s, eq = single(tk, N, band)
        srows.append({"ticker": tk, "rule": lab, **s})
        curves[f"{tk} {lab}"] = eq
Sx = pd.DataFrame(srows); print(Sx.round(3).to_string()); Sx.to_csv(f"{O}/single.csv")
pd.DataFrame(curves).to_parquet(f"{O}/curves.parquet")

# ---- sensitivity: idle cash earns the 1-3y Treasury ETF (SHY) return, 2002-08 onward (SHY's inception)
shy = adj["SHY"].pct_change(fill_method=None).fillna(0)
crow = []
for name, sig in signals.items():
    net, turn, expo = run(sig)
    a = net.loc["2002-08-01":]; e = expo.loc["2002-08-01":]
    withcash = a + (1 - e) * shy.loc["2002-08-01":]
    crow.append({"strategy": name, "CAGR cash=0 (2002-08+)": stats(a)["CAGR"], "CAGR cash=SHY": stats(withcash)["CAGR"],
                 "Sharpe cash=SHY": stats(withcash)["Sharpe(rf=0)"], "MaxDD cash=SHY": stats(withcash)["MaxDD"]})
C = pd.DataFrame(crow).set_index("strategy"); print(C.round(3).to_string()); C.to_csv(f"{O}/backtest_cash.csv")
