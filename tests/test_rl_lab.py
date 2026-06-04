from orbitrl.rl_lab import RLLab


def test_rl_lab_runs_episodes_and_prints(screen, capsys):
    lab = RLLab(screen, seed=11)
    # Deterministic fall-inward policies so episodes end fast (~80 ticks).
    lab.policies = [lambda _obs: False for _ in range(lab.sim.n)]

    for _ in range(300):
        lab.tick(screen)

    assert lab.episode > 1, "expected at least one episode to complete and reset"
    out = capsys.readouterr().out
    assert "[episode 1] scores:" in out
