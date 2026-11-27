"""Step 2: event study of MA120 / MA200 crosses on point-in-time S&P 500 members, 1996-2026.
Usage: python 02_events.py <panel_dir> <out_dir>
Outputs: events.parquet (one row per event, with features + forward outcomes), baseline.parquet
"""
import sys, os
import numpy as np, pandas as pd

P, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
adj = pd.read_pickle(f"{P}/adj.pkl")
mem = pd.read_pickle(f"{P}/mem.pkl")
notrade = pd.read_pickle(f"{P}/notrade.pkl")
EV_START = pd.Timestamp("1996-01-01")
H = [5, 20, 60, 120, 250]

px = adj.ffill()                      # after delisting, last price is carried (= cash-out at last print)
alive = adj.notna()
ret = adj.pct_change(fill_method=None)
spy = px["SPY"]
spy_ret = spy.pct_change()

# forward returns (stock and SPY)
fwd = {h: px.shift(-h) / px - 1 for h in H}
spy_fwd = {h: spy.shift(-h) / spy - 1 for h in H}
# path extremes over next 120 / 250 days (max adverse / favourable excursion)
def fwd_ext(df, w, fn):
    r = df.iloc[::-1].rolling(w, min_periods=1)
    r = (r.min() if fn == "min" else r.max()).iloc[::-1]
    return r.shift(-1) / df - 1
mae120 = fwd_ext(px, 120, "min"); mfe120 = fwd_ext(px, 120, "max")
mae250 = fwd_ext(px, 250, "min"); mfe250 = fwd_ext(px, 250, "max")

# ex-ante features
vol60 = ret.rolling(60, min_periods=40).std() * np.sqrt(252)
ret250 = px / px.shift(250) - 1
ret21 = px / px.shift(21) - 1
rm = spy_ret
cov = ret.rolling(250, min_periods=150).cov(rm)
beta = cov.div(rm.rolling(250, min_periods=150).var(), axis=0)
spy_vol20 = rm.rolling(20).std() * np.sqrt(252)
spy_ma200 = spy.rolling(200).mean()
spy_up = (spy > spy_ma200)

frames = []
for N in (120, 200):
    ma = adj.rolling(N, min_periods=N).mean()
    valid = ma.notna() & alive
    below = (adj < ma) & valid
    above = (adj > ma) & valid
    slope20 = ma / ma.shift(20) - 1
    dist = adj / ma - 1
    prev_below = below.shift(1, fill_value=False)
    prev_above = above.shift(1, fill_value=False)
    cross_dn = below & prev_above
    cross_up = above & prev_below
    # 3-day confirmation: 3rd consecutive close on the new side
    conf_dn = below & below.shift(1, fill_value=False) & below.shift(2, fill_value=False) & ~below.shift(3, fill_value=True)
    conf_up = above & above.shift(1, fill_value=False) & above.shift(2, fill_value=False) & ~above.shift(3, fill_value=True)
    # 3% band: first close >3% beyond the MA since the last close on the other side
    band_dn_now = (adj < ma * 0.97) & valid
    band_up_now = (adj > ma * 1.03) & valid
    band_dn = band_dn_now & ~band_dn_now.shift(1, fill_value=False)
    band_up = band_up_now & ~band_up_now.shift(1, fill_value=False)
    # require that since the previous band event the price had crossed back (approximated by: price on the
    # other side of the MA at least once in the prior 60 days)
    band_dn &= above.rolling(60, min_periods=1).max().shift(1).fillna(0).astype(bool)
    band_up &= below.rolling(60, min_periods=1).max().shift(1).fillna(0).astype(bool)

    # re-cross (whipsaw) within 10 / 20 days after the event
    def fwd_any(df, w):
        return df.astype(float).iloc[::-1].rolling(w, min_periods=1).max().iloc[::-1].shift(-1).fillna(0) > 0
    back_above10 = fwd_any(above, 10); back_below10 = fwd_any(below, 10)
    back_above20 = fwd_any(above, 20); back_below20 = fwd_any(below, 20)
    # first raw cross in the previous 60 days? (declustering)
    prior_dn = cross_dn.astype(float).rolling(60, min_periods=1).sum().shift(1).fillna(0)
    prior_up = cross_up.astype(float).rolling(60, min_periods=1).sum().shift(1).fillna(0)

    elig = mem & ~notrade & (adj.index >= EV_START)[:, None]
    for direction, sigs in (("down", {"raw": cross_dn, "conf3": conf_dn, "band3": band_dn}),
                            ("up", {"raw": cross_up, "conf3": conf_up, "band3": band_up})):
        for var, sig in sigs.items():
            s = (sig & elig).stack()
            s = s[s]
            idx = s.index
            d = pd.DataFrame(index=idx).reset_index()
            d.columns = ["date", "ticker"]
            d["ma"] = N; d["dir"] = direction; d["variant"] = var
            def g(df):
                return df.stack(future_stack=True).reindex(idx).values
            for h in H:
                d[f"r{h}"] = g(fwd[h])
                d[f"x{h}"] = d[f"r{h}"] - spy_fwd[h].reindex(d["date"]).values
            d["mae120"] = g(mae120); d["mfe120"] = g(mfe120)
            d["mae250"] = g(mae250); d["mfe250"] = g(mfe250)
            d["vol60"] = g(vol60); d["beta"] = g(beta); d["ret250"] = g(ret250); d["ret21"] = g(ret21)
            d["slope20"] = g(slope20); d["dist"] = g(dist)
            d["spy_up"] = spy_up.reindex(d["date"]).values
            d["spy_vol20"] = spy_vol20.reindex(d["date"]).values
            d["spy_r60"] = spy_fwd[60].reindex(d["date"]).values
            if direction == "down":
                d["whip10"] = g(back_above10); d["whip20"] = g(back_above20); d["first60"] = g(prior_dn) == 0
            else:
                d["whip10"] = g(back_below10); d["whip20"] = g(back_below20); d["first60"] = g(prior_up) == 0
            frames.append(d)
            print(N, direction, var, len(d))

ev = pd.concat(frames, ignore_index=True)
ev.to_parquet(f"{OUT}/events.parquet")

# unconditional baseline: every member-day (subsampled every 5th trading day), same horizons
elig = mem & (adj.index >= EV_START)[:, None] & alive
sub = elig.iloc[::5]
s = sub.stack(); s = s[s]; idx = s.index
b = pd.DataFrame(index=idx).reset_index(); b.columns = ["date", "ticker"]
for h in H:
    b[f"r{h}"] = fwd[h].stack(future_stack=True).reindex(idx).values
    b[f"x{h}"] = b[f"r{h}"] - spy_fwd[h].reindex(b["date"]).values
b["mae120"] = mae120.stack(future_stack=True).reindex(idx).values
b["mfe120"] = mfe120.stack(future_stack=True).reindex(idx).values
b["vol60"] = vol60.stack(future_stack=True).reindex(idx).values
b["spy_up"] = spy_up.reindex(b["date"]).values
for N in (120, 200):
    ma = adj.rolling(N, min_periods=N).mean()
    b[f"above{N}"] = (adj > ma).stack(future_stack=True).reindex(idx).values
b.to_parquet(f"{OUT}/baseline.parquet")
print("baseline", len(b))
