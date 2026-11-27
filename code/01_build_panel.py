"""Step 1: build a wide daily panel (dates x tickers) from the point-in-time S&P 500 dataset.

Data: Johnbrick123/sp500-data GitHub release (prices.parquet, membership_intervals.parquet,
no_trade_days.csv, exit_gaps.csv). Download:
  https://github.com/Johnbrick123/sp500-data/releases/download/data/prices.parquet
  https://github.com/Johnbrick123/sp500-data/releases/download/data/membership_intervals.parquet
Usage: python 01_build_panel.py <data_dir> <out_dir>
"""
import sys, os
import duckdb, numpy as np, pandas as pd

DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
START = "1994-06-01"   # ~1.5y warm-up so MA200 exists from 1996

con = duckdb.connect()
px = con.sql(f"""select date, ticker, adj_close, close, high, low
                 from '{DATA}/prices.parquet' where date >= '{START}'""").df()
px["date"] = pd.to_datetime(px["date"])
adj = px.pivot(index="date", columns="ticker", values="adj_close").sort_index()
adj = adj.where(adj > 0)
print("panel", adj.shape, adj.index.min().date(), adj.index.max().date())

# point-in-time membership mask
m = pd.read_parquet(f"{DATA}/membership_intervals.parquet")
mem = pd.DataFrame(False, index=adj.index, columns=adj.columns)
for r in m.itertuples():
    if r.ticker not in mem.columns:
        continue
    end = r.end if pd.notna(r.end) else adj.index.max() + pd.Timedelta(days=1)
    mem.loc[(mem.index >= r.start) & (mem.index < end), r.ticker] = True

# no-trade days (halts / carried prices) -> not eligible as event days
nt = pd.read_csv(f"{DATA}/no_trade_days.csv", parse_dates=["date"])
notrade = pd.DataFrame(False, index=adj.index, columns=adj.columns)
for r in nt.itertuples():
    if r.ticker in notrade.columns and r.date in notrade.index:
        notrade.loc[r.date, r.ticker] = True

# exit gaps (e.g. SVB/Signature): book the post-gap trade as the final price
eg = pd.read_csv(f"{DATA}/exit_gaps.csv", parse_dates=["last_member_day"])
for r in eg.itertuples():
    if r.ticker in adj.columns and r.last_member_day >= adj.index.min():
        s = adj[r.ticker]
        last = s.loc[:r.last_member_day].dropna()
        if len(last):
            nxt = adj.index[adj.index > r.last_member_day]
            if len(nxt):
                adj.loc[nxt[0], r.ticker] = last.iloc[-1] * (1 + r.change)
                adj.loc[nxt[1:], r.ticker] = np.nan
                print("exit gap applied", r.ticker, r.change)

adj.to_pickle(f"{OUT}/adj.pkl")
mem.to_pickle(f"{OUT}/mem.pkl")
notrade.to_pickle(f"{OUT}/notrade.pkl")
print("members per day (median):", int(mem.sum(1).loc["1996":].median()))
