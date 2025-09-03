"""
viewer_ascii.py — prosta wizualizacja 15x15 i tryb sterowania graczem.

Tryby:
- scripted: gracz = ScriptedPlayer; animacja ASCII (opcjonalnie zapis do pliku)
- human:    gracz sterowany z klawiatury (WASD = ruch, J = ATTACK, K = SKILL, Q = quit)

Przykłady:
  python viewer_ascii.py --mode scripted --cycles 1 --light_ticks 20 --dark_ticks 20 --speed 0.1
  python viewer_ascii.py --mode human    --cycles 1 --light_ticks 10 --dark_ticks 10
  python viewer_ascii.py --mode scripted --record data/demo_frames.txt --speed 0.0
"""

from __future__ import annotations

import argparse
import time
from typing import List, Set, Optional

from env import GridEnv, MOVES_ONLY, LEARNABLE
from player import ScriptedPlayer
from agent import BTGatedAgent


def render_grid(env: GridEnv) -> List[str]:
    grid = [['.' for _ in range(env.w)] for _ in range(env.h)]
    px, py = env.player
    nx, ny = env.npc
    if (px, py) == (nx, ny):
        grid[py][px] = 'X'
    else:
        grid[py][px] = 'P'
        grid[ny][nx] = 'N'
    return[''.join(row) for row in grid]


def frame_header(cycle: int, phase: str, tick: int, env: GridEnv,
allowed: Set[str], action_p: Optional[str], action_n: Optional[str]) -> str:
    lines = []
    lines.append(f'Cycle={cycle} Phase={phase} Tick={tick} | dist={env.dist()} | HPgracza={env.player_hp}  HPnpc={env.npc_hp} | Akcja gracza={env.skill_cd_player}  Akcja npc={env.skill_cd_npc}')
    if phase == 'DARK':
        lines.append(f'Allowed for NPC={sorted(list(allowed))}')
    lines.append(f'Player action={action_p or '-'} | NPC action={action_n or '-'}')
    return '\n'.join(lines)


def run(mode: str, cycles: int, light_ticks: int, dark_ticks: int,
speed: float, record_path: Optional[str], seed: int):

    env = GridEnv(seed=seed)
    player = ScriptedPlayer(rng_seed=seed+13)
    agent = BTGatedAgent()

    def maybe_write(s: str):
        if record_path:
            with open(record_path, 'a') as f:
                f.write(s + '\n')
        else:
            print(s)

    if record_path:
        # clear file
        open(record_path, 'w').close()

    # Scripted:
    if mode == 'scripted':
        for c in range(1, cycles + 1):
            allowed = set(MOVES_ONLY)  # NPC zaczyna tylko z przemieszczaniem się
            learned_prev = {a for a in observed_light if a in LEARNABLE}
            allowed = set(MOVES_ONLY) | learned_prev  # ew. dodanie ruchów dla NPC z LEARNABLE
            observed_light: Set[str] = set()
            # LIGHT:
            for t in range(light_ticks):
                action_p = player.act(env, t, 'LIGHT')
                action_n = agent.pick_action(env, allowed)
                
                env.step_player(action_p)
                observed_light.add(action_p)
                env.step_npc(action_n)
                env.tick_cooldowns()

                # render
                lines = render_grid(env)
                hdr = frame_header(c, 'LIGHT', t, env, allowed, action_p, action_n)
                maybe_write(hdr + '\n' + '\n'.join(lines) + '\n' + '-'*32)
                if speed > 0 and not record_path:
                    time.sleep(speed)

            # DARK:
            for t in range(dark_ticks):
                action_p = player.act(env, t, 'LIGHT')
                action_n = agent.pick_action(env, allowed)
                
                env.step_player(action_p)
                env.step_npc(action_n)
                env.tick_cooldowns()
                
                # render
                lines = render_grid(env)
                hdr = frame_header(c, 'DARK', t, env, allowed, action_p, action_n)
                maybe_write(hdr + '\n' + '\n'.join(lines) + '\n' + '-'*32)
                if speed > 0 and not record_path:
                    time.sleep(speed)

    # Human:
    if mode == 'human':
        observed_light: Set[str] = set()
        for c in range(1, cycles+1):
            allowed = set(MOVES_ONLY)  # NPC zaczyna tylko z przemieszczaniem się
            # last_light = light_history[-1] if len(light_history) > 0 else set()
            learned_prev = {a for a in observed_light if a in LEARNABLE}
            allowed = set(MOVES_ONLY) | learned_prev  # ew. dodanie ruchów dla NPC z LEARNABLE
            observed_light: Set[str] = set()
            # LIGHT:
            for t in range(light_ticks):
                action_p = ask_action_human(env, phase='LIGHT')
                action_n = agent.pick_action(env, allowed)
                
                env.step_player(action_p)
                observed_light.add(action_p)
                env.step_npc(action_n)
                env.tick_cooldowns()

                # render
                lines = render_grid(env)
                hdr = frame_header(c, 'LIGHT', t, env, allowed, action_p, action_n)
                maybe_write(hdr + '\n' + '\n'.join(lines) + '\n' + '-'*32)
                if speed > 0 and not record_path:
                    time.sleep(speed)
            
            # DARK:
            for t in range(dark_ticks):
                action_p = ask_action_human(env, phase='DARK')
                action_n = agent.pick_action(env, allowed)
                
                env.step_player(action_p)
                env.step_npc(action_n)
                env.tick_cooldowns()
                
                # render
                lines = render_grid(env)
                hdr = frame_header(c, 'DARK', t, env, allowed, action_p, action_n)
                maybe_write(hdr + '\n' + '\n'.join(lines) + '\n' + '-'*32)
                if speed > 0 and not record_path:
                    time.sleep(speed)

    else:
        f'Mode does not exist. Please choose "scripted" or "human".'


def ask_action_human(env: GridEnv, phase: str) -> str:
    """
    Mapowanie klawiszy:
      w/s/a/d -> MOVE_up/down/left/right
      j -> ATTACK
      k -> SKILL (jeśli CD==0)
      q -> zakończ program
    """
    while True:
        s = input(f'[{phase}] Wybierz akcję (w/s/a/d/j/k, q=quit): ').strip().lower()
        if s == 'q':
            print('Koniec.')
            raise SystemExit(0)
        keymap = {
            'w': 'MOVE_up',
            's': 'MOVE_down',
            'a': 'MOVE_left',
            'd': 'MOVE_right',
            'j': 'ATTACK',
            'k': 'SKILL',
        }
        if s in keymap:
            a = keymap[s]
            # prosty feedback o cooldownie
            if a == 'SKILL' and env.skill_cd_player > 0:
                print(f'SKILL na cooldownie: {env.skill_cd_player} ticków. Wybierz inną akcję.')
                continue
            return a
        print('Nieznana komenda. Dozwolone: w/s/a/d/j/k, q.')


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['scripted', 'human'], default='human')
    ap.add_argument('--cycles', type=int, default=1)
    ap.add_argument('--light_ticks', type=int, default=20)
    ap.add_argument('--dark_ticks', type=int, default=20)
    ap.add_argument('--speed', type=float, default=0.05, help='opóźnienie między klatkami w trybie scripted')
    ap.add_argument('--record', type=str, default='', help='ścieżka do pliku z zapisem klatek (bez live printów)')
    ap.add_argument('--seed', type=int, default=0)
    return ap.parse_args()


if __name__ == '__main__':
    args = parse_args()
    record = args.record if args.record != '' else None
    print(f'[viewer] Using seed={args.seed}')
    run(args.mode, args.cycles, args.light_ticks, args.dark_ticks, args.speed, record, args.seed)
