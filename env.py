"""
env.py — minimalne środowisko siatkowe dla eksperymentu ECHO-like.

Interfejs jest kompatybilny z resztą projektu:
- stała ACTIONS
- klasa GridEnv(width, height, seed)
- metody: reset_positions(), dist(), step_player(action), step_npc(action), tick_cooldowns()

Semantyka akcji (manhattan grid):
- MOVE_up/down/right/left: przesunięcie o 1 pole, z uwzględnieniem granic planszy.
- ATTACK: jeśli dystans manhattan = 1, zadaj 1 pkt obrażeń przeciwnikowi.
- SKILL:
    * gracz (player): defensywny dash o 2 pola „od” NPC (oś o większej wartości bezwzględnej).
    * NPC: ofensywny leap o 2 pola „w stronę” gracza.
  Obie umiejętności mają niezależny cooldown (domyślnie 5 ticków).

Uwaga na deterministykę: używamy własnego RNG (random.Random(seed)).
"""

from __future__ import annotations

from typing import List
import random

LEARNABLE: set[str] = {'ATTACK', 'SKILL'}
MOVES_ONLY: set[str] = {'MOVE_up', 'MOVE_down', 'MOVE_right', 'MOVE_left'}
ACTIONS: List[str] = ['MOVE_up', 'MOVE_down', 'MOVE_right', 'MOVE_left', 'ATTACK', 'SKILL']

class GridEnv:
    def __init__(self, width: int = 45, height: int = 15, seed: int = 0):
        """Prosta plansza width×height. Pozycje to [x, y] (listy, żeby zachować kompatybilność)."""
        self.w = int(width)
        self.h = int(height)
        self.rng = random.Random(seed)

        # Parametry „gry”
        self.max_hp_player = 10
        self.max_hp_npc = 10
        self.skill_cd_len_player = 5
        self.skill_cd_len_npc = 5

        # Stan bieżący
        self.player: List[int] = [0, 0]
        self.npc: List[int] = [0, 0]
        self.player_hp: int = self.max_hp_player
        self.npc_hp: int = self.max_hp_npc
        self.skill_cd_player: int = 0
        self.skill_cd_npc: int = 0

        self.reset_positions()

    # ---------------------------
    # Narzędzia pomocnicze
    # ---------------------------
    def _clamp_xy(self, x: int, y: int):
        """Przypnij współrzędne do granic planszy (zwraca krotkę (x,y))."""
        x = 0 if x < 0 else x
        y = 0 if y < 0 else y
        x = self.w - 1 if x >= self.w else x
        y = self.h - 1 if y >= self.h else y
        return x, y

    # ---------------------------
    # API środowiska
    # ---------------------------
    def reset_positions(self) -> None:
        """Wylosuj różne pola startowe i zresetuj HP/CD."""
        self.player = [self.rng.randrange(self.w), self.rng.randrange(self.h)]
        self.npc = [self.rng.randrange(self.w), self.rng.randrange(self.h)]
        while self.npc == self.player:
            self.npc = [self.rng.randrange(self.w), self.rng.randrange(self.h)]

        self.player_hp = self.max_hp_player
        self.npc_hp = self.max_hp_npc
        self.skill_cd_player = 0
        self.skill_cd_npc = 0

    def dist(self) -> int:
        """Odległość manhattan między graczem a NPC."""
        return abs(self.player[0] - self.npc[0]) + abs(self.player[1] - self.npc[1])

    # ---------------------------
    # Ruchy gracza i NPC
    # ---------------------------
    def step_player(self, action: str) -> None:
        """Wykonaj akcję gracza i zaktualizuj stan."""
        if action == 'ATTACK':
            if self.dist() == 1:
                self.npc_hp -= 1
            return

        if action == 'SKILL':
            if self.skill_cd_player == 0:
                self.skill_cd_player = self.skill_cd_len_player
                # dash „od” NPC o 2 pola wzdłuż osi o większej wartości bezwzględnej
                dx = self.player[0] - self.npc[0]
                dy = self.player[1] - self.npc[1]
                if abs(dx) >= abs(dy):
                    step = 2 if dx > 0 else -2
                    nx, ny = self.player[0] + step, self.player[1]
                else:
                    step = 2 if dy > 0 else -2
                    nx, ny = self.player[0], self.player[1] + step
                self.player[0], self.player[1] = self._clamp_xy(nx, ny)
            return

        # Ruch o 1 pole
        if action == 'MOVE_up':
            nx, ny = self.player[0], self.player[1] - 1
        elif action == 'MOVE_down':
            nx, ny = self.player[0], self.player[1] + 1
        elif action == 'MOVE_left':
            nx, ny = self.player[0] - 1, self.player[1]
        elif action == 'MOVE_right':
            nx, ny = self.player[0] + 1, self.player[1]
        else:
            return  # nieznana akcja → ignorujemy
        self.player[0], self.player[1] = self._clamp_xy(nx, ny)

    def step_npc(self, action: str) -> None:
        """Wykonaj akcję NPC i zaktualizuj stan."""
        if action == 'ATTACK':
            if self.dist() == 1:
                self.player_hp -= 1
            return

        if action == 'SKILL':
            if self.skill_cd_npc == 0:
                self.skill_cd_npc = self.skill_cd_len_npc
                # leap „do” gracza o 2 pola wzdłuż osi o większej wartości bezwzględnej
                dx = self.player[0] - self.npc[0]
                dy = self.player[1] - self.npc[1]
                if abs(dx) >= abs(dy):
                    step = 2 if dx > 0 else -2
                    nx, ny = self.npc[0] + step, self.npc[1]
                else:
                    step = 2 if dy > 0 else -2
                    nx, ny = self.npc[0], self.npc[1] + step
                self.npc[0], self.npc[1] = self._clamp_xy(nx, ny)
            return

        # Ruch o 1 pole
        if action == 'MOVE_up':
            nx, ny = self.npc[0], self.npc[1] - 1
        elif action == 'MOVE_down':
            nx, ny = self.npc[0], self.npc[1] + 1
        elif action == 'MOVE_left':
            nx, ny = self.npc[0] - 1, self.npc[1]
        elif action == 'MOVE_right':
            nx, ny = self.npc[0] + 1, self.npc[1]
        else:
            return
        self.npc[0], self.npc[1] = self._clamp_xy(nx, ny)

    def tick_cooldowns(self) -> None:
        """Zmniejsz cooldowny umiejętności (nie mniej niż 0)."""
        if self.skill_cd_player > 0:
            self.skill_cd_player -= 1
        if self.skill_cd_npc > 0:
            self.skill_cd_npc -= 1
