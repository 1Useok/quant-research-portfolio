"""python run_demo.py [--out DIR] : 비용 인식 vs 비용 무시 프런티어를 계산해 CSV로 쓴다."""

import argparse
import csv
from pathlib import Path

from backtest import Backtest, summarize
from model import load_panel

ROOT = Path(__file__).resolve().parent
WEALTHS = (0, 30, 100, 300)          # 운용자산(억원). 0은 비용이 없는 경우
FIELDS = ("net_return_ann", "vol_ann", "net_sharpe", "utility_ann", "turnover_month", "cost_ann", "gross_exposure")
LABEL = {False: "cost_blind", True: "cost_aware"}


def compute(panel, last=None, wealths=WEALTHS):
    bt = Backtest(panel)
    return {(w, aware): bt.run(w, aware, last) for w in wealths for aware in (False, True)}


def write_outputs(panel, runs, out):
    out.mkdir(parents=True, exist_ok=True)

    def writer(name, header):
        f = (out / name).open("w", encoding="utf-8", newline="")
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header.split())
        return f, w

    f, w = writer("frontier.csv", "wealth_eok strategy months " + " ".join(FIELDS))
    with f:
        for (wealth, aware), rec in runs.items():
            s = summarize(rec)
            w.writerow((wealth, LABEL[aware], s["months"]) + tuple(f"{s[k]:.5f}" for k in FIELDS))
    f, w = writer("weights.csv", "wealth_eok strategy month stock prev_weight weight")
    with f:
        for (wealth, aware), rec in runs.items():
            for r in rec:
                for i, stock in enumerate(panel.stocks):
                    w.writerow((wealth, LABEL[aware], r["month"], stock,
                                f"{r['prev'][i]:.6f}", f"{r['weights'][i]:.6f}"))
    f, w = writer("nav.csv", "wealth_eok strategy month ridge gross_return cost net_return nav")
    with f:
        for (wealth, aware), rec in runs.items():
            nav = 1.0
            for r in rec:
                nav *= 1 + r["net"]
                w.writerow((wealth, LABEL[aware], r["month"], r["ridge"], f"{r['gross']:.6f}",
                            f"{r['cost']:.6f}", f"{r['net']:.6f}", f"{nav:.6f}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "outputs"))
    out = Path(ap.parse_args().out)
    panel = load_panel(ROOT / "data" / "panel.csv")
    runs = compute(panel)
    write_outputs(panel, runs, out)
    print("wealth  strategy   netR    vol  Sharpe    util  turn/m   cost  gross")
    for (wealth, aware), rec in runs.items():
        s = summarize(rec)
        print(f"{wealth:6d}  {'aware' if aware else 'blind':8s} {s['net_return_ann']:6.1%} {s['vol_ann']:5.1%} "
              f"{s['net_sharpe']:6.2f} {s['utility_ann']:7.4f} {s['turnover_month']:6.2f} "
              f"{s['cost_ann']:5.1%} {s['gross_exposure']:5.2f}")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
