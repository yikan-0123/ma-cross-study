"""Step 6: MU case study + analogue search ("deep below a still-rising MA200 after a big run").
Usage: python 06_mu_case.py <panel_dir> <out_dir>"""
import sys, numpy as np, pandas as pd
P, O = sys.argv[1], sys.argv[2]
adj = pd.read_pickle(f"{P}/adj.pkl"); mem = pd.read_pickle(f"{P}/mem.pkl")
px = adj.ffill()
ret = adj.pct_change(fill_method=None)
ma120 = adj.rolling(120, min_periods=120).mean(); ma200 = adj.rolling(200, min_periods=200).mean()
d120 = adj / ma120 - 1; d200 = adj / ma200 - 1
s120 = ma120 / ma120.shift(20) - 1; s200 = ma200 / ma200.shift(20) - 1
r250 = px / px.shift(250) - 1
peak250 = px.rolling(250, min_periods=120).max(); dd = px / peak250 - 1
vol60 = ret.rolling(60).std() * np.sqrt(252)

mu = pd.DataFrame({"close_adj": adj.MU, "ma120": ma120.MU, "ma200": ma200.MU, "dist120": d120.MU, "dist200": d200.MU,
                   "ma120_slope20": s120.MU, "ma200_slope20": s200.MU, "ret250": r250.MU, "dd_from_250d_high": dd.MU, "vol60": vol60.MU})
print("MU latest:\n", mu.tail(1).T.round(4).to_string())
b = (adj.MU < ma120.MU); c = b & ~b.shift(1, fill_value=True)
b2 = (adj.MU < ma200.MU); c2 = b2 & ~b2.shift(1, fill_value=True)
print("last MA120 down-cross:", c[c].index[-3:].date, " last MA200 down-cross:", c2[c2].index[-3:].date)
mu.to_csv(f"{O}/mu_state.csv")

# analogue: S&P 500 member, >=20% below MA200, MA200 still rising, 12m return > +30%, drawdown from 1y high <= -40%
cond = (d200 < -0.20) & (s200 > 0) & (r250 > 0.30) & (dd <= -0.40) & mem & (adj.index >= "1996-01-01")[:, None]
first = cond & ~(cond.astype(float).rolling(120, min_periods=1).max().shift(1).fillna(0).astype(bool))
s = first.stack(); s = s[s]; idx = s.index
A = pd.DataFrame(index=idx).reset_index(); A.columns = ["date", "ticker"]
spy = px["SPY"]
for h in (20, 60, 120, 250):
    A[f"r{h}"] = (px.shift(-h) / px - 1).stack(future_stack=True).reindex(idx).values
    A[f"x{h}"] = A[f"r{h}"] - (spy.shift(-h) / spy - 1).reindex(A.date).values
fmin = px.iloc[::-1].rolling(120, min_periods=1).min().iloc[::-1].shift(-1) / px - 1
A["mae120"] = fmin.stack(future_stack=True).reindex(idx).values
# did the price regain MA200 within 250 days?
reg = (adj > ma200).astype(float).iloc[::-1].rolling(250, min_periods=1).max().iloc[::-1].shift(-1)
A["regain200_250d"] = reg.stack(future_stack=True).reindex(idx).values
A = A.dropna(subset=["r60"])
print("\nanalogues n=", len(A), " distinct tickers", A.ticker.nunique(), " distinct months", A.date.dt.to_period("M").nunique())
print(A[["r20", "r60", "r120", "r250", "x60", "x120", "x250", "mae120"]].describe(percentiles=[.1, .25, .5, .75, .9]).round(3).to_string())
print("P(regain MA200 within 250d) =", round(A.regain200_250d.mean(), 3))
print(A.sort_values("date").tail(15).round(3).to_string())
A.to_csv(f"{O}/mu_analogues.csv", index=False)
