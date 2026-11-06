"""
Study 2b: Which effective pitch types do Rockies pitchers underuse?
Compares the Rockies' 2025 pitch mix to the league, scores each pitch type's
league-wide results, and checks Rockies usage at home vs. on the road.
Outputs: rockies_pitch_mix.csv, chart_rockies_mix.png
"""
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

NAMES = {"FF": "Four-seam", "SI": "Sinker", "FC": "Cutter", "SL": "Slider", "ST": "Sweeper",
         "CU": "Curveball", "KC": "Knuckle curve", "CH": "Changeup", "FS": "Splitter",
         "SV": "Slurve", "FO": "Forkball", "KN": "Knuckleball"}

con = sqlite3.connect("coors.db")
df = pd.read_sql("""
    SELECT pitcher, game_pk, home_team, away_team, pitch_type, description, woba_value, woba_denom
    FROM pitches WHERE pitch_type IS NOT NULL
""", con)

# ---------- 1. Assign each pitcher a team: the team present in the most of his games ----------
games = df.drop_duplicates(["pitcher", "game_pk"])[["pitcher", "game_pk", "home_team", "away_team"]]
team_counts = pd.concat([games[["pitcher", "home_team"]].rename(columns={"home_team": "team"}),
                         games[["pitcher", "away_team"]].rename(columns={"away_team": "team"})])
team = (team_counts.value_counts(["pitcher", "team"]).reset_index(name="n")
        .sort_values("n", ascending=False).drop_duplicates("pitcher").set_index("pitcher").team)
df["pitcher_team"] = df.pitcher.map(team)
df["is_rockies"] = df.pitcher_team == "COL"
print(f"Rockies pitchers identified: {df[df.is_rockies].pitcher.nunique()}")

# ---------- 2. League-wide results by pitch type ----------
swing = df.description.isin(["swinging_strike", "swinging_strike_blocked", "foul_tip", "foul"]) | \
        df.description.str.startswith("hit_into_play", na=False)
whiff = df.description.isin(["swinging_strike", "swinging_strike_blocked", "foul_tip"])
df["swing"], df["whiff"] = swing, whiff

league = df.groupby("pitch_type").agg(pitches=("pitcher", "size"), swings=("swing", "sum"), whiffs=("whiff", "sum"))
pa_end = df[df.woba_denom == 1].groupby("pitch_type").agg(woba_num=("woba_value", "sum"), woba_den=("woba_denom", "sum"))
league = league.join(pa_end)
league = league[league.pitches >= 3000]
league["whiff_rate"] = league.whiffs / league.swings
league["woba_allowed"] = league.woba_num / league.woba_den
league["league_usage"] = league.pitches / league.pitches.sum()
lg_avg_woba = league.woba_num.sum() / league.woba_den.sum()

# ---------- 3. Rockies usage: overall, home, road ----------
def usage(mask):
    s = df[mask].pitch_type.value_counts()
    return s / s.sum()

rk = df.is_rockies
league["rockies_usage"] = usage(rk)
league["rockies_home_usage"] = usage(rk & (df.home_team == "COL"))
league["rockies_road_usage"] = usage(rk & (df.away_team == "COL"))
league = league.fillna({"rockies_usage": 0, "rockies_home_usage": 0, "rockies_road_usage": 0})
league["usage_gap"] = league.rockies_usage - league.league_usage          # negative = Rockies underuse
league["home_minus_road"] = league.rockies_home_usage - league.rockies_road_usage
league["better_than_avg"] = league.woba_allowed < lg_avg_woba

out = league.reset_index()
out["pitch"] = out.pitch_type.map(NAMES).fillna(out.pitch_type)
cols = ["pitch", "league_usage", "rockies_usage", "usage_gap", "rockies_home_usage",
        "rockies_road_usage", "home_minus_road", "woba_allowed", "whiff_rate"]
out = out.sort_values("usage_gap")
print(f"\nLeague-average wOBA allowed (PA-ending pitches): {lg_avg_woba:.3f}")
print(out[cols].round(3).to_string(index=False))

flag = out[(out.usage_gap < -0.01) & out.better_than_avg]
print("\nUNDERUSED BY ROCKIES + BETTER-THAN-AVERAGE RESULTS LEAGUE-WIDE:")
print(flag[cols].round(3).to_string(index=False) if len(flag) else "None met the cutoffs.")
out[cols].round(4).to_csv("rockies_pitch_mix.csv", index=False)

# ---------- 4. Chart: usage gap vs. pitch quality ----------
fig, ax = plt.subplots(figsize=(8, 5.5))
colors = ["#333366" if b else "#b0b0b0" for b in out.better_than_avg]
ax.scatter(out.usage_gap * 100, out.woba_allowed, s=out.league_usage * 4000, c=colors, alpha=0.85, edgecolors="white")
for _, r in out.iterrows():
    ax.annotate(r.pitch, (r.usage_gap * 100, r.woba_allowed), fontsize=8, xytext=(7, 4), textcoords="offset points")
ax.axvline(0, color="black", linewidth=0.8)
ax.axhline(lg_avg_woba, color="gray", linestyle="--", linewidth=0.8)
ax.invert_yaxis()   # better pitches (lower wOBA) at the top
ax.set_xlabel("Rockies usage minus league usage (percentage points; left = Rockies underuse)")
ax.set_ylabel("wOBA allowed league-wide (higher on chart = better pitch)")
ax.set_title("Effective pitches the Rockies underuse sit top-left (2025)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("chart_rockies_mix.png", dpi=200)
con.close()
print("\nSaved rockies_pitch_mix.csv and chart_rockies_mix.png")
