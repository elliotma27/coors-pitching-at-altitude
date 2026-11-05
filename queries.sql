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
