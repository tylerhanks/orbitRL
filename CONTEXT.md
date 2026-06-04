# Context — orbitRL

Glossary of domain terms. Definitions only — no implementation details.

## Simulation

The shared, headless core of OrbitXL: the physics, enemies, difficulty zones,
and scoring that advance every frame, independent of who controls the orbiting
bodies (a human player or AI agents) and independent of whether anything is
drawn. Each **World** composes the Simulation with its own control and
presentation processors.

## Environment

A headless, steppable interface to the **Simulation** for one **Episode** of N
**Agents**. The Environment is reset and advanced one tick at a time by an
external caller, who supplies one **Action** per Agent and receives back an
**Observation**, a **Reward**, and a done flag per Agent. It is the seam a
**Trainer** drives and the **RL Lab** renders.

## Episode

One run of the Simulation from a reset until every Agent is dead. An Agent dies
by flying past the outer ring, falling into the black hole, or colliding with an
enemy. Cumulative score over an Episode is an Agent's fitness.

## Agent

One AI-controlled orbiting body in an Environment. Agents are addressed by a
stable index for the whole Episode; a dead Agent keeps its index.

## Observation

What an Agent perceives on a given tick: its own orbital state (radius, angle,
radial velocity, zone) and the enemy field. The Trainer decides how to turn an
Observation into model input.

## Action

An Agent's choice for one tick: push outward or fall inward. The only control an
Agent has over its orbit; angular motion is fixed by the Agent's zone.

## Reward

The signal returned to a Trainer for an Agent on a tick: the gain in that Agent's
score since the previous tick. Distinct from cumulative score (the Episode-long
fitness).

## Trainer

A caller that learns: it drives an Environment by choosing Actions from its
policies, reads Rewards and Observations, and reads cumulative scores as fitness
at Episode end. Runs without rendering.

## RL Lab

The on-screen demo: a pygame adapter that renders an Environment driven by
default (untrained) policies, resetting each Episode so a human can watch.
