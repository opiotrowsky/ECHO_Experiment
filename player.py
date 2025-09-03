"""
player.py — skryptowy „gracz” do eksperymentu ECHO-like.

Interfejs:
- klasa ScriptedPlayer(rng_seed=0, ...)
- metoda act(env, tick, phase) -> str

Założenia:
- „Gracz” czasem atakuje, czasem używa SKILL, a w ruchu ma lekki bias:
  domyślnie „oddalaj się od NPC” (czytelne dla eksperymentu), z domieszką losowości.
- Parametry sterują częstotliwością akcji, aby wygodnie testować pamięć cyklu.

Zwracane akcje pochodzą z env.ACTIONS.
"""

from __future__ import annotations

from typing import Literal
import random
from env import ACTIONS


MovePolicy = Literal['away', 'towards', 'random']


class ScriptedPlayer:
    def __init__(
        self,
        rng_seed: int = 0,
        p_attack_adjacent: float = 0.6,
        p_skill_light: float = 0.12,
        p_skill_dark: float = 0.04,
        move_policy: MovePolicy = 'away',
        jitter_move_prob: float = 0.15,
    ) -> None:
        """
        :param rng_seed: ziarno deterministycznej losowości
        :param p_attack_adjacent: prawd. ATTACK gdy dystans==1
        :param p_skill_light: prawd. użycia SKILL w fazie LIGHT (jeśli CD==0)
        :param p_skill_dark: prawd. użycia SKILL w fazie DARK (jeśli CD==0)
        :param move_policy: 'away' (od NPC), 'towards' (w stronę NPC) lub 'random'
        :param jitter_move_prob: prawd. wykonania kroku losowego zamiast polityki bazowej
        """
        self.rng = random.Random(rng_seed)
        self.p_attack_adjacent = float(p_attack_adjacent)
        self.p_skill_light = float(p_skill_light)
        self.p_skill_dark = float(p_skill_dark)
        self.move_policy = move_policy
        self.jitter_move_prob = float(jitter_move_prob)

    def act(self, env, tick: int, phase: str) -> str:
        """Zdecyduj o akcji na danym ticku i fazie ('LIGHT' / 'DARK')."""
        # 1) Jeśli jesteśmy obok przeciwnika → często atakuj
        if env.dist() == 1 and self.rng.random() < self.p_attack_adjacent:
            return 'ATTACK'

        # 2) Czasem użyj SKILL (zależnie od fazy), tylko gdy brak CD
        p_skill = self.p_skill_light if phase == 'LIGHT' else self.p_skill_dark
        if env.skill_cd_player == 0 and self.rng.random() < p_skill:
            return 'SKILL'

        # 3) Ruch
        if self.rng.random() < self.jitter_move_prob or self.move_policy == 'random':
            return self._random_move()
        if self.move_policy == 'towards':
            return self._move_towards(env)
        # domyślnie: away
        return self._move_away(env)

    # ------------------
    # Ruchy pomocnicze
    # ------------------
    def _random_move(self) -> str:
        return self.rng.choice([a for a in ACTIONS if a.startswith('MOVE_')])

    def _move_towards(self, env) -> str:
        dx = env.player[0] - env.npc[0]
        dy = env.player[1] - env.npc[1]
        # Chcemy iść „w stronę” NPC: odwróć wektor względem pozycji gracza
        # (czyli dąż do zmniejszenia |dx| i |dy|)
        # Wybieramy oś o większym |delta|, żeby ruch był zdecydowany.
        if abs(dx) >= abs(dy):
            return 'MOVE_left' if dx > 0 else 'MOVE_right'
        else:
            return 'MOVE_up' if dy > 0 else 'MOVE_down'

    def _move_away(self, env) -> str:
        dx = env.player[0] - env.npc[0]
        dy = env.player[1] - env.npc[1]
        # Oddalaj się od NPC: zwiększaj |dx| lub |dy| w osi o większym gapie
        if abs(dx) >= abs(dy):
            return 'MOVE_right' if dx > 0 else 'MOVE_left'
        else:
            return 'MOVE_down' if dy > 0 else 'MOVE_up'
