# Bespoke, esper-backed RL Environment

The RL world is exposed to trainers through `OrbitSim`, a bespoke external-action
Environment (`reset()` / `step(actions) -> obs, rewards, dones, all_done`) backed
by the shared esper simulation spine, rather than a PettingZoo `ParallelEnv`
subclass or a pure-Python reimplementation. We chose bespoke-over-PettingZoo to
avoid the dependency and ceremony (string agent ids, space dicts) for a
from-scratch playground, keeping the interface PettingZoo-shaped so a wrapper is
a small later step; we chose esper-backed-over-pure-Python so the Environment and
the human game share one physics implementation (the spine) instead of forking it.

## Consequences

esper is a global singleton, so `OrbitSim` manages a *named* esper world and
switches into it (only when not already active — esper's component cache is
per-world, so no manual cache clearing is needed). It therefore cannot be driven
from inside another world's `esper.process`, which is why the pygame app's main
loop branches: the RL Lab scene is stepped directly by `OrbitSim`, while the
menu/game/highscores worlds keep the generic `esper.process` path.
