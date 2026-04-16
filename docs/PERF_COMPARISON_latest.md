# Quant Hunter Performance Report

## Summary

- Pipeline sample groups: 5
- Pipeline repeats per group: 3
- Performance regressions: 0

## Pipeline

- 10 files | scan 4.22ms | backtest 0.30ms | recommend 0.62ms | plan 0.03ms | board 0.04ms | export 4.18ms | paper 1.37ms
- 50 files | scan 20.31ms | backtest 1.34ms | recommend 2.28ms | plan 0.05ms | board 0.10ms | export 6.36ms | paper 1.45ms
- 100 files | scan 40.88ms | backtest 2.83ms | recommend 4.34ms | plan 0.06ms | board 0.17ms | export 9.10ms | paper 1.46ms
- 200 files | scan 80.57ms | backtest 5.51ms | recommend 8.31ms | plan 0.09ms | board 0.31ms | export 12.76ms | paper 1.65ms
- 500 files | scan 211.56ms | backtest 14.11ms | recommend 20.97ms | plan 0.19ms | board 0.76ms | export 31.41ms | paper 2.27ms

## Qt Boot

- Samples: 3674.84ms, 3974.00ms, 3987.98ms

## Qt Boot Breakdown

- Import: 0.01ms
- Run 1: total 3912.34ms | build 182.49ms | post 618.37ms | finish 1.73ms
- Run 2: total 3610.50ms | build 180.50ms | post 615.86ms | finish 1.73ms
- Run 3: total 3678.78ms | build 175.86ms | post 631.32ms | finish 1.60ms

## Regressions

- No performance regressions detected against the selected baseline.