-- ============================================================
-- Q1: THE MECHANISM
-- Does Coors add damage on fly balls more than on ground balls?
--
-- xwOBA (estimated_woba_using_speedangle) only knows exit velocity
-- and launch angle, not altitude. So at Coors, actual wOBA minus
-- xwOBA ("park_gap") shows where the park itself adds damage.
-- ============================================================
SELECT
    CASE WHEN home_team = 'COL' THEN 'Coors' ELSE 'Elsewhere' END AS park,
    bb_type,
    COUNT(*)                                            AS batted_balls,
    ROUND(AVG(woba_value), 3)                           AS actual_woba,
    ROUND(AVG(estimated_woba_using_speedangle), 3)      AS expected_woba,
    ROUND(AVG(woba_value)
        - AVG(estimated_woba_using_speedangle), 3)      AS park_gap
FROM pitches
WHERE bb_type IS NOT NULL                              -- balls in play only
  AND estimated_woba_using_speedangle IS NOT NULL
  AND woba_denom = 1                                   -- counts toward wOBA
GROUP BY park, bb_type
ORDER BY bb_type, park;


-- ============================================================
-- Q2: LABEL EVERY QUALIFIED PITCHER BY ARCHETYPE
-- (Archetype-level pooling; a per-pitcher Coors cutoff left only 19 pitchers.)
-- ============================================================
DROP VIEW IF EXISTS pitcher_archetypes;
CREATE VIEW pitcher_archetypes AS
WITH traits AS (
    SELECT
        pitcher,
        COUNT(*)                                        AS bip,
        1.0 * SUM(bb_type = 'fly_ball') / COUNT(*)      AS fb_rate,
        1.0 * SUM(launch_speed >= 95)
            / COUNT(launch_speed)                       AS hard_hit_rate
    FROM pitches
    WHERE bb_type IS NOT NULL
      AND woba_denom = 1
    GROUP BY pitcher
    HAVING COUNT(*) >= 150
),
ranked AS (
    SELECT
        *,
        NTILE(3) OVER (ORDER BY fb_rate)       AS fb_tier,
        NTILE(3) OVER (ORDER BY hard_hit_rate) AS hh_tier
    FROM traits
)
SELECT
    pitcher, bip, fb_rate, hard_hit_rate,
    CASE
        WHEN fb_tier = 1 AND hh_tier = 1 THEN 'Contact manager (low FB + low hard-hit)'
        WHEN fb_tier = 3                 THEN 'Fly-ball heavy'
        WHEN hh_tier = 3                 THEN 'Allows hard contact'
        ELSE 'Middle'
    END AS archetype
FROM ranked;

-- Check: how many pitchers in each archetype?
SELECT archetype, COUNT(*) AS pitchers
FROM pitcher_archetypes
GROUP BY archetype;


-- ============================================================
-- Q3: COORS PENALTY BY ARCHETYPE (pooled plate appearances)
-- ============================================================
SELECT
    a.archetype,
    COUNT(DISTINCT CASE WHEN p.home_team = 'COL' THEN a.pitcher END)  AS pitchers_at_coors,
    SUM(CASE WHEN p.home_team = 'COL' THEN p.woba_denom END)          AS coors_pa,
    ROUND(1.0 * SUM(CASE WHEN p.home_team = 'COL'  THEN p.woba_value END)
              / SUM(CASE WHEN p.home_team = 'COL'  THEN p.woba_denom END), 3) AS coors_woba,
    ROUND(1.0 * SUM(CASE WHEN p.home_team <> 'COL' THEN p.woba_value END)
              / SUM(CASE WHEN p.home_team <> 'COL' THEN p.woba_denom END), 3) AS other_woba,
    ROUND(1.0 * SUM(CASE WHEN p.home_team = 'COL'  THEN p.woba_value END)
              / SUM(CASE WHEN p.home_team = 'COL'  THEN p.woba_denom END)
        - 1.0 * SUM(CASE WHEN p.home_team <> 'COL' THEN p.woba_value END)
              / SUM(CASE WHEN p.home_team <> 'COL' THEN p.woba_denom END), 3) AS coors_penalty
FROM pitches p
JOIN pitcher_archetypes a ON a.pitcher = p.pitcher
WHERE p.woba_denom = 1
GROUP BY a.archetype
ORDER BY coors_penalty;
