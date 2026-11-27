"""Step 4: Q4 lag between price turning points and MA signals; Q3 jump (earnings-type) share of variance.
Usage: python 04_lag_jump.py <panel_dir> <out_dir>"""
import sys, numpy as np, pandas as pd
P, O = sys.argv[1], sys.argv[2]
adj = pd.read_pickle(f"{P}/adj.pkl"); mem = pd.read_pickle(f"{P}/mem.pkl")
dates = adj.index
A = adj.values
M = mem.values
MA = {N: adj.rolling(N, min_periods=N).mean().values for N in (120, 200)}
W, LOOK = 126, 252
rows = []
for j, tk in enumerate(adj.columns):
    p = A[:, j]
    ok = ~np.isnan(p)
    if ok.sum() < 600:
        continue
    s = pd.Series(p)
    cmax = s.rolling(2 * W + 1, center=True, min_periods=W).max().values
    cmin = s.rolling(2 * W + 1, center=True, min_periods=W).min().values
    for kind in ("top", "bottom"):
        cand = np.flatnonzero((p == (cmax if kind == "top" else cmin)) & ok)
        for i in cand:
            if dates[i] < pd.Timestamp("1996-06-01") or not M[i, j] or i + LOOK >= len(p) or np.isnan(MA[200][i, j]):
                continue
            seg = p[i:i + LOOK + 1]
            if kind == "top":
                k = np.nanargmin(seg); move = seg[k] / p[i] - 1
                if move > -0.20: continue
            else:
                k = np.nanargmax(seg); move = seg[k] / p[i] - 1
                if move < 0.25: continue
            r = {"ticker": tk, "date": dates[i], "kind": kind, "move": move, "days_to_extreme": int(k)}
            for N in (120, 200):
                ma = MA[N][i:i + LOOK + 1, j]
                sig = np.flatnonzero(seg < ma) if kind == "top" else np.flatnonzero(seg > ma)
                sig = sig[sig > 0]
                if len(sig):
                    c = sig[0]
                    r[f"lag_cross{N}"] = int(c)
                    r[f"pnl_at_cross{N}"] = seg[c] / p[i] - 1          # move already done when the price signal fires
                    r[f"rest_after_cross{N}"] = seg[k] / seg[c] - 1 if c < k else 0.0  # move left to the extreme
                # MA turning point: extreme of MA between the price turn and the price extreme (+60d slack)
                end = min(len(ma), k + 60)
                mseg = ma[:end]
                if np.isnan(mseg).all():
                    continue
                t = int(np.nanargmax(mseg) if kind == "top" else np.nanargmin(mseg))
                r[f"lag_maturn{N}"] = t
                r[f"pnl_at_maturn{N}"] = seg[t] / p[i] - 1
                r[f"rest_after_maturn{N}"] = seg[k] / seg[t] - 1 if t < k else 0.0
            rows.append(r)
L = pd.DataFrame(rows)
L.to_parquet(f"{O}/turns.parquet")
pd.set_option("display.width", 250)
for kind in ("top", "bottom"):
    d = L[L.kind == kind]
    print(f"\n== {kind}: n={len(d)}  median move {d.move.median():.3f}, median days to extreme {d.days_to_extreme.median()}")
    cols = [c for c in L.columns if c.startswith(("lag_", "pnl_", "rest_"))]
    print(d[cols].describe(percentiles=[.25, .5, .75]).T[["count", "25%", "50%", "75%", "mean"]].round(3).to_string())

# ---- jump share of forward 60d variance (proxy for earnings / news days) for MA200 first-in-60d events
ev = pd.read_parquet(f"{O}/events.parquet")
ev = ev[(ev.ma == 200) & (ev.variant == "raw") & ev.first60]
R = adj.pct_change(fill_method=None).values
ci = {t: k for k, t in enumerate(adj.columns)}
di = {d: k for k, d in enumerate(dates)}
share1, share3 = [], []
for d, t in zip(ev.date, ev.ticker):
    i, j = di[d], ci[t]
    x = R[i + 1:i + 61, j]; x = x[~np.isnan(x)]
    if len(x) < 40:
        share1.append(np.nan); share3.append(np.nan); continue
    ss = (x ** 2).sum()
    srt = np.sort(x ** 2)[::-1]
    share1.append(srt[0] / ss); share3.append(srt[:3].sum() / ss)
ev["jump1"] = share1; ev["jump3"] = share3
print("\nshare of 60d realised variance from the single largest day: median %.3f, mean %.3f" % (np.nanmedian(share1), np.nanmean(share1)))
print("share from the 3 largest days: median %.3f, mean %.3f  (3/60 = 0.05 if returns were i.i.d. normal-ish)" % (np.nanmedian(share3), np.nanmean(share3)))
# does a big jump day explain extreme outcomes? sd of r60 by jump1 tercile
ev["jq"] = pd.qcut(ev["jump1"], 3, labels=["low", "mid", "high"])
print(ev.groupby("jq", observed=True)["r60"].agg(["size", "std", "mean"]).round(3).to_string())
ev[["date", "ticker", "dir", "jump1", "jump3", "r60"]].to_parquet(f"{O}/jumps.parquet")
