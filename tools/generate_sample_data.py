from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "sample_data"


def generate_rows(symbol: str = "SHSE.600000", pattern: str = "reclaim") -> list[list[str | float]]:
    rows: list[list[str | float]] = []
    current = date(2026, 1, 5)
    close = 10.0 if pattern != "weak" else 7.5

    for idx in range(46):
        while current.weekday() >= 5:
            current += timedelta(days=1)

        if pattern == "reclaim":
            if idx < 18:
                close += 0.05
                high = close + 0.06
                low = close - 0.07
                open_price = close - 0.02
                volume = 980_000 + idx * 22_000
            elif idx == 18:
                open_price = close + 0.08
                high = close + 0.55
                low = close - 0.18
                close = close + 0.03
                volume = 3_800_000
            elif idx == 19:
                open_price = close + 0.02
                high = close + 0.14
                low = close - 0.12
                close = close - 0.04
                volume = 2_150_000
            elif idx == 20:
                open_price = close + 0.06
                high = close + 0.28
                low = close - 0.06
                close = close + 0.22
                volume = 2_650_000
            elif idx < 30:
                close += 0.08
                high = close + 0.09
                low = close - 0.08
                open_price = close - 0.03
                volume = 1_450_000 + (idx - 20) * 55_000
            elif idx == 34:
                open_price = close + 0.14
                high = close + 0.62
                low = close - 0.16
                close = close + 0.05
                volume = 4_200_000
            elif idx == 35:
                open_price = close + 0.03
                high = close + 0.12
                low = close - 0.10
                close = close - 0.01
                volume = 2_350_000
            elif idx == 36:
                open_price = close + 0.04
                high = close + 0.24
                low = close - 0.04
                close = close + 0.20
                volume = 2_900_000
            else:
                drift = -0.03 if idx > 40 else 0.04
                close += drift
                high = close + 0.08
                low = close - 0.08
                open_price = close - 0.02
                volume = 1_280_000 + max(idx - 30, 0) * 37_000
        elif pattern == "watch":
            if idx < 24:
                close += 0.04
                high = close + 0.05
                low = close - 0.05
                open_price = close - 0.01
                volume = 720_000 + idx * 18_000
            elif idx == 24:
                open_price = close + 0.05
                high = close + 0.45
                low = close - 0.15
                close = close + 0.01
                volume = 2_900_000
            elif idx == 25:
                open_price = close + 0.01
                high = close + 0.04
                low = close - 0.10
                close = close - 0.05
                volume = 2_100_000
            else:
                close += 0.01
                high = close + 0.04
                low = close - 0.05
                open_price = close - 0.01
                volume = 1_050_000 + max(idx - 25, 0) * 12_000
        else:
            close += -0.03 if idx % 4 else 0.01
            high = close + 0.03
            low = close - 0.07
            open_price = close - 0.02
            volume = 650_000 + idx * 8_000

        rows.append(
            [
                current.isoformat(),
                symbol,
                round(open_price, 2),
                round(high, 2),
                round(low, 2),
                round(close, 2),
                int(volume),
            ]
        )
        current += timedelta(days=1)
    return rows


def _write_csv(path: Path, rows: list[list[str | float]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)


def _write_reference_files() -> None:
    with (OUTPUT_DIR / "stock_profiles.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "name", "industry", "is_leader", "notes"])
        writer.writerow(["SHSE.600000", "浦发银行", "银行", 1, "低位修复型金融龙头"])
        writer.writerow(["SZSE.000001", "平安银行", "银行", 1, "消息驱动观察标的"])
        writer.writerow(["SHSE.601398", "工商银行", "银行", 1, "趋势偏弱，作为对照样本"])

    with (OUTPUT_DIR / "news_catalysts.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "title", "summary", "published_at", "sentiment_score", "heat"])
        writer.writerow(["SHSE.600000", "银行板块获得增量资金关注", "权重金融获得关注，修复持续性增强。", "2026-02-25", 1.2, 1.4])
        writer.writerow(["SHSE.600000", "公司推进分红与资产质量改善", "偏中期利好，有助于估值修复。", "2026-02-24", 0.9, 1.0])
        writer.writerow(["SZSE.000001", "零售金融业务改善预期升温", "短线有催化，但需要等待技术形态二次确认。", "2026-02-25", 0.7, 0.9])
        writer.writerow(["SHSE.601398", "板块轮动放缓", "情绪偏中性，持续性一般。", "2026-02-23", 0.1, 0.4])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    samples = {
        "SHSE.600000_demo.csv": generate_rows("SHSE.600000", "reclaim"),
        "SZSE.000001_demo.csv": generate_rows("SZSE.000001", "watch"),
        "SHSE.601398_demo.csv": generate_rows("SHSE.601398", "weak"),
    }
    for filename, rows in samples.items():
        _write_csv(OUTPUT_DIR / filename, rows)
    _write_reference_files()


if __name__ == "__main__":
    main()
