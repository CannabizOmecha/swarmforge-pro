# MindGrove 🌿

A pocket-sized overworld game — Pokémon-MMO-style controls — that is secretly a
science-based cognitive trainer. You wander a grove with a touch D-pad and an
**A** button; four shrines each train a distinct executive function, and the game
continuously reshapes itself around how your mind is developing.

**Zero dependencies. One file. Works offline.** Open `index.html` on your phone,
or serve the folder (`python3 -m http.server`) and visit it from your phone on
the same network. Progress is saved locally on the device.

## Controls

| Input | Action |
|---|---|
| On-screen D-pad (or arrow keys / WASD) | Grid-based walking, hold to glide |
| **A** button (or Z / Enter / Space) | Talk, advance dialogue, start trials |

Walk up to a shrine, the Sage, or the old sign and press **A**.

## The four shrines

| Shrine | Trains | Task paradigm |
|---|---|---|
| Memory Shrine | Working memory | Corsi spatial span — repeat growing light sequences |
| Focus Shrine | Inhibitory control | Stroop — answer the ink color, not the word |
| Shift Shrine | Cognitive flexibility | Task switching — the rule (SHAPE/COLOR) changes under you |
| Pattern Shrine | Fluid reasoning | Sequence induction — infer compound rules, pick what comes next |

These are the three core executive functions (working memory, inhibition,
flexibility — Diamond, 2013) plus fluid reasoning, the function they feed.

## How the game grows with you (the science)

- **Zone of proximal development → adaptive staircase.** Every shrine has a
  continuous "depth" level. After each session the staircase nudges depth so you
  hover near ~75–85% accuracy — hard enough to grow, never hopeless. This is
  Vygotsky's ZPD operationalized, and matches the empirical "~85% rule" for
  optimal training difficulty (Wilson et al., 2019).
- **Flow channel.** Because difficulty tracks demonstrated skill, challenge and
  ability rise together — the boredom/anxiety balance from Csikszentmihalyi's
  flow model is maintained automatically.
- **Forgetting curves → spaced repetition, diegetically.** Each skill has a
  vitality that decays exponentially (Ebbinghaus); its half-life lengthens as
  your depth grows (stability growth, as in SuperMemo/FSRS-style schedulers).
  Fading shrines literally glow brighter in the overworld, pulling you back at
  the moment re-training roots deepest. The Sage names your weakest skill.
- **Interleaving & desirable difficulties.** The world layout and the Sage's
  guidance push you to rotate shrines rather than grind one (Rohrer; Bjork's
  "desirable difficulties" — harder-feeling practice that produces more durable
  learning).
- **Growth mindset framing.** All feedback praises strategy, effort, and
  persistence — never innate talent (Dweck). Failed sessions get explicit
  "struggle is the mechanism" framing; difficulty drops are framed as the right
  rung of the ladder, not punishment.
- **Retrieval practice.** Every trial is active recall/production, never passive
  review (the testing effect).
- **Per-trial micro-staircases.** Time pressure, switch probability, congruency
  ratio, sequence length, grid size, and rule count all scale with depth, so the
  *texture* of a task changes as you advance — not just "more of the same."

## Architecture notes

Everything lives in `index.html`:

- **Overworld** — canvas tilemap with camera clamp, grid movement with smooth
  interpolation and held-direction gliding (the Pokémon feel), procedurally
  drawn tiles/sprites (no assets).
- **Adaptive engine** — `adaptLevel()` (session staircase), `vitality()`
  (forgetting-curve decay), `weakestSkill()` (spacing scheduler).
- **Puzzle framework** — async trial loops with a generation counter so quitting
  a trial cleanly aborts it; shared timed-choice and feedback primitives.
- **Persistence** — `localStorage`, versioned key (`mindgrove-save-v1`).

## References (selected)

- Diamond, A. (2013). Executive functions. *Annual Review of Psychology.*
- Wilson, R. C. et al. (2019). The eighty five percent rule for optimal learning. *Nature Communications.*
- Bjork, R. A. & Bjork, E. L. — desirable difficulties in learning.
- Dweck, C. (2006). *Mindset.*
- Cepeda, N. J. et al. (2006). Distributed practice in verbal recall tasks. *Psychological Bulletin.*
- Rohrer, D. & Taylor, K. (2007). The shuffling of mathematics problems improves learning.
- Csikszentmihalyi, M. (1990). *Flow.*
