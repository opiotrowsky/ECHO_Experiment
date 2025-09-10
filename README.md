
# ECHO-like Experiment

Minimalny prototyp do pracy magisterskiej:
- Symulator siatkowy 45x15
- Gracz skryptowy
- NPC: prosta AI + "gating" akcji w fazie DARK
- Dwie kondycje: `memory` (pamięć 1 cyklu + gating) vs `baseline` (bez pamięci/gatingu)
- Metryki:
  - **M1 pokrycie akcji**: odsetek akcji z LIGHT[c] użytych przez NPC w cyklu c+1
  - **M2 użycie niewyuczonych**: miara użytych w cyklu c+1 akcji, które nie były zarejestrowane w LIGHT[c] 
  - **M3 latencja**: ile cykli mija do pierwszego użycia nowej akcji gracza (tu: przybliżenie 1 lub 2)
  - **M4 niepokryte akcje**: ile akcji zarejestrowanych w LIGHT[c] nie zostało użytych w cyklu c+1
  - **M5 koszt CPU**: ms/tick (uśrednione)
  - **Difficulty proxy**: spadek HP gracza (orientacyjnie)

## Uruchomienie w terminalu
```
cd echo_experiment
python run_experiment.py
python analysis_plot.py
```
Wyniki CSV i wykresy zapisują się w `data/`.
