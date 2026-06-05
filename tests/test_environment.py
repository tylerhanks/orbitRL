import hashlib
import random

from orbitrl.environment import CAMP_WINDOW_TICKS, EnemyObs, Observation, OrbitSim, flatten

N = 5


def make_script(n: int, steps: int, seed: int = 123) -> list[list[bool]]:
    rng = random.Random(seed)
    return [[rng.random() < 0.5 for _ in range(n)] for _ in range(steps)]


def run_until_all_dead(sim: OrbitSim, max_steps: int = 5000) -> int:
    """Drive every agent inward (fall into the black hole) until the episode ends."""
    for step in range(1, max_steps + 1):
        _obs, _rewards, _dones, all_done = sim.step([False] * sim.n)
        if all_done:
            return step
    raise AssertionError("episode never terminated")


def test_determinism_same_seed_same_actions():
    script = make_script(N, 300)
    a = OrbitSim(N, seed=0, world="det_a")
    a.reset()
    b = OrbitSim(N, seed=0, world="det_b")
    b.reset()
    for t, acts in enumerate(script):
        assert a.step(acts) == b.step(acts), f"trajectory diverged at step {t}"


def test_distinct_worlds_are_isolated():
    a = OrbitSim(N, seed=1, world="iso_a")
    a.reset()
    b = OrbitSim(N, seed=2, world="iso_b")
    b.reset()

    # Stepping a must not touch b's state.
    b_scores_before = b.scores
    for _ in range(120):
        a.step([True] * N)
    assert b.scores == b_scores_before


def test_reset_restores_full_generation():
    sim = OrbitSim(N, seed=7, world="reset")
    sim.reset()
    run_until_all_dead(sim)

    fitness = sim.scores  # readable before the wipe
    assert len(fitness) == N

    obs = sim.reset()
    assert sim.living == N
    assert len(obs) == N
    assert all(o is not None for o in obs)


def test_dead_agents_are_masked_and_earn_no_reward():
    sim = OrbitSim(N, seed=3, world="mask")
    sim.reset()
    dead: set[int] = set()
    for _ in range(5000):
        obs, rewards, dones, all_done = sim.step([False] * N)
        for i in range(N):
            # done iff this agent's observation is masked out
            assert dones[i] == (obs[i] is None)
            # an agent that was already dead earns nothing
            if i in dead:
                assert rewards[i] == 0.0
        dead = {i for i, done in enumerate(dones) if done}
        if all_done:
            break
    assert dead == set(range(N))


def test_reward_is_score_delta():
    sim = OrbitSim(N, seed=4, world="reward")
    sim.reset()
    for acts in make_script(N, 200):
        before = sim.scores
        _obs, rewards, _dones, _all_done = sim.step(acts)
        after = sim.scores
        assert rewards == [float(after[i] - before[i]) for i in range(N)]


def test_enemy_obs_excludes_black_hole():
    sim = OrbitSim(N, seed=5, world="enemies")
    obs = sim.reset()

    # Closed-loop survival (hold inward when too far out) keeps an agent alive past
    # the first enemy spawn (~4s); stop as soon as a living agent perceives enemies.
    enemies: list[EnemyObs] = []
    for _ in range(900):
        acts = [(o.r < 180.0) if o is not None else False for o in obs]
        obs, _r, _d, _a = sim.step(acts)
        living = [o for o in obs if o is not None]
        if living and living[0].enemies:
            enemies = living[0].enemies
            break

    assert enemies, "expected enemies to spawn while an agent survived"
    # The black hole carries Enemy but no EnemyType (radius 50); it must never appear.
    assert all(e.radius in {10.0, 20.0, 30.0} for e in enemies)


def test_flatten_shape_and_dead_agent_zeros():
    obs = Observation(
        r=200.0,
        theta=1.0,
        r_dot=-100.0,
        zone=2,
        alive=True,
        enemies=[EnemyObs(r=300.0, theta=1.0, radius=20.0, speed=-70.0)],
    )
    k = 3
    vec = flatten(obs, k)
    assert vec.shape == (5 + 4 * k,)

    dead = flatten(None, k)
    assert dead.shape == (5 + 4 * k,)
    assert not dead.any()


def test_trajectory_fingerprint_canary():
    """Guards against silent dynamics drift. Re-bless only on intentional changes."""
    sim = OrbitSim(N, seed=0, world="fingerprint")
    sim.reset()
    digest = hashlib.sha256()
    for acts in make_script(N, 300, seed=999):
        _obs, _r, _d, _a = sim.step(acts)
        digest.update(repr(sim.scores).encode())
    assert digest.hexdigest() == FINGERPRINT


def _hold_around_spawn(sim: OrbitSim) -> bool:
    """Drive a bang-bang policy that holds near the r=200 spawn radius (a tight oscillation =
    camping) for one window-plus, returning whether the episode ended."""
    obs = sim.reset()
    for _ in range(CAMP_WINDOW_TICKS + 10):
        acts = [(o.r < 200.0) if o is not None else False for o in obs]
        obs, _r, _d, all_done = sim.step(acts)
        if all_done:
            return True
    return False


def test_camp_timeout_kills_and_penalizes_stationary_agent():
    sim = OrbitSim(1, seed=11, world="camp_on", camp_timeout=True)
    assert _hold_around_spawn(sim), "stationary agent should have been timed out within a window"
    # Negative score is the unambiguous camping signal: only CAMP_PENALTY can drive Score
    # below zero (collision/ring deaths merely stop accrual).
    assert sim.scores[0] < 0


def test_camp_timeout_is_opt_in():
    # Same bang-bang camper, but with the default-off flag: no kill, no penalty.
    sim = OrbitSim(1, seed=11, world="camp_off")
    _hold_around_spawn(sim)
    assert sim.scores[0] >= 0


# Blessed at implementation time; changes only when the simulation dynamics change.
FINGERPRINT = "c21e32d04ee3ee94cf45c4047e69ee4e5a0d24e8df95712efa579458d65697c0"
