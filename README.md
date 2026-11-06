# Pitching at Altitude: Which Pitchers Hold Up at Coors Field?

**Elliot Malsam** · [elliotma27.github.io](https://elliotma27.github.io) · 2025 Statcast analysis in SQL (SQLite) and Python, tested out of sample on 2026 · [Full brief (PDF)](Elliot_Malsam_Coors_Pitching_Brief.pdf)

## Question
Which pitcher profiles lose the least at Coors Field, why, and which pitchers fit that profile?

## Method
- Pulled the 2025 regular season of Statcast data (about 124,000 balls in play) with `pybaseball` and loaded it into SQLite.
- **Mechanism:** xwOBA is built only from exit velocity and launch angle, so it doesn't know about altitude. Comparing actual minus expected wOBA at Coors against other parks isolates where the park itself adds damage.
- **Archetypes:** grouped 311 pitchers (150+ balls in play) into thirds by fly-ball rate and hard-hit rate (SQL window functions), then compared wOBA allowed at Coors vs. elsewhere.
- **Coors Fit Score:** built a translation table of how much each exit velocity / launch angle bin gains at Coors (shrunk toward zero where Coors data is thin), then ran every pitcher's road batted balls through it to project his Coors penalty.

## Findings
**1. Coors amplifies fly balls far more than ground balls.** Relative to other parks, fly balls produced +0.089 wOBA beyond their contact quality, line drives +0.048, ground balls only +0.013.

![Mechanism](results_2025/chart_mechanism.png)

**2. Fly-ball pitchers lose the most, and fly balls matter more than hard contact.** Fly-ball-heavy pitchers allowed +0.057 wOBA more at Coors (±0.030). Hard-contact pitchers without a fly-ball tendency lost about the same as average (+0.035). Contact managers showed no penalty, but on only 207 Coors PA, so that estimate is very uncertain.

![Archetypes](results_2025/chart_archetypes.png)

**3. The best fits combine strikeouts and ground balls, but fit is a tiebreaker.** Projected penalties span only +0.014 to +0.025 wOBA, while talent (road wOBA) ranges from .22 to .38. Coors-proof starters include José Soriano, Tylor Megill, and Yoshinobu Yamamoto; relievers include Jhoan Durán, Abner Uribe, and Brad Keller. Full rankings: [`coors_fit_scores.csv`](results_2025/coors_fit_scores.csv).

![Fit score](results_2025/chart_fit_score.png)

## Validation
Within 2025, projected and actual Coors penalties were essentially uncorrelated at the pitcher level (r = -0.03, n = 61), and out of sample the 2025 scores did not predict 2026 Coors results (see below). The score describes contact profiles well but is not yet a reliable predictor for individual pitchers.

## What I'd explore next: scouting and development
If the Coors-fit profile is rare and expensive to acquire, it may be worth building instead of buying: scouting college and high school pitchers who already limit fly balls, and developing ground-ball traits (sinkers, steeper approach angles) within the system. The first question to answer is whether fly-ball tendencies carry over from college and the minors to the majors.

## Limitations
Single-season Coors samples are small. Coors PA skew toward Rockies pitchers, and visiting pitchers at Coors face the Rockies' own lineup, which was weak in 2025 and likely hides some of the park effect. Weather, the humidor, and reduced breaking-ball movement aren't modeled. Archetype cutoffs are simple thirds.

## Next steps
Pool three or more seasons, project from stable traits like fly-ball rate, adjust for opponent quality, and add pitch-level traits.

---

# Study 2: Which pitches protect against Coors, and does the Rockies' mix use them?

**Finding 4: Splitters, changeups, and sinkers keep the ball on the ground; four-seamers get punished.** Splitters pair a .345 whiff rate with a .531 ground-ball rate and low hard contact, and lost almost nothing at Coors (+0.005, small sample). Sinkers produced the most ground balls (.548) and one of the smallest Coors penalties (+0.019). Four-seamers allowed the most fly balls, hard contact, and barrels, with a clear Coors penalty in both seasons (+0.054 in 2025, +0.039 in 2026). Sweepers were the most punished pitch at Coors in 2025 (+0.103) but not in 2026 (+0.020), so I treat that as noise.

![Pitch types](results_2025/chart_pitch_types.png)
![Pitch types at Coors](results_2025/chart_pitch_coors.png)

**Finding 5: In 2025, the Rockies leaned on the pitch Coors punishes most.** Rockies pitchers threw four-seamers 40.6% of the time vs. 32.0% league-wide, and sinkers at half the league rate (7.8% vs. 15.6%). Their mix was nearly identical at home and on the road, so it isn't a deliberate altitude adjustment. Changeups and splitters are both underused by the Rockies and better than average league-wide.

**2026 update:** the Rockies moved sharply toward the league mix. Four-seamers fell from 40.6% to 30.6% and sinkers nearly doubled (7.8% to 14.6%). One gap remains: they threw fewer sinkers at home (12.6%) than on the road (16.4%), the opposite of what Coors would suggest. Full table: [`rockies_pitch_mix.csv`](results_2025/rockies_pitch_mix.csv) and [`pitch_type_profile.csv`](results_2025/pitch_type_profile.csv).

![Rockies pitch mix](results_2025/chart_rockies_mix.png)

**Development takeaway:** for Coors-bound pitchers, prioritize splitters, changeups, and sinkers, and where an arsenal allows, rely less on four-seamers at home, and keep sinkers in the mix at Coors.

**Caveats:** pitch mix is limited by each pitcher's arsenal, so this is a development direction rather than a usage mandate. League results partly reflect who throws each pitch, high-ride four-seamers likely fare better than others, the splitter's Coors estimate rests on 126 balls in play, and team assignment is approximate (28 Rockies pitchers in 2025, 34 in 2026).

---

# Does it hold up in 2026? What replicated and what didn't

I reran every step on the 2026 season (outputs in [`results_2026/`](results_2026/)), then tested whether 2025 labels and scores predicted 2026 results (`07_validate_2026.py`).

| Finding | 2025 | 2026 | Held up? |
|---|---|---|---|
| Coors boost on fly balls vs. ground balls | +0.089 vs. +0.013 | +0.056 vs. +0.018 | Yes |
| Fly-ball-heavy pitchers' Coors penalty (same season) | +0.057 (±0.030) | +0.047 (±0.023) | Yes |
| Contact managers' Coors penalty (same season) | 0.000 (±0.066) | +0.018 (±0.059) | Directionally |
| Four-seam Coors penalty | +0.054 | +0.039 | Yes |
| Sinker Coors penalty | +0.019 | +0.024 | Yes |
| Sweeper Coors penalty | +0.103 | +0.020 | No |
| 2025 archetype predicts 2026 Coors results | | Contact managers +0.087 (±0.067) | No |
| 2025 Fit Score predicts 2026 Coors results | | No pattern (r = -0.10) | No |
| Fly-ball rate stable year to year | | r = 0.64 (n = 190) | Yes |

![Validation](results_2026/chart_validation_2026.png)

**What I take from this:** the park effect and the trait are real; the individual predictions are not yet. Across both seasons, Coors adds the most damage on fly balls, and within each season fly-ball pitchers lose the most. Fly-ball rate is also a fairly stable skill (r = 0.64), more stable than hard-hit rate (r = 0.50). But labeling a pitcher from one season and predicting his next season at Coors did not work: the 2025 contact managers did worst at Coors in 2026 (on only 247 PA), and the Fit Score showed no predictive pattern. Individual Coors samples are tiny, and the two-trait contact-manager label reshuffles a lot year to year. Next: pool more seasons and project from stable traits before relying on this for individual decisions.

## Reproduce
```
pip install -r requirements.txt
python3 01_pull_data.py        # downloads 2025 Statcast (slow)
python3 02_build_db.py         # builds coors.db
# run queries.sql (Q1, Q2, Q3) in DB Browser for SQLite, then Write Changes
python3 03_charts_and_fits.py
python3 04_coors_fit_score.py
python3 05_pitch_types.py
python3 06_rockies_pitch_mix.py
# for 2026: copy the folder, change the season dates/filenames in 01 and 02, rerun, then:
python3 07_validate_2026.py   # run from the 2026 folder; reads ../rockiesproject/coors.db
```
