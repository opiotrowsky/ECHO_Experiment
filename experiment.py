"""
Warunki:
- baseline: brak pamięci/gatingu (NPC ma pełne ACTIONS od początku)
- memory:  gating wg akcji gracza z poprzedniego cyklu LIGHT (domyślnie K=1)

Metryki (per epizod):
- m1_coverage:   średni odsetek akcji z LIGHT[c-1], których NPC użył w cyklu c
- m2_latency_cycles: średnia liczba cykli od obserwacji do pierwszego użycia (tylko dla akcji, które zaszły)
- m3_missed_actions_rate: odsetek akcji, które NPC zobaczył, ale nigdy ich nie użył
- m4_cpu_ms_per_tick: średni koszt CPU (ms) na tick (pomiar perf_counter)
- difficulty_proxy:  łączna utrata HP gracza (suma obrażeń zadanych przez NPC)

Uwaga: interfejs pozostaje zgodny z analysis_plot.py oraz run_experiment.py.
"""

from __future__ import annotations

import time
from typing import Dict, List, Set, Iterable
from collections import deque

from env import GridEnv, ACTIONS, MOVES_ONLY, LEARNABLE
from player import ScriptedPlayer
from agent import BTGatedAgent


def run_single_experiment(seed: int = 0, light_ticks: int = 10, dark_ticks: int = 10,
cycles: int = 20, condition: str = 'memory') -> Dict[str, float]:
    env = GridEnv(seed=seed)
    player = ScriptedPlayer(rng_seed=seed + 13)
    agent = BTGatedAgent()

    # Akumulatory metryk
    coverage_per_cycle: List[float] = []
    cpu_times: List[float] = []
    damage_to_player_total = 0

    # Do liczenia latencji: kiedy akcję po raz pierwszy zobaczono i kiedy po raz pierwszy użył jej NPC
    first_seen_cycle: Dict[str, int] = {}
    first_used_cycle: Dict[str, int] = {}
    
    # Do liczenia użycia niewyuczonych podczas LIGHT[c] akcji w cyklu c+1
    unlearned_rate_per_cycle: List[float] = []
    
    observed_light: Set[str] = set()
    light_history: deque[set[str]] = deque(maxlen=1)
    
    if condition == 'memory':
        for c in range(1, cycles + 1):
            allowed = set(MOVES_ONLY)  # NPC zaczyna tylko z przemieszczaniem się
            observed_prev = light_history[-1] if len(light_history) > 0 else set()
            learned_prev = {a for a in observed_prev if a in LEARNABLE}
            allowed = set(MOVES_ONLY) | learned_prev  # ew. dodanie ruchów dla NPC z LEARNABLE
            observed_light: Set[str] = set()
            
            used_in_cycle: Set[str] = set()
            
            # LIGHT Phase
            for t in range(light_ticks):
                t0 = time.perf_counter()
                # pick action:
                action_p = player.act(env, t, 'LIGHT')
                action_n = agent.pick_action(env, allowed)
                # NPC observation:
                env.step_player(action_p)
                observed_light.add(action_p)
                if action_p in LEARNABLE and action_p not in first_seen_cycle:
                    first_seen_cycle[action_p] = c  # pierwszy raz „widziana” w tym cyklu
                
                if action_n:
                    prev_player_hp = env.player_hp
                    env.step_npc(action_n)
                    used_in_cycle.add(action_n)

                    if env.player_hp < prev_player_hp:
                        damage_to_player_total += (prev_player_hp - env.player_hp)
                
                env.tick_cooldowns()
                t1 = time.perf_counter()
                cpu_times.append(t1 - t0)
                
                    # latencja: jeśli akcję już „widziano” i jeszcze nie zarejestrowano użycia → zapisz
                if action_n in LEARNABLE:
                    if action_n in first_seen_cycle and action_n not in first_used_cycle:
                        first_used_cycle[action_n] = c  # pierwszy raz użyta w tym cyklu
            
            # DARK Phase
            for t in range(dark_ticks):
                t0 = time.perf_counter()
                
                action_p = player.act(env, t, 'DARK')
                action_n = agent.pick_action(env, allowed)
                
                env.step_player(action_p)
                if action_n:
                    prev_player_hp = env.player_hp
                    env.step_npc(action_n)
                    used_in_cycle.add(action_n)
                    
                    if env.player_hp < prev_player_hp:
                        damage_to_player_total += (prev_player_hp - env.player_hp)

                    # latencja: jeśli akcję już „widziano” i jeszcze nie zarejestrowano użycia → zapisz
                if action_n in LEARNABLE:
                    if action_n in first_seen_cycle and action_n not in first_used_cycle:
                        first_used_cycle[action_n] = c  # pierwszy raz użyta w tym cyklu

                env.tick_cooldowns()
                t1 = time.perf_counter()
                cpu_times.append(t1 - t0)
            
            # Pokrycie dla cyklu c: ile z akcji z LIGHT[c-1] zostało użytych w cyklu c
            ref = {a for a in observed_prev if a in LEARNABLE}
            used = {a for a in used_in_cycle if a in LEARNABLE}
            if ref:
                coverage_per_cycle.append(len(used & ref) / len(ref))
            if used:
                unlearned_rate_c = len(used - ref) / len(used)
                unlearned_rate_per_cycle.append(unlearned_rate_c)
            
            light_history.append(observed_light)  # dodanie observed_light z bieżącego LIGHT[c] do historii obserwacji
    
    # Wersja bez obserwowania akcji gracza:
    if condition == 'baseline':
        for c in range(1, cycles + 1):
            allowed = set(ACTIONS)  # NPC działa ze wszystimi akcjami
            observed_light: Set[str] = set()
            observed_prev = light_history[-1] if len(light_history) > 0 else set()
            
            used_in_cycle: Set[str] = set()
            
            # LIGHT Phase
            for t in range(light_ticks):
                t0 = time.perf_counter()
                # pick action:
                action_p = player.act(env, t, 'LIGHT')
                action_n = agent.pick_action(env, allowed)
                # NPC observation:
                env.step_player(action_p)
                observed_light.add(action_p)
                if action_p in LEARNABLE and action_p not in first_seen_cycle:
                    first_seen_cycle[action_p] = c  # pierwszy raz „widziana” w tym cyklu
                
                if action_n:
                    prev_player_hp = env.player_hp
                    env.step_npc(action_n)
                    used_in_cycle.add(action_n)

                    if env.player_hp < prev_player_hp:
                        damage_to_player_total += (prev_player_hp - env.player_hp)
                
                env.tick_cooldowns()
                t1 = time.perf_counter()
                cpu_times.append(t1 - t0)
                
                    # latencja: jeśli akcję już „widziano” i jeszcze nie zarejestrowano użycia → zapisz
                if action_n in LEARNABLE:
                    if action_n in first_seen_cycle and action_n not in first_used_cycle:
                        first_used_cycle[action_n] = c
            
            # DARK Phase
            for t in range(dark_ticks):
                t0 = time.perf_counter()
                
                action_p = player.act(env, t, 'DARK')
                action_n = agent.pick_action(env, allowed)
                
                env.step_player(action_p)
                if action_n:
                    prev_player_hp = env.player_hp
                    env.step_npc(action_n)
                    used_in_cycle.add(action_n)
                    
                    if env.player_hp < prev_player_hp:
                        damage_to_player_total += (prev_player_hp - env.player_hp)

                    # latencja: jeśli akcję już „widziano” i jeszcze nie zarejestrowano użycia → zapisz
                if action_n in LEARNABLE:
                    if action_n in first_seen_cycle and action_n not in first_used_cycle:
                        first_used_cycle[action_n] = c  # pierwszy raz użyta w tym cyklu

                env.tick_cooldowns()
                t1 = time.perf_counter()
                cpu_times.append(t1 - t0)
            
            # Pokrycie dla cyklu c: ile z akcji z LIGHT[c-1] zostało użytych w cyklu c
            ref = {a for a in observed_prev if a in LEARNABLE}
            used = {a for a in used_in_cycle if a in LEARNABLE}
            if ref:
                coverage_per_cycle.append(len(used & ref) / len(ref))
            if used:
                unlearned_rate_c = len(used - ref) / len(used)
                unlearned_rate_per_cycle.append(unlearned_rate_c)
            
            light_history.append(observed_light)  # dodanie observed_light z bieżącego LIGHT[c] do historii obserwacji
    
    # ---------------- Agregacja metryk ----------------
    m1_coverage = sum(coverage_per_cycle) / len(coverage_per_cycle) if coverage_per_cycle else float('nan')
    m2_unlearned_usage = (sum(unlearned_rate_per_cycle)) / len(unlearned_rate_per_cycle) if unlearned_rate_per_cycle else float('nan')

    # Latencja liczona tylko dla akcji, które kiedykolwiek zobaczono
    seen_f = set(first_seen_cycle)
    used_f = set(first_used_cycle)
    latencies = [first_used_cycle[a] - first_seen_cycle[a] for a in (seen_f & used_f)]
    m3_latency = (sum(latencies) / len(latencies)) if latencies else float('nan')
    m4_missed_rate = (len(seen_f - used_f) / len(seen_f)) if seen_f else float('nan')

    m5_cpu_ms = 1000.0 * (sum(cpu_times) / len(cpu_times)) if cpu_times else 0.0
    difficulty = float(damage_to_player_total)

    return {
        'm1_coverage': m1_coverage,
        'm2_unlearned_usage': m2_unlearned_usage,
        'm3_latency_cycles': m3_latency,
        'm4_missed_actions_rate': m4_missed_rate,
        'm5_cpu_ms_per_tick': m5_cpu_ms,
        'difficulty_proxy': difficulty,
    }


def run_experiments(
    out_csv_path,
    seeds: Iterable[int] = (0, 1, 2, 3, 4),
    condition: str = 'memory',
    **episode_kwargs,
):
    """
    Uruchom serię epizodów i zapisz wyniki do CSV.

    :param out_csv_path: ścieżka pliku CSV do zapisu wyników
    :param seeds: lista seedów
    :param condition: 'baseline' lub 'memory'
    :param episode_kwargs: parametry przekazywane do run_episode (np. memory_k=1)
    """
    import csv

    rows: List[dict] = []
    for s in seeds:
        res = run_single_experiment(seed=s, condition=condition, **episode_kwargs)
        row = {'seed': s, 'condition': condition}
        row.update(res)
        rows.append(row)

    # zapis CSV
    out_csv_path = str(out_csv_path)
    with open(out_csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return rows
