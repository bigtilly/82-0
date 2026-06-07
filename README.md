# 82-0 NBA Draft Simulator

A Monte Carlo optimizer and strategy guide for the [82-0 web game](https://82-0.vercel.app), where you build a 5-player historical NBA roster and simulate a full 82-game season.

---

## How the Game Works

Each draft round you spin a slot machine that picks:
1. **Era** — uniformly random from 7 decades (1960s–2020s)
2. **Team** — uniformly random within that era

You see all players from that team/era combo and pick one for an open roster slot (PG, SG, SF, PF, or C). The player must be eligible for the slot based on their recorded positions.

**Resources per draft:**
- 1 team reroll (keeps era, spins a new team)
- 1 era reroll (keeps team, spins a new era)
- Free restarts (refresh the page anytime)

**Uniqueness rule:** The same player name can only appear once on your roster, even if they exist in multiple team/era combos (e.g. Wilt on GSW 1960s and PHI 1960s — pick one).

---

## Scoring (Classic Mode)

Team OVR is calculated from raw cumulative stats across all 5 players:

```
Team OVR = 100 × (
    Σ PPG / 133.4 × 0.46 +
    Σ RPG / 39.7  × 0.25 +
    Σ APG / 29.3  × 0.18 +
    adj_SPG / 6.1 × 0.07 +
    adj_BPG / 3.2 × 0.04
)
```

`adj_SPG` and `adj_BPG` scale up stats to compensate for players with missing data:
```
adj_SPG = Σ(spg where spg > 0) × (5 / count_with_spg)
```
1960s players have no recorded SPG/BPG — their slots are covered by the scaling of teammates who do.

**Wins projection:**
```
Wins = round(82 × min(OVR / 110, 1) ^ 1.15)
```
82-0 requires OVR ≥ ~110.

---

## Project Structure

| File | Purpose |
|------|---------|
| `engine.py` | Python port of the Classic mode scoring engine |
| `simulator.py` | Data loading, spin mechanics, player uniqueness |
| `optimizer.py` | EV-based pick/reroll decisions, stat_contribution ranking |
| `analyzer.py` | Monte Carlo runner — win distribution and 82-0 rate |
| `game_logic.ipynb` | Interactive walkthrough: scoring, player tiers, strategy |

---

## Running the Simulator

```bash
pip install jupyter

# Run 10,000 drafts (default)
python analyzer.py

# Larger sample
python analyzer.py --n 100000

# No rerolls (pure random)
python analyzer.py --n 50000 --rerolls-team 0 --rerolls-decade 0
```

---

## How the Simulator Works

### Simulator (`simulator.py`)

Replicates the game's spin and selection mechanics exactly:

- **Era-first spin:** picks one of 7 eras uniformly at random (1/7 each), then picks a team uniformly within that era — matching the actual game behavior
- **Player pool:** loads the full player dataset, builds a team/era index, and filters out players with corrupted stat entries
- **Player uniqueness:** tracks drafted players by `baseSlug` — the same player appearing across multiple team/era combos can only be drafted once per roster
- **Eligibility:** a player can only be picked if they have at least one open position slot that matches their recorded positions array

### Optimizer (`optimizer.py`)

Decides the best action at each round — pick a player, use the team reroll, or use the era reroll.

**Player scoring (`stat_contribution`):**  
Every player is scored by their direct weighted contribution to the team OVR formula:
```
score = ppg/133.4 × 0.46 + rpg/39.7 × 0.25 + apg/29.3 × 0.18 + spg/6.1 × 0.07 + bpg/3.2 × 0.04
```
This is precomputed for every player in every team/era combo at startup.

**Baseline expected value:**  
For each position slot, the optimizer precomputes the weighted average `stat_contribution` of the best available player for that slot across all 180 possible spins (era-first weighted). This is the baseline — what a random spin is worth for any given open slot.

**Pick value:**  
When evaluating a player, the pick's total value is:
```
pick_value = player_score + sum(expected_future_value for each remaining open slot)
```
The future value per remaining slot uses the precomputed baseline. This means each pick is evaluated against what you'd expect to get for those slots in future rounds.

**Reroll decision:**  
At each round the optimizer computes three values:
1. `pick_value` — best available player on the current spin
2. `team_reroll_ev` — average pick value across all other teams in the same era
3. `era_reroll_ev` — average pick value across all other eras for the same team

It takes whichever action has the highest value, within the 1+1 reroll budget.

### Analyzer (`analyzer.py`)

Runs the optimizer through thousands of simulated drafts via Monte Carlo and collects statistics:

- Runs N complete 5-round drafts using the optimizer's pick/reroll decisions
- Records final wins, which players appeared, which team/era combos were used
- Reports win distribution, 82-0 rate, top players in winning rosters, and top combos

```bash
python analyzer.py --n 10000
```

---

## Human Strategy Guide

### The Mental Score Formula

Calculate each player's value with:

```
Score = PPG + 2×RPG + 2×APG + 3×SPG + 3×BPG
```

For **1960s players** (no SPG/BPG recorded): use `PPG + 2×RPG + 2×APG` only.

### Tier Thresholds

| Score | Tier | What to do |
|-------|------|-----------|
| ≥ 80 | **S** | Lock in immediately, no question |
| ≥ 63 | **A** | Strong pick |
| ≥ 50 | **B** | Take if rerolls are gone |
| ≥ 46 | **C** | Marginal — only if totally out of options |
| < 46 | — | Reroll or restart |

### Top Players by Mental Score

| Score | Player | Team / Era |
|-------|--------|-----------|
| 97.7 | Wilt Chamberlain | GSW 1960s |
| 89.1 | Wilt Chamberlain | PHI 1960s |
| 83.6 | Kareem Abdul-Jabbar | MIL 1970s |
| 78.1 | Kareem Abdul-Jabbar | LAL 1970s |
| 76.9 | Nikola Jokić | DEN 2020s |
| 74.0 | Russell Westbrook | WAS 2020s |
| 71.7 | Wilt Chamberlain | LAL 1960s |
| 70.7 | Luka Dončić | DAL 2020s |
| 70.5 | Giannis Antetokounmpo | MIL 2020s |
| 69.7 | DeMarcus Cousins | NOP 2010s |
| 69.4 | Bob McAdoo | LAC 1970s |
| 69.2 | Bill Russell | BOS 1960s |
| 68.9 | Hakeem Olajuwon | HOU 1990s |
| 68.8 | Michael Jordan | CHI 1980s |
| 68.8 | Moses Malone | HOU 1980s |
| 68.2 | David Robinson | SAS 1990s |
| 68.1 | Oscar Robertson | SAC 1960s |
| 68.0 | James Harden | BKN 2020s |
| 67.8 | Shaquille O'Neal | ORL 1990s |
| 67.5 | Bob Pettit | ATL 1960s |

### Round 1 — Should I Restart?

Restart if the best available player on your first spin scores **below 63**. Round 1 sets the floor — anything below Tier A means you're already behind.

### Every Round — Reroll Decision

**Use team reroll if** the best available player scores **below 50**.
The team reroll keeps the era and picks a new team — you stay in the same statistical pool.

**Use era reroll to target a specific legend:**

| Team | Target Era | Player | Score |
|------|-----------|--------|-------|
| GSW | 1960s | Wilt | 97.7 |
| PHI | 1960s | Wilt | 89.1 |
| MIL | 1970s | Kareem | 83.6 |
| LAL | 1970s | Kareem | 78.1 |
| DEN | 2020s | Jokić | 76.9 |
| WAS | 2020s | Westbrook | 74.0 |
| DAL | 2020s | Luka | 70.7 |
| LAL | 1960s | Wilt | 71.7 |
| NOP | 2010s | Cousins | 69.7 |
| LAC | 1970s | McAdoo | 69.4 |
| BOS | 1960s | Bill Russell | 69.2 |
| HOU | 1990s | Hakeem | 68.9 |
| CHI | 1980s | MJ | 68.8 |
| SAS | 1990s | Robinson | 68.2 |
| SAC | 1960s | Oscar Robertson | 68.1 |
| MIN | 2000s | Garnett | 67.1 |

### The 82-0 Threshold

Your 5 players' combined mental scores need to reach **~320**.

- **BPG-heavy teams** (Kareem, Hakeem, Robinson, Wemby): BPG is underweighted in the formula — you'll outperform the estimate. 315 is enough.
- **APG-heavy teams** (Westbrook, Harden, Magic): APG is slightly overweighted — aim for 325+ to be safe.

You generally need **at least one Tier S or two Tier A players** to build a realistic 82-0 roster.

### Defensive Bonus (SPG/BPG Scaling)

When you have old-era players with no SPG/BPG data, the engine scales up your modern players' defensive stats:

- 1 null-SPG player + 4 with SPG → 4 players scaled ×1.25
- 2 null-SPG players + 3 with SPG → ×1.67
- 3 null-SPG players + 2 with SPG → ×2.5

**Implication:** If you draft Wilt or Oscar Robertson (1960s, no defensive stats), your remaining picks' SPG/BPG are worth more than face value. Prioritize players with high BPG (Kareem 3.41, Hakeem 3.46, Robinson 3.38, Wembanyama 3.5) or high SPG (MJ 2.81) to maximize this effect.

---

## Key Findings from Simulation

- **Era-first spin probability:** Each era has exactly 1/7 chance regardless of team count. 1960s combos (14 teams) come up as often as 2020s combos (30 teams) — but each specific 1960s team is nearly twice as likely to be selected within that era spin.
- **Wilt GSW 1960s** is the single most impactful player in the game by a wide margin (score 97.7 vs next best 89.1).
- **BPG is undervalued** by the mental formula — rim protectors consistently outperform their estimated score.
