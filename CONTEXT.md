# Context — orbitRL

Glossary of domain terms. Definitions only — no implementation details.

## Simulation

The shared, headless core of OrbitXL: the physics, enemies, difficulty zones,
and scoring that advance every frame, independent of who controls the orbiting
bodies (a human player or AI agents) and independent of whether anything is
drawn. Each **World** composes the Simulation with its own control and
presentation processors.
