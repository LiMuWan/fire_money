# Quant Hunter Performance Comparison 2026-04-15

## Summary

- Pipeline sample groups: 5
- Pipeline repeats per group: 3
- Performance regressions: 5

## Pipeline

- 10 files | scan 4.64ms | backtest 0.32ms | recommend 0.72ms | plan 0.04ms | board 0.04ms | export 5.17ms | paper 1.52ms
- 50 files | scan 22.16ms | backtest 1.43ms | recommend 2.58ms | plan 0.05ms | board 0.10ms | export 7.40ms | paper 1.65ms
- 100 files | scan 41.18ms | backtest 3.01ms | recommend 4.53ms | plan 0.07ms | board 0.18ms | export 9.34ms | paper 1.61ms
- 200 files | scan 84.44ms | backtest 5.89ms | recommend 9.02ms | plan 0.09ms | board 0.33ms | export 26.07ms | paper 1.73ms
- 500 files | scan 301.97ms | backtest 25.09ms | recommend 38.58ms | plan 0.33ms | board 1.37ms | export 47.00ms | paper 3.19ms

## Qt Boot

- Samples: 1524.33ms, 1217.36ms, 1461.03ms

## Qt Boot Breakdown

- Import: 0.01ms
- Run 1: total 1235.97ms | build 114.55ms | post 356.69ms | finish 0.70ms
- Run 2: total 2164.21ms | build 118.45ms | post 419.92ms | finish 0.90ms
- Run 3: total 1355.77ms | build 158.69ms | post 363.43ms | finish 0.65ms

## Regressions

- files=200 export_ms baseline=15.17ms current=26.07ms threshold=20.48ms
- files=500 scan_ms baseline=207.13ms current=301.97ms threshold=279.63ms
- files=500 backtest_ms baseline=13.52ms current=25.09ms threshold=18.25ms
- files=500 recommend_ms baseline=21.08ms current=38.58ms threshold=28.46ms
- files=500 export_ms baseline=28.73ms current=47.00ms threshold=38.79ms