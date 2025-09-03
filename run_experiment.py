#!/usr/bin/env python3
"""
run_experiment.py — uruchamia batch eksperymentów i zapisuje wyniki do CSV.

Domyślnie wykonuje dwa warunki:
- memory   -> data/results_memory.csv
- baseline -> data/results_baseline.csv

Możesz sterować parametrami przez CLI:
  python run_experiment.py --seeds 0,1,2,3,4 --cycles 5 --light_ticks 100 --dark_ticks 100 --memory_k 1 --conditions memory,baseline --outdir data
"""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean
from typing import List

from experiment import run_experiments

DEFAULT_CONDITIONS = ['memory', 'baseline']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Batch runner for ECHO-like experiment')
    p.add_argument('--outdir', type=str, default='data', help='Katalog wyjściowy na CSV/figury')
    p.add_argument('--seeds', type=str, default='0,1,2,3,4', help='Lista seedów rozdzielona przecinkami')
    p.add_argument('--cycles', type=int, default=5, help='Liczba cykli LIGHT/DARK w epizodzie')
    p.add_argument('--light_ticks', type=int, default=100, help='Długość fazy LIGHT (ticki)')
    p.add_argument('--dark_ticks', type=int, default=100, help='Długość fazy DARK (ticki)')
    p.add_argument('--conditions', type=str, default=','.join(DEFAULT_CONDITIONS), help='Warunki do uruchomienia: np. memory,baseline')
    return p.parse_args()


def to_seed_list(s: str) -> List[int]:
    return [int(x.strip()) for x in s.split(',') if x.strip() != '']


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    seeds = to_seed_list(args.seeds)
    conditions = [c.strip() for c in args.conditions.split(',') if c.strip() != '']

    # Uruchom każdy warunek i zapisz pod stałymi nazwami dla kompatybilności z analysis_plot.py
    for cond in conditions:
        outfile = outdir / f'results_{cond}.csv'
        rows = run_experiments(
            outfile,
            seeds=seeds,
            condition=cond,
            light_ticks=args.light_ticks,
            dark_ticks=args.dark_ticks,
            cycles=args.cycles,
        )
        print(f'Wrote {outfile} ({len(rows)} wierszy)')

        # Prosty podgląd średnich metryk
        def avg(key: str):
            vals = [float(r[key]) for r in rows]
            return sum(vals)/len(vals) if vals else float('nan')

        m1 = avg('m1_coverage')
        m2 = avg('m2_latency_cycles')
        m3 = avg('m3_cpu_ms_per_tick')
        diff = avg('difficulty_proxy')
        print(f'[{cond}] m1_coverage={m1:.3f}, m2_latency={m2:.3f} cycles, m3_cpu={m3:.4f} ms/tick, difficulty={diff:.1f}')

    # Dodatkowo wydrukuj „sample” pierwszego wiersza memory/baseline (gdy istnieją)
    for cond in ['memory', 'baseline']:
        f = outdir / f'results_{cond}.csv'
        if f.exists():
            with f.open() as fh:
                lines = fh.readlines()
            if len(lines) >= 2:
                print(f'{cond.capitalize()} condition (sample):', lines[1].strip())

if __name__ == '__main__':
    main()
