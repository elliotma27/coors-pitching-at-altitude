"""
Step 1: Pull the 2025 MLB season of Statcast pitch data and save only the columns we need.

This takes a while (often 30-60+ minutes) because it downloads every pitch of the season
in small date chunks. Start it, then work on Step 2 while it runs.
"""
from pybaseball import statcast, cache
import pandas as pd

cache.enable()  # if the download gets interrupted, re-running picks up from cached chunks

# 2025 regular season (adjust if you want to trim to exact dates)
START = "2025-03-18"
END = "2025-09-28"

print(f"Pulling Statcast data {START} to {END}...")
df = statcast(start_dt=START, end_dt=END)

# Keep only what the project needs
cols = [
    "game_date", "game_pk", "game_type", "home_team", "away_team",
    "pitcher", "batter", "p_throws", "pitch_type", "release_speed",
    "events", "description", "bb_type",
    "launch_speed", "launch_angle", "launch_speed_angle",
    "woba_value", "woba_denom", "estimated_woba_using_speedangle",
]
df = df[cols]

# Regular season games only ("R"); drops spring training and postseason if any slipped in
df = df[df["game_type"] == "R"]

print(f"Rows: {len(df):,}")
print(f"Pitches at Coors (home_team == 'COL'): {(df['home_team'] == 'COL').sum():,}")

df.to_parquet("statcast_2025.parquet", index=False)
print("Saved statcast_2025.parquet")
