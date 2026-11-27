# What Happens After a Stock Breaks Its 120-Day or 200-Day Moving Average?

An event study and backtest of MA120 / MA200 crosses on **point-in-time S&P 500 constituents, January 1996 to 25 November 2026**. The sample includes companies that were later removed, acquired or went bankrupt, so it is free of survivorship bias. Micron (MU) is used as a case study.

## Key findings

**For individual large-cap US stocks, crossing above or below MA120 or MA200 has almost no power to predict direction.** Across about 770,000 events, the excess return over SPY in the following 60, 120 and 250 trading days stays within ±0.8%, and the full return distribution is almost the same as buying on a random day. The value of the moving average is in **risk control**: it flags high-volatility regimes and cuts deep drawdowns.

| Question | Answer |
| --- | --- |
| 1. Identifying the trend | About 70% of raw crosses reverse within 10 days. A 3-day confirmation lowers this to 53%, and a 3% band lowers it to 38%. The informative variable is the **slope of the MA**. When SPY is above its own MA200, a stock that breaks below an MA200 that is already falling underperforms SPY by 1.4% over the next 120 days (month-clustered t ≈ -2.6). An upside break while the MA is still falling is usually a false breakout (-1.3% over 120 days, t ≈ -2.9). |
| 2. Size of the move after the signal | After a confirmed MA200 break-down, the median 120-day return is +5.3%. The 10th to 90th percentiles are -22% to +32%, the same as on a random day. The median maximum drawdown within 120 days is -9.1%, and the worst quarter of cases exceeds -19.5%. |
| 3. Dispersion and its drivers | The standard deviation of forward returns is about 10% (20 days), 17% (60 days), 24% (120 days) and 36% (250 days). The three main drivers are: (1) the stock's own volatility (60-day standard deviation rises from 10.6% in the lowest-volatility quintile to 24.6% in the highest); (2) market beta times the market's move (about 25% of the variance); (3) earnings and event gaps (the single largest day accounts for about 20% of 60-day variance, against about 2% if days were i.i.d.). |
| 4. Lag between price reversal and MA reversal | After a genuine top (followed by a fall of at least 20%, median -35%), the median lags are: price below MA120 after 22 days (already down 12.7%), below MA200 after 32 days (down 15%), MA120 turns down after 55 days, and MA200 turns down after 85 days. About half of the decline is still ahead when the signal fires. |
| 5. Entry and exit rules | Holding each constituent only while it is above MA200 gives 5.5–6.3% a year, against 11.5% for equal-weight buy and hold. Maximum drawdown falls from -59% to about -20%. For SPY, an MA200 rule with a ±2% band returns 8.7% a year against 10.2%, with a drawdown of -23% against -55%. |

### Backtest summary (1996–2026, 10 bp per side, idle cash at 0%)

| Strategy | CAGR | Volatility | Sharpe (rf=0) | Max drawdown | Turnover per year |
| --- | --- | --- | --- | --- | --- |
| Buy & hold (equal-weight members) | 11.5% | 20.0% | 0.65 | -59.0% | 0.1 |
| Volatility-managed: w = min(1, 25% / vol60) | 8.8% | 12.9% | 0.72 | -35.0% | 1.4 |
| Index filter: SPY > MA200 | 7.6% | 12.3% | 0.66 | -26.8% | 6.5 |
| MA50 > MA200 (golden cross) | 6.8% | 10.3% | 0.69 | -28.5% | 1.5 |
| 12-1 month momentum > 0 | 6.7% | 11.2% | 0.64 | -30.3% | 6.8 |
| MA200, 3-day confirmation | 6.3% | 9.3% | 0.71 | -20.2% | 3.6 |
| MA200, ±2% band | 6.1% | 9.1% | 0.70 | -23.7% | 3.3 |
| Price > MA200 | 5.5% | 9.0% | 0.64 | -26.2% | 8.5 |
| Price > MA200 and MA200 rising | 5.1% | 7.9% | 0.67 | -16.4% | 5.9 |
| Price > MA120 | 4.3% | 9.0% | 0.51 | -25.5% | 11.7 |

The results hold with one extra day of execution delay. When idle cash earns the return of SHY (1–3 year Treasuries, from August 2002), the Sharpe ratio of the MA200 rules rises to 0.82–0.84, against 0.65 for buy and hold. They also hold in each sub-period (1996–2007, 2008–2016, 2017–2026).

### Micron (MU) case, as of 25 November 2026

- Close 601.25; MA120 933.29 (-35.6%, now falling); MA200 776.29 (-22.6%, still rising). Down 50% from the June 2026 high after a +161% 12-month run. 60-day annualised volatility is 89%.
- A confirmed (3-day) MA200 break-down occurred on 18 November 2026.
- 109 historical analogues (S&P 500 members more than 20% below a still-rising MA200, after a 12-month gain above 30% and a drawdown of more than 40%): median return +4.5% over 20 days but -23.7% over 250 days, with a median 250-day excess return of -19% against SPY. The dispersion is very wide (10th to 90th percentile: -75% to +58%).

## Method

- **Universe:** S&P 500 members on each day, using point-in-time membership. Prices are split- and dividend-adjusted. After delisting, a stock is valued at its last trade. SVB and Signature Bank use their actual post-halt prints.
- **Events:** a close below (or above) the MA after a close on the other side. There are three variants: raw cross, 3-day confirmation, and a 3% band. The MAs are 120-day and 200-day simple moving averages.
- **Outcomes:** forward 5/20/60/120/250-day returns, excess return over SPY, maximum adverse and favourable excursion, and whether the price re-crosses within 10 or 20 days.
- **Control group:** every member-day (sampled every 5th day, about 780,000 observations).
- **Inference:** events cluster heavily in time (hundreds of stocks break down together in a crash), so means are averaged by calendar month first, and t-statistics are computed across months (in the spirit of Fama-MacBeth).
- **Backtests:** one equal-weight slot per constituent. The signal is taken at the close and the position is held from the next day. Costs are 10 bp per side.

## Limitations

- Large caps only. Small caps and non-US markets (for example A-shares or Hong Kong) may behave differently.
- There are no earnings dates or sector classifications in the data. The earnings effect is proxied by the largest single-day move.
- Turning points in the lag analysis are chosen with hindsight (only tops followed by a real decline), so they describe genuine trends and are not an ex-ante expectation.
- Sixteen sub-groups were tested, so t-values near 2.7 should be read as marginal under multiple testing.

## Reproduce

```bash
pip install pandas numpy pyarrow duckdb statsmodels
cd code && bash run_all.sh      # downloads the public data; about 5 minutes and 3 GB RAM
```

| File | Purpose |
| --- | --- |
| `code/01_build_panel.py` | Daily panel, point-in-time membership, halts and delistings |
| `code/02_events.py` | MA120/MA200 cross events and forward outcomes |
| `code/03_stats.py` | Summary statistics and volatility-driver regressions |
| `code/04_lag_jump.py` | Lag between price turns and MA signals; jump share of variance |
| `code/05_backtest.py` | Strategy backtests with costs, delay and cash-yield sensitivity |
| `code/06_mu_case.py` | Micron state and historical analogues |
| `code/07_iterate.py` | MA slope × market regime grid; Micron's own cross history |
| `results/*.csv` | All result tables |

## Data

Prices and index membership come from the public dataset [Johnbrick123/sp500-data](https://github.com/Johnbrick123/sp500-data). The scripts download it at run time. This repository does not contain the raw data.

## References

- Brock, W., Lakonishok, J. & LeBaron, B. (1992). Simple Technical Trading Rules and the Stochastic Properties of Stock Returns. *Journal of Finance*, 47(5).
- Sullivan, R., Timmermann, A. & White, H. (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5).
- Faber, M. (2007). A Quantitative Approach to Tactical Asset Allocation. SSRN 962461.
- Moskowitz, T., Ooi, Y. H. & Pedersen, L. H. (2012). Time Series Momentum. *Journal of Financial Economics*, 104(2).
- Han, Y., Yang, K. & Zhou, G. (2013). A New Anomaly: The Cross-Sectional Profitability of Technical Analysis. *Journal of Financial and Quantitative Analysis*, 48(5).
- Moreira, A. & Muir, T. (2017). Volatility-Managed Portfolios. *Journal of Finance*, 72(4).

## Disclaimer

This is quantitative research, not investment advice. Past statistics do not guarantee future results.
