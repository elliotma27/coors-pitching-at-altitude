"""
Study 2: Which pitch types limit fly balls and hard contact, and which hold up at Coors?
Outputs: pitch_type_profile.csv, chart_pitch_types.png, chart_pitch_coors.png
"""
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

NAMES = {"FF": "Four-seam", "SI": "Sinker", "FC": "Cutter", "SL": "Slider", "ST": "Sweeper",
         "CU": "Curveball", "KC": "Knuckle curve", "CH": "Changeup", "FS": "Splitter",
         "SV": "Slurve", "FO": "Forkball", "KN": "Knuckleball"}

con = sqlite3.connect("coors.db")

# ---------- Part 1: league-wide profile by pitch type (all parks) ----------
profile_sql = """
WITH pitch_level AS (
    SELECT
        pitch_type,
        COUNT(*) AS pitches,
        SUM(description IN ('swinging_strike', 'swinging_strike_blocked', 'foul_tip')) AS whiffs,
        SUM(description IN ('swinging_strike', 'swinging_strike_blocked', 'foul_tip', 'foul')
            OR description LIKE 'hit_into_play%') AS swings
    FROM pitches
    WHERE pitch_type IS NOT NULL
    GROUP BY pitch_type
),
contact AS (
    SELECT
        pitch_type,
        COUNT(*)                                          AS bip,
        AVG(bb_type = 'ground_ball')                      AS gb_rate,
        AVG(bb_type = 'fly_ball')                         AS fb_rate,
        1.0 * SUM(launch_speed >= 95) / COUNT(launch_speed) AS hard_hit_rate,
        AVG(launch_speed_angle = 6)                       AS barrel_rate,
        AVG(woba_value)                                   AS woba_on_contact
    FROM pitches
    WHERE bb_type IS NOT NULL AND woba_denom = 1 AND pitch_type IS NOT NULL
    GROUP BY pitch_type
)
SELECT p.pitch_type, p.pitches,
       1.0 * p.whiffs / p.swings AS whiff_rate,
       c.bip, c.gb_rate, c.fb_rate, c.hard_hit_rate, c.barrel_rate, c.woba_on_contact
FROM pitch_level p
JOIN contact c ON c.pitch_type = p.pitch_type
WHERE p.pitches >= 3000          -- drop rare pitch types
ORDER BY c.fb_rate
"""
prof = pd.read_sql(profile_sql, con)
prof["pitch"] = prof.pitch_type.map(NAMES).fillna(prof.pitch_type)
prof["usage"] = prof.pitches / prof.pitches.sum()

# ---------- Part 2: Coors effect by pitch type (actual minus expected, vs. elsewhere) ----------
coors_sql = """
SELECT
    pitch_type,
    SUM(home_team = 'COL') AS coors_bip,
    AVG(CASE WHEN home_team = 'COL'  THEN woba_value - estimated_woba_using_speedangle END) AS coors_gap,
    AVG(CASE WHEN home_team <> 'COL' THEN woba_value - estimated_woba_using_speedangle END) AS other_gap
FROM pitches
WHERE bb_type IS NOT NULL AND woba_denom = 1
  AND estimated_woba_using_speedangle IS NOT NULL AND pitch_type IS NOT NULL
GROUP BY pitch_type
"""
cz = pd.read_sql(coors_sql, con)
cz["coors_extra"] = cz.coors_gap - cz.other_gap
prof = prof.merge(cz[["pitch_type", "coors_bip", "coors_extra"]], on="pitch_type", how="left")

show = prof[["pitch", "usage", "whiff_rate", "gb_rate", "fb_rate", "hard_hit_rate",
             "barrel_rate", "woba_on_contact", "coors_bip", "coors_extra"]]
print(show.round(3).to_string(index=False))
show.round(4).to_csv("pitch_type_profile.csv", index=False)

# ---------- Chart A: fly-ball rate vs. hard-hit rate by pitch type ----------
fig, ax = plt.subplots(figsize=(8, 5.5))
sc = ax.scatter(prof.fb_rate, prof.hard_hit_rate, s=prof.usage * 4000, c=prof.whiff_rate,
                cmap="Blues", edgecolors="#333366", alpha=0.9)
for _, r in prof.iterrows():
    ax.annotate(r.pitch, (r.fb_rate, r.hard_hit_rate), fontsize=8, xytext=(7, 5), textcoords="offset points")
cb = plt.colorbar(sc, ax=ax); cb.set_label("Whiff rate")
ax.set_xlabel("Fly-ball rate on contact")
ax.set_ylabel("Hard-hit rate (95+ mph)")
ax.set_title("Which pitches avoid fly balls and hard contact? (2025, bubble size = usage)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("chart_pitch_types.png", dpi=200); plt.close()

# ---------- Chart B: Coors effect by pitch type ----------
cb_df = prof[prof.coors_bip >= 150].sort_values("coors_extra")
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.barh(cb_df.pitch, cb_df.coors_extra, color="#333366")
for i, (v, n) in enumerate(zip(cb_df.coors_extra, cb_df.coors_bip)):
    ax.text(max(v, 0) + 0.002, i, f"{v:+.3f}  (n={int(n)})", va="center", fontsize=8)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Extra wOBA on contact at Coors beyond contact quality (vs. elsewhere)")
ax.set_title("Which pitch types get punished most at Coors? (2025)")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("chart_pitch_coors.png", dpi=200); plt.close()

con.close()
print("\nSaved pitch_type_profile.csv, chart_pitch_types.png, chart_pitch_coors.png")
