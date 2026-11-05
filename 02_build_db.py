"""
Step 2: Load the saved Statcast data into a SQLite database so the analysis can be done in SQL.
Creates coors.db with one table: pitches
"""
import sqlite3
import pandas as pd

df = pd.read_parquet("statcast_2025.parquet")

con = sqlite3.connect("coors.db")
df.to_sql("pitches", con, if_exists="replace", index=False)

# Indexes make the GROUP BY queries much faster on ~700k rows
con.execute("CREATE INDEX IF NOT EXISTS idx_pitcher ON pitches(pitcher)")
con.execute("CREATE INDEX IF NOT EXISTS idx_home ON pitches(home_team)")
con.commit()

count = con.execute("SELECT COUNT(*) FROM pitches").fetchone()[0]
print(f"coors.db created with {count:,} pitches")
con.close()
