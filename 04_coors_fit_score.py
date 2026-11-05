"""
Step 5: Coors Fit Score.
Projects how every pitcher's batted balls would play at Coors Field, using a
translation table built from where each exit velocity / launch angle combo
gains value at Coors. Uses each pitcher's ROAD batted balls (hundreds per
pitcher) instead of his small Coors sample.

Outputs: coors_fit_scores.csv, chart_fit_score.png, plus validation printouts.
"""
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SHRINK_K = 50        # bins with little Coors data get pulled toward zero
MIN_ROAD_BIP = 150   # minimum road balls in play to be scored

con = sqlite3.connect("coors.db")
pa = pd.read_sql("""
    SELECT pitcher, game_pk, home_team, bb_type, launch_speed, launch_angle, woba_value
    FROM pitches
    WHERE woba_denom = 1 AND woba_value IS NOT NULL
""", con)
pa["at_coors"] = pa["home_team"] == "COL"

# ---------- 1. Coors translation table (EV x LA bins) ----------
bip = pa.dropna(subset=["bb_type", "launch_speed", "launch_angle"]).copy()
bip["ev_bin"] = (np.floor(bip.launch_speed / 10) * 10).clip(60, 110)    # 60 = under 70 mph, 110 = 110+
bip["la_bin"] = (np.floor(bip.launch_angle / 10) * 10).clip(-30, 50)    # -30 = steep grounders, 50 = popups

tbl = (bip.groupby(["ev_bin", "la_bin", "at_coors"]).woba_value
          .agg(["mean", "size"]).unstack("at_coors"))
tbl.columns = ["other_mean", "coors_mean", "other_n", "coors_n"]
tbl = tbl.fillna({"coors_n": 0})
tbl["raw_delta"] = tbl.coors_mean - tbl.other_mean
tbl["delta"] = (tbl.raw_delta * tbl.coors_n / (tbl.coors_n + SHRINK_K)).fillna(0)

print("Biggest Coors boosts by batted-ball bin:")
print(tbl.sort_values("delta", ascending=False).head(8)[["coors_n", "raw_delta", "delta"]].round(3))

bip = bip.merge(tbl[["delta"]], left_on=["ev_bin", "la_bin"], right_index=True, how="left")

# ---------- 2. Translate every pitcher's road batted balls ----------
road_pa = pa[~pa.at_coors]
road_bip = bip[~bip.at_coors]

per_p = road_pa.groupby("pitcher").agg(road_pa=("woba_value", "size"),
                                       road_woba=("woba_value", "mean"),
                                       games=("game_pk", "nunique"))
per_p["road_bip"] = road_bip.groupby("pitcher").size()
per_p["delta_sum"] = road_bip.groupby("pitcher").delta.sum()
per_p = per_p[per_p.road_bip >= MIN_ROAD_BIP].copy()

per_p["projected_penalty"] = per_p.delta_sum / per_p.road_pa            # extra wOBA per PA at Coors
per_p["coors_projected_woba"] = per_p.road_woba + per_p.projected_penalty
per_p["role"] = np.where(per_p.road_pa / per_p.games >= 12, "SP", "RP")  # rough starter proxy

# Actual Coors results, for validation
coors_actual = pa[pa.at_coors].groupby("pitcher").woba_value.agg(coors_pa="size", coors_woba="mean")
per_p = per_p.join(coors_actual, how="left")
per_p["actual_penalty"] = per_p.coors_woba - per_p.road_woba

# Archetype labels from the SQL view
arch = pd.read_sql("SELECT pitcher, archetype, fb_rate, hard_hit_rate FROM pitcher_archetypes", con)
per_p = per_p.join(arch.set_index("pitcher"), how="left")

# ---------- 3. Validation ----------
print("\nVALIDATION 1: projected vs. actual Coors penalty by archetype (PA-weighted)")
v = per_p.dropna(subset=["archetype"]).copy()
v["w_proj"] = v.projected_penalty * v.road_pa
v["w_act"] = v.actual_penalty * v.coors_pa
g = v.groupby("archetype").agg(proj=("w_proj", "sum"), road_pa=("road_pa", "sum"),
                               act=("w_act", "sum"), coors_pa=("coors_pa", "sum"))
g["projected"] = g.proj / g.road_pa
g["actual"] = g.act / g.coors_pa
print(g[["projected", "actual", "coors_pa"]].sort_values("projected").round(3))

big = per_p[per_p.coors_pa >= 20]
r = big[["projected_penalty", "actual_penalty"]].corr().iloc[0, 1]
print(f"\nVALIDATION 2: pitcher-level correlation (pitchers with 20+ Coors PA, n={len(big)}): r = {r:.2f}")
print("(Expect this to be noisy: individual Coors samples are small.)")

# ---------- 4. Names ----------
try:
    from pybaseball import playerid_reverse_lookup
    names = playerid_reverse_lookup(per_p.index.tolist(), key_type="mlbam")
    names["name"] = names.name_first.str.title() + " " + names.name_last.str.title()
    per_p = per_p.join(names.set_index("key_mlbam")["name"])
except Exception as e:
    print("Name lookup failed, using IDs:", e)
    per_p["name"] = per_p.index.astype(str)

out = per_p.reset_index()[["name", "role", "archetype", "road_bip", "fb_rate", "hard_hit_rate",
                           "road_woba", "projected_penalty", "coors_projected_woba",
                           "coors_pa", "actual_penalty"]]
out = out.sort_values("projected_penalty")
out["fit_rank"] = range(1, len(out) + 1)
out.round(3).to_csv("coors_fit_scores.csv", index=False)

cols = ["name", "role", "projected_penalty", "road_woba", "coors_projected_woba"]
print(f"\nMOST COORS-PROOF PROFILES (smallest projected penalty, of {len(out)} pitchers):")
print(out[cols].head(20).round(3).to_string(index=False))
print("\nBEST PROJECTED STARTERS AT COORS (talent + fit):")
print(out[out.role == "SP"].sort_values("coors_projected_woba")[cols].head(15).round(3).to_string(index=False))
print("\nBEST PROJECTED RELIEVERS AT COORS (talent + fit):")
print(out[out.role == "RP"].sort_values("coors_projected_woba")[cols].head(15).round(3).to_string(index=False))

# ---------- 5. Chart: talent vs. Coors fit ----------
fig, ax = plt.subplots(figsize=(8, 5.5))
for role, color in [("SP", "#333366"), ("RP", "#9aa9c4")]:
    d = out[out.role == role]
    ax.scatter(d.road_woba, d.projected_penalty, s=18, alpha=0.75, color=color,
               label="Starters" if role == "SP" else "Relievers")
best = out.sort_values("coors_projected_woba").head(10)
for _, row in best.iterrows():
    ax.annotate(row["name"], (row.road_woba, row.projected_penalty), fontsize=7,
                xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("wOBA allowed away from Coors (lower = better pitcher)")
ax.set_ylabel("Projected Coors penalty (lower = better fit)")
ax.set_title("Coors Fit Score: best pitchers AND best fits sit bottom-left (2025)")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig("chart_fit_score.png", dpi=200)
con.close()
print("\nSaved coors_fit_scores.csv and chart_fit_score.png")
