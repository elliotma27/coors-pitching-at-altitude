"""
Step 7: Does it hold up in 2026? Out-of-sample test of the 2025 findings.

Run from the 2026 folder (rockiesproject_2026), after its coors.db is built.
Reads the 2025 database from ../rockiesproject/coors.db.

Tests:
  A. Do pitchers labeled by their 2025 archetype show the same Coors pattern in 2026?
  B. Does the 2025 Coors Fit Score predict 2026 Coors results?
  C. Are the traits stable year to year (fly-ball rate, hard-hit rate)?
Outputs: validation_2026.csv, chart_validation_2026.png
"""
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DB_2025 = "../rockiesproject/coors.db"
DB_2026 = "coors.db"
SHRINK_K, MIN_ROAD_BIP = 50, 150

def load_pa(path):
    con = sqlite3.connect(path)
    pa = pd.read_sql("""SELECT pitcher, home_team, bb_type, launch_speed, launch_angle, woba_value
                        FROM pitches WHERE woba_denom = 1 AND woba_value IS NOT NULL""", con)
    con.close()
    pa["at_coors"] = pa.home_team == "COL"
    return pa

def traits(pa):
    bip = pa.dropna(subset=["bb_type"])
    t = bip.groupby("pitcher").agg(bip=("bb_type", "size"),
                                   fb_rate=("bb_type", lambda s: (s == "fly_ball").mean()),
                                   hard_hit_rate=("launch_speed", lambda s: (s.dropna() >= 95).mean()))
    t = t[t.bip >= 150].copy()
    t["fb_tier"] = pd.qcut(t.fb_rate.rank(method="first"), 3, labels=[1, 2, 3]).astype(int)
    t["hh_tier"] = pd.qcut(t.hard_hit_rate.rank(method="first"), 3, labels=[1, 2, 3]).astype(int)
    t["archetype"] = np.select(
        [(t.fb_tier == 1) & (t.hh_tier == 1), t.fb_tier == 3, t.hh_tier == 3],
        ["Contact manager (low FB + low hard-hit)", "Fly-ball heavy", "Allows hard contact"], "Middle")
    return t

def fit_score(pa):
    bip = pa.dropna(subset=["bb_type", "launch_speed", "launch_angle"]).copy()
    bip["ev_bin"] = (np.floor(bip.launch_speed / 10) * 10).clip(60, 110)
    bip["la_bin"] = (np.floor(bip.launch_angle / 10) * 10).clip(-30, 50)
    tbl = bip.groupby(["ev_bin", "la_bin", "at_coors"]).woba_value.agg(["mean", "size"]).unstack("at_coors")
    tbl.columns = ["other_mean", "coors_mean", "other_n", "coors_n"]
    tbl = tbl.fillna({"coors_n": 0})
    tbl["delta"] = ((tbl.coors_mean - tbl.other_mean) * tbl.coors_n / (tbl.coors_n + SHRINK_K)).fillna(0)
    bip = bip.merge(tbl[["delta"]], left_on=["ev_bin", "la_bin"], right_index=True, how="left")
    road_pa, road_bip = pa[~pa.at_coors], bip[~bip.at_coors]
    p = road_pa.groupby("pitcher").size().to_frame("road_pa")
    p["road_bip"] = road_bip.groupby("pitcher").size()
    p["delta_sum"] = road_bip.groupby("pitcher").delta.sum()
    p = p[p.road_bip >= MIN_ROAD_BIP]
    return (p.delta_sum / p.road_pa).rename("proj_penalty_2025")

def pooled_penalty(pa, groups, label):
    """Coors penalty for a grouping of pitchers, pooled across their PAs, with a 95% interval."""
    d = pa[pa.pitcher.isin(groups.index)].copy()
    d["group"] = d.pitcher.map(groups)
    rows = []
    for g, x in d.groupby("group"):
        c, o = x[x.at_coors].woba_value, x[~x.at_coors].woba_value
        if len(c) < 30:
            continue
        rows.append({label: g, "coors_pa_2026": len(c), "penalty_2026": c.mean() - o.mean(),
                     "ci95": 1.96 * np.sqrt(c.var() / len(c) + o.var() / len(o))})
    return pd.DataFrame(rows)

pa25, pa26 = load_pa(DB_2025), load_pa(DB_2026)
t25, t26 = traits(pa25), traits(pa26)

# ---------- A. 2025 archetypes -> 2026 Coors results ----------
A = pooled_penalty(pa26, t25.archetype, "archetype_2025").sort_values("penalty_2026")
print("TEST A: Coors penalty in 2026, grouping pitchers by their 2025 archetype")
print(A.round(3).to_string(index=False))

# ---------- B. 2025 Fit Score -> 2026 Coors results ----------
proj = fit_score(pa25)
tercile = pd.qcut(proj.rank(method="first"), 3, labels=["Best 2025 fit", "Middle 2025 fit", "Worst 2025 fit"])
B = pooled_penalty(pa26, tercile.astype(str), "fit_group_2025")
B["order"] = B.fit_group_2025.map({"Best 2025 fit": 0, "Middle 2025 fit": 1, "Worst 2025 fit": 2})
B = B.sort_values("order").drop(columns="order")
print("\nTEST B: Coors penalty in 2026, grouping pitchers by their 2025 Fit Score (thirds)")
print(B.round(3).to_string(index=False))

act26 = pa26.groupby(["pitcher", "at_coors"]).woba_value.agg(["mean", "size"]).unstack("at_coors")
act26.columns = ["road_woba", "coors_woba", "road_pa", "coors_pa"]
act26["actual_penalty_2026"] = act26.coors_woba - act26.road_woba
j = act26.join(proj, how="inner")
j20 = j[j.coors_pa >= 20]
r = j20[["proj_penalty_2025", "actual_penalty_2026"]].corr().iloc[0, 1] if len(j20) > 2 else float("nan")
print(f"Pitcher-level correlation, 2025 projection vs. 2026 actual (20+ Coors PA, n={len(j20)}): r = {r:.2f}")

# ---------- C. Trait stability ----------
both = t25[["fb_rate", "hard_hit_rate"]].join(t26[["fb_rate", "hard_hit_rate"]], lsuffix="_2025", rsuffix="_2026", how="inner")
r_fb = both[["fb_rate_2025", "fb_rate_2026"]].corr().iloc[0, 1]
r_hh = both[["hard_hit_rate_2025", "hard_hit_rate_2026"]].corr().iloc[0, 1]
print(f"\nTEST C: year-to-year stability (pitchers qualified both years, n={len(both)})")
print(f"  Fly-ball rate:  r = {r_fb:.2f}")
print(f"  Hard-hit rate:  r = {r_hh:.2f}")

pd.concat([A.assign(test="A"), B.assign(test="B")]).round(4).to_csv("validation_2026.csv", index=False)

# ---------- Chart ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
short = {"Contact manager (low FB + low hard-hit)": "Contact managers", "Allows hard contact": "Allows hard contact",
         "Middle": "Middle", "Fly-ball heavy": "Fly-ball heavy"}
axes[0].barh([short[a] for a in A.archetype_2025], A.penalty_2026, xerr=A.ci95, color="#333366", ecolor="#999999", capsize=4)
axes[0].set_title("2025 archetype -> 2026 Coors penalty")
axes[1].barh(B.fit_group_2025, B.penalty_2026, xerr=B.ci95, color="#5b7fa6", ecolor="#999999", capsize=4)
axes[1].invert_yaxis()
axes[1].set_title("2025 Fit Score -> 2026 Coors penalty")
for ax in axes:
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("wOBA at Coors minus elsewhere, 2026 (95% interval)")
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Does it hold up in 2026? Out-of-sample test of the 2025 findings")
plt.tight_layout(); plt.savefig("chart_validation_2026.png", dpi=200)
print("\nSaved validation_2026.csv and chart_validation_2026.png")
