"""
Step 4: Make the two charts for the brief and build the "who fits Coors" list.
Run after the Q2 v2 view (pitcher_archetypes) has been created in coors.db.
Outputs: chart_mechanism.png, chart_archetypes.png, contact_managers_2025.csv
"""
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pybaseball import playerid_reverse_lookup

con = sqlite3.connect("coors.db")

# ---------- Chart 1: the mechanism ----------
# Extra damage at Coors beyond contact quality, by batted-ball type
mech = pd.read_sql("""
    SELECT CASE WHEN home_team = 'COL' THEN 'Coors' ELSE 'Elsewhere' END AS park,
           bb_type,
           AVG(woba_value) - AVG(estimated_woba_using_speedangle) AS gap
    FROM pitches
    WHERE bb_type IS NOT NULL
      AND estimated_woba_using_speedangle IS NOT NULL
      AND woba_denom = 1
    GROUP BY park, bb_type
""", con)
mech = mech.pivot(index="bb_type", columns="park", values="gap")
mech["coors_extra"] = mech["Coors"] - mech["Elsewhere"]
mech = mech.drop(index="popup").sort_values("coors_extra")   # popups: too few at Coors

labels = {"ground_ball": "Ground balls", "line_drive": "Line drives", "fly_ball": "Fly balls"}
fig, ax = plt.subplots(figsize=(7, 4))
ax.barh([labels[i] for i in mech.index], mech["coors_extra"], color=["#8a8a8a", "#5b7fa6", "#333366"])
for i, v in enumerate(mech["coors_extra"]):
    ax.text(v + 0.002, i, f"+{v:.3f}", va="center")
ax.set_xlabel("Extra wOBA at Coors beyond contact quality (actual minus expected, vs. elsewhere)")
ax.set_title("Coors amplifies fly balls far more than ground balls (2025)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("chart_mechanism.png", dpi=200)
plt.close()

# ---------- Chart 2: Coors penalty by archetype, with 95% intervals ----------
pa = pd.read_sql("""
    SELECT a.archetype,
           (p.home_team = 'COL') AS at_coors,
           p.woba_value
    FROM pitches p
    JOIN pitcher_archetypes a ON a.pitcher = p.pitcher
    WHERE p.woba_denom = 1 AND p.woba_value IS NOT NULL
""", con)

rows = []
for arch, g in pa.groupby("archetype"):
    c, o = g[g.at_coors == 1].woba_value, g[g.at_coors == 0].woba_value
    penalty = c.mean() - o.mean()
    se = np.sqrt(c.var() / len(c) + o.var() / len(o))
    rows.append({"archetype": arch, "penalty": penalty, "ci95": 1.96 * se, "coors_pa": len(c)})
arch = pd.DataFrame(rows).sort_values("penalty")
print(arch.round(3).to_string(index=False))

short = {
    "Contact manager (low FB + low hard-hit)": "Contact managers\n(low FB + low hard-hit)",
    "Allows hard contact": "Allows hard contact",
    "Middle": "Middle",
    "Fly-ball heavy": "Fly-ball heavy",
}
fig, ax = plt.subplots(figsize=(7, 4))
ax.barh([short[a] for a in arch.archetype], arch.penalty, xerr=arch.ci95,
        color="#333366", ecolor="#999999", capsize=4)
for i, (v, n) in enumerate(zip(arch.penalty, arch.coors_pa)):
    ax.text(max(v, 0) + 0.004, i + 0.28, f"{v:+.3f}  (n={n:,} Coors PA)", fontsize=8)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Coors penalty: wOBA allowed at Coors minus elsewhere (95% interval)")
ax.set_title("Fly-ball pitchers lose the most at Coors (2025)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("chart_archetypes.png", dpi=200)
plt.close()

# ---------- Who fits: 2025 contact managers ----------
fits = pd.read_sql("""
    SELECT pitcher, bip, fb_rate, hard_hit_rate
    FROM pitcher_archetypes
    WHERE archetype LIKE 'Contact manager%'
    ORDER BY fb_rate + hard_hit_rate
""", con)
names = playerid_reverse_lookup(fits.pitcher.tolist(), key_type="mlbam")
names["name"] = names.name_first.str.title() + " " + names.name_last.str.title()
fits = fits.merge(names[["key_mlbam", "name"]], left_on="pitcher", right_on="key_mlbam", how="left")
fits = fits[["name", "bip", "fb_rate", "hard_hit_rate"]]
fits[["fb_rate", "hard_hit_rate"]] = fits[["fb_rate", "hard_hit_rate"]].round(3)
fits.to_csv("contact_managers_2025.csv", index=False)
print("\nTop contact managers (2025):")
print(fits.head(15).to_string(index=False))

con.close()
print("\nSaved chart_mechanism.png, chart_archetypes.png, contact_managers_2025.csv")
