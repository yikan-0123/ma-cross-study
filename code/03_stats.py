"""Step 3: summary statistics for Q1-Q3 (+ MU analogues).
Usage: python 03_stats.py <out_dir>"""
import sys, numpy as np, pandas as pd
import statsmodels.api as sm

O = sys.argv[1]
ev = pd.read_parquet(f"{O}/events.parquet")
bl = pd.read_parquet(f"{O}/baseline.parquet")
H = [5, 20, 60, 120, 250]
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)

def fm_t(d, col):
    """Average per calendar month, then t-stat across months (controls for time clustering)."""
    m = d.dropna(subset=[col]).groupby(d["date"].dt.to_period("M"))[col].mean()
    return m.mean() / (m.std(ddof=1) / np.sqrt(len(m))), len(m)

def summ(d, tag):
    row = {"set": tag, "n": len(d)}
    for h in (20, 60, 120, 250):
        r = d[f"r{h}"].dropna(); x = d[f"x{h}"].dropna()
        row[f"mean{h}"] = r.mean(); row[f"med{h}"] = r.median(); row[f"sd{h}"] = r.std()
        row[f"p10_{h}"] = r.quantile(.1); row[f"p90_{h}"] = r.quantile(.9)
        row[f"hit{h}"] = (r > 0).mean(); row[f"xs{h}"] = x.mean(); row[f"xmed{h}"] = x.median()
        row[f"t_xs{h}"] = fm_t(d, f"x{h}")[0]
    row["mae120_med"] = d["mae120"].median(); row["mfe120_med"] = d["mfe120"].median()
    row["mae120_p25"] = d["mae120"].quantile(.25)
    if "mae250" in d:
        row["mae250_med"] = d["mae250"].median(); row["mfe250_med"] = d["mfe250"].median()
    if "whip10" in d:
        row["whip10"] = d["whip10"].mean(); row["whip20"] = d["whip20"].mean()
    return row

rows = []
base = summ(bl, "baseline all member-days")
rows.append(base)
for N in (120, 200):
    rows.append(summ(bl[bl[f"above{N}"] == True], f"baseline state above MA{N}"))
    rows.append(summ(bl[bl[f"above{N}"] == False], f"baseline state below MA{N}"))
for N in (120, 200):
    for dr in ("down", "up"):
        for var in ("raw", "conf3", "band3"):
            d = ev[(ev.ma == N) & (ev.dir == dr) & (ev.variant == var)]
            rows.append(summ(d, f"MA{N} {dr} {var} all"))
            if var == "raw":
                dd = d[d.first60]
                rows.append(summ(dd, f"MA{N} {dr} raw first-in-60d"))
                # slope split (trend vs pullback)
                rows.append(summ(dd[dd.slope20 < 0], f"MA{N} {dr} first60 MA falling"))
                rows.append(summ(dd[dd.slope20 >= 0], f"MA{N} {dr} first60 MA rising"))
                rows.append(summ(dd[dd.spy_up == True], f"MA{N} {dr} first60 SPY>MA200"))
                rows.append(summ(dd[dd.spy_up == False], f"MA{N} {dr} first60 SPY<MA200"))
                if dr == "down":
                    rows.append(summ(dd[dd.ret250 > 1.0], f"MA{N} down first60 after +100% 12m run"))
                    rows.append(summ(dd[(dd.ret250 > 1.0) & (dd.slope20 >= 0)], f"MA{N} down first60 +100% run & MA rising"))
                    rows.append(summ(dd[(dd.ret250 > 0.5)], f"MA{N} down first60 after +50% 12m run"))
T = pd.DataFrame(rows).set_index("set")
T.to_csv(f"{O}/summary.csv")
cols = ["n", "mean20", "mean60", "med60", "sd60", "p10_60", "p90_60", "hit60", "xs60", "t_xs60",
        "mean120", "med120", "sd120", "xs120", "t_xs120", "mean250", "sd250", "xs250", "t_xs250",
        "mae120_med", "mfe120_med", "whip10", "whip20"]
print(T[cols].round(3).to_string()) if "--quiet" not in sys.argv else None

# ---- Q3: what drives the dispersion of forward returns? (MA200 first-in-60d down + up events)
d = ev[(ev.variant == "raw") & ev.first60 & (ev.ma == 200)].dropna(subset=["r60", "vol60", "beta", "ret250", "spy_vol20", "spy_r60", "dist"]).copy()
d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=["slope20", "ret250", "vol60", "beta"])
d["absr60"] = d["r60"].abs()
d["mkt_down"] = (~d["spy_up"].astype(bool)).astype(float)
X_cols = ["vol60", "beta", "spy_vol20", "mkt_down", "ret250", "slope20"]
Z = (d[X_cols] - d[X_cols].mean()) / d[X_cols].std()
res = sm.OLS(d["absr60"], sm.add_constant(Z)).fit(cov_type="cluster", cov_kwds={"groups": d["date"].dt.to_period("M").astype(str)})
print("\nQ3 ex-ante drivers of |60d return| (standardised coefs, month-clustered t):")
print(pd.DataFrame({"coef": res.params, "t": res.tvalues}).round(4).to_string(), "\nR2", round(res.rsquared, 3))
single = {c: sm.OLS(d["absr60"], sm.add_constant(d[[c]])).fit().rsquared for c in X_cols}
print("single-factor R2:", {k: round(v, 3) for k, v in single.items()})
# vol bucket table: sd of 60d returns by ex-ante vol quintile
d["volq"] = pd.qcut(d["vol60"], 5, labels=["Q1 low", "Q2", "Q3", "Q4", "Q5 high"])
vb = d.groupby(["dir", "volq"], observed=True).agg(n=("r60", "size"), vol60=("vol60", "median"), sd60=("r60", "std"), mean60=("r60", "mean"), p10=("r60", lambda s: s.quantile(.1)), p90=("r60", lambda s: s.quantile(.9)))
print(vb.round(3).to_string()); vb.to_csv(f"{O}/vol_buckets.csv")
# ex-post decomposition: share of 60d return variance explained by the market's own 60d return
for dr in ("down", "up"):
    dd = d[d.dir == dr]
    r2 = sm.OLS(dd["r60"], sm.add_constant(dd["spy_r60"] * dd["beta"])).fit().rsquared
    r2b = sm.OLS(dd["r60"], sm.add_constant(dd["spy_r60"])).fit().rsquared
    print(f"{dr}: R2 of r60 on beta*SPY60 = {r2:.3f}; on SPY60 = {r2b:.3f}")
# regime table
rg = d.groupby(["dir", "mkt_down"]).agg(n=("r60", "size"), sd60=("r60", "std"), mean60=("r60", "mean"), xs60=("x60", "mean"))
print(rg.round(3).to_string())
d.to_parquet(f"{O}/q3_sample.parquet")
