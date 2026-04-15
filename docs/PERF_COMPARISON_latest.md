# Quant Hunter Performance Report

## Summary

- Pipeline sample groups: 5
- Pipeline repeats per group: 3
- Performance regressions: 0

## Pipeline

- 10 files | scan 4.06ms | backtest 0.31ms | recommend 0.63ms | plan 0.04ms | board 0.04ms | export 3.86ms | paper 1.09ms
- 50 files | scan 19.26ms | backtest 1.35ms | recommend 2.28ms | plan 0.05ms | board 0.10ms | export 5.39ms | paper 1.12ms
- 100 files | scan 37.77ms | backtest 2.76ms | recommend 4.20ms | plan 0.06ms | board 0.17ms | export 7.35ms | paper 1.17ms
- 200 files | scan 75.46ms | backtest 5.40ms | recommend 8.22ms | plan 0.09ms | board 0.31ms | export 17.40ms | paper 1.27ms
- 500 files | scan 191.11ms | backtest 13.35ms | recommend 20.67ms | plan 0.18ms | board 0.75ms | export 25.67ms | paper 1.79ms

## Qt Boot

- Samples: 2254.66ms, 2367.41ms, 2362.82ms

## Qt Boot Breakdown

- Import: 0.01ms
- Run 1: total 2177.91ms | build 161.09ms | post 551.50ms | finish 0.84ms
- Run 2: total 2302.21ms | build 164.68ms | post 552.72ms | finish 0.88ms
- Run 3: total 2330.96ms | build 161.10ms | post 554.49ms | finish 0.87ms

## Regressions

- No performance regressions detected against the selected baseline.