"""
agent.py — prosty agent BT (Behavior Tree) z respektowaniem „gatingu” akcji.

Interfejs kompatybilny z experiment.py:
- klasa BTGatedAgent(...)
- metoda pick_action(env, allowed_actions) -> str | None

Kolejność priorytetów (BT):
1) Jeśli dystans == 1 i 'ATTACK' dozwolony -> ATTACK
2) Jeśli dystans >= skill_min_distance i 'SKILL' dozwolony i brak CD -> SKILL
3) Ruch w stronę gracza (oś o większej odległości), ale tylko spośród dozwolonych ruchów
4) Fallback: dowolna dozwolona akcja (iteracyjnie)
5) Jeśli nic nie jest dozwolone -> None

Uwagi:
- „allowed_actions” pochodzi z mechanizmu „gatingu” w fazie DARK – zwykle jest zbiorem
  akcji zaobserwowanych u gracza w poprzednim cyklu (albo pełnym ACTIONS w baseline).
- Agent nie modyfikuje „allowed_actions”; jedynie je respektuje.
"""

from __future__ import annotations

from typing import Iterable, Optional, Set


class BTGatedAgent:
    def __init__(
        self,
        skill_min_distance: int = 3,
        prefer_axis_with_larger_gap: bool = True,
    ) -> None:
        """
        :param skill_min_distance: minimalny dystans manhattan, przy którym SKILL ma sens (agresywny leap)
        :param prefer_axis_with_larger_gap: gdy True, wybierz ruch najpierw po osi z większym |delta|
        """
        self.skill_min_distance = int(skill_min_distance)
        self.prefer_axis_with_larger_gap = bool(prefer_axis_with_larger_gap)

    # ------------------------------
    # Główne API
    # ------------------------------
    def pick_action(self, env, allowed_actions: Iterable[str]) -> Optional[str]:
        """Zwróć wybraną akcję lub None, jeśli żadna nie jest dozwolona."""
        allowed: Set[str] = set(allowed_actions)

        if not allowed:
            return None

        # 1) ATTACK jeśli stoimy obok i jest dozwolony
        if env.dist() == 1 and 'ATTACK' in allowed:
            return 'ATTACK'

        # 2) SKILL (agresywny leap) gdy jest sens strategiczny i CD==0
        if (
            env.dist() >= self.skill_min_distance
            and 'SKILL' in allowed
            and getattr(env, 'skill_cd_npc', 0) == 0
        ):
            return 'SKILL'

        # 3) Ruch w stronę gracza – wybór osi i kierunku
        move = self._move_towards_player(env, allowed)
        if move is not None:
            return move

        # 4) Fallback: pierwsza z dozwolonych akcji (stabilny porządek po sortowaniu)
        for a in sorted(allowed):
            return a

        # 5) Nic nie można wykonać
        return None

    # ------------------------------
    # Pomocnicze
    # ------------------------------
    def _move_towards_player(self, env, allowed: Set[str]) -> Optional[str]:
        """Wybierz ruch zbliżający do gracza (spośród dozwolonych)."""
        dx = env.player[0] - env.npc[0]
        dy = env.player[1] - env.npc[1]

        # zbuduj preferencje ruchów (kolejność kandydatów)
        candidates = []
        if self.prefer_axis_with_larger_gap:
            if abs(dx) >= abs(dy):
                candidates = [('MOVE_right' if dx > 0 else 'MOVE_left'), ('MOVE_down' if dy > 0 else 'MOVE_up')]
            else:
                candidates = [('MOVE_down' if dy > 0 else 'MOVE_up'), ('MOVE_right' if dx > 0 else 'MOVE_left')]
        else:
            # prostsza logika: najpierw w poziomie, potem w pionie
            candidates = [('MOVE_right' if dx > 0 else 'MOVE_left'), ('MOVE_down' if dy > 0 else 'MOVE_up')]

        for a in candidates:
            if a in allowed:
                return a
        return None
