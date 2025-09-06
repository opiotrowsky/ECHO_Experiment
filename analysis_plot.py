#!/usr/bin/env python3
"""
analysis_plot.py — analiza wyników i wykresy porównawcze warunków (bez seaborn, 1 wykres = 1 figura).

Funkcje:
- Odczytuje wszystkie pliki data/results_*.csv (np. memory, baseline, memory_k2 ...)
- Generuje boxploty dla każdej metryki, porównując dostępne warunki
- Zapisuje podsumowanie (średnia, odchylenie std, min, max) do data/summary_metrics.csv

Użycie:
  python analysis_plot.py --outdir data --metrics m1_coverage,m2_latency_cycles,m3_missed_actions_rate,m4_cpu_ms_per_tick,difficulty_proxy
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', type=str, default='data')
    ap.add_argument(
        '--metrics',
        type=str,
        default='m1_coverage,m2_latency_cycles,m3_missed_actions_rate,m4_cpu_ms_per_tick,difficulty_proxy',
        help='Lista metryk rozdzielona przecinkami',
    )
    return ap.parse_args()


def read_results(outdir: Path):
    """Zwraca dict: {condition: [row_dict, ...]} dla wszystkich plików results_*.csv w katalogu."""
    data = {}
    for f in outdir.glob('results_*.csv'):
        condition = f.stem.replace('results_', '')
        with f.open(newline='') as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        if rows:
            data[condition] = rows
    return data


def to_float_list(rows, key):
    vals = []
    for r in rows:
        try:
            vals.append(float(r[key]))
        except (KeyError, ValueError):
            pass
    return vals


def write_summary(outdir: Path, metrics: list[str], data_by_cond: dict[str, list[dict]]):
    """Zapisz summary_metrics.csv z prostymi statystykami."""
    out = outdir / 'summary_metrics.csv'
    fields = ['condition', 'n']
    for m in metrics:
        fields += [f'{m}_mean', f'{m}_std', f'{m}_min', f'{m}_max']

    rows = []
    for cond, rows_raw in sorted(data_by_cond.items()):
        row = {'condition': cond, 'n': len(rows_raw)}
        for m in metrics:
            vals = to_float_list(rows_raw, m)
            if vals:
                row[f'{m}_mean'] = f'{mean(vals):.6f}'
                row[f'{m}_std']  = f'{pstdev(vals):.6f}'
                row[f'{m}_min']  = f'{min(vals):.6f}'
                row[f'{m}_max']  = f'{max(vals):.6f}'
            else:
                row[f'{m}_mean'] = row[f'{m}_std'] = row[f'{m}_min'] = row[f'{m}_max'] = ''
        rows.append(row)

    with out.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('Saved', out)


def save_boxplots(outdir: Path, metrics: list[str], data_by_cond: dict[str, list[dict]]):
    """Dla każdej metryki zapisz boxplot z porównaniem dostępnych warunków."""
    conditions = sorted(data_by_cond.keys())
    for m in metrics:
        series = [to_float_list(data_by_cond[c], m) for c in conditions]
        # Pomiń metryki bez danych
        if not any(len(s) for s in series):
            print(f'Skip {m} (no data)')
            continue
        plt.figure()
        plt.title(f'{m}: comparison across conditions')
        plt.boxplot(series, labels=conditions)
        plt.ylabel(m)
        out = outdir / f'{m}_boxplot.png'
        plt.savefig(out, bbox_inches='tight')
        plt.close()
        print('Saved', out)


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    metrics = [m.strip() for m in args.metrics.split(',') if m.strip()]

    data_by_cond = read_results(outdir)
    if not data_by_cond:
        print(f'Brak plików results_*.csv w {outdir}')
        return

    save_boxplots(outdir, metrics, data_by_cond)
    write_summary(outdir, metrics, data_by_cond)


if __name__ == '__main__':
    main()
