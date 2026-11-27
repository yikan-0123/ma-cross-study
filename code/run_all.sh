#!/usr/bin/env bash
# Reproduce the whole study (Python 3.11+, ~5 min, ~3 GB RAM).
# pip install pandas numpy pyarrow duckdb statsmodels
set -e
mkdir -p data panel out
BASE=https://github.com/Johnbrick123/sp500-data/releases/download/data
for f in prices.parquet membership_intervals.parquet no_trade_days.csv exit_gaps.csv; do
  [ -f data/$f ] || curl -sL -o data/$f $BASE/$f
done
python 01_build_panel.py data panel     # wide panel + point-in-time membership
python 02_events.py panel out           # MA120/MA200 cross events + forward outcomes
python 03_stats.py out                  # Q1-Q3 tables, volatility drivers
python 04_lag_jump.py panel out         # Q4 lags; jump share of variance
python 05_backtest.py panel out         # Q5 strategies vs buy & hold
python 06_mu_case.py panel out          # MU state + analogue events
python 07_iterate.py out                # slope x market regime grid, MU own history
