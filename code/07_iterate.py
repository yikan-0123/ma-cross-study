"""Step 7: self-critique iterations. (a) 2x2 grid MA slope x market regime; (b) dist measured in vol units;
(c) MU's own MA200/MA120 cross history.  Usage: python 07_iterate.py <out_dir>"""
import sys, numpy as np, pandas as pd
O = sys.argv[1]
ev = pd.read_parquet(f"{O}/events.parquet")
def fm(d, col):
    m = d.dropna(subset=[col]).groupby(d["date"].dt.to_period("M"))[col].mean()
    return m.mean(), m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))
rows = []
for N in (120, 200):
    for dr in ("down", "up"):
        d = ev[(ev.ma == N) & (ev.dir == dr) & (ev.variant == "conf3")]
        for sl in ("MA rising", "MA falling"):
            for mk in ("SPY>MA200", "SPY<MA200"):
                x = d[((d.slope20 >= 0) if sl == "MA rising" else (d.slope20 < 0)) & ((d.spy_up == True) if mk == "SPY>MA200" else (d.spy_up == False))]
                r = {"MA": N, "dir": dr, "MA slope": sl, "market": mk, "n": len(x)}
                for h in (60, 120, 250):
                    m, t = fm(x, f"x{h}"); r[f"xs{h}"] = m; r[f"t{h}"] = t
                r["med_r120"] = x.r120.median(); r["sd120"] = x.r120.std(); r["whip20"] = x.whip20.mean()
                rows.append(r)
G = pd.DataFrame(rows); pd.set_option("display.width", 250)
print(G.round(3).to_string()); G.to_csv(f"{O}/grid.csv", index=False)

mu = ev[(ev.ticker == "MU") & (ev.variant == "conf3")].sort_values("date")
print("\nMU confirmed (3-day) crosses since 1996:", len(mu))
print(mu.groupby(["ma", "dir"])[["r60", "r120", "x120", "mae120", "mfe120"]].agg(["count", "median"]).round(3).to_string())
print(mu[(mu.ma == 200) & (mu.dir == "down")][["date", "r60", "r120", "r250", "mae120", "whip20"]].tail(12).round(3).to_string())
