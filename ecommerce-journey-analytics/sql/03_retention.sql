-- Weekly visitor-ID retention with right-censoring and partial-week controls.

CREATE OR REPLACE TABLE visitor_weekly_activity AS
SELECT DISTINCT
    visitor_id,
    DATE_TRUNC('week', session_start_utc)::DATE AS activity_week
FROM session_facts;

CREATE OR REPLACE TABLE visitor_cohorts AS
SELECT
    visitor_id,
    MIN(activity_week) AS cohort_week
FROM visitor_weekly_activity
GROUP BY visitor_id;

CREATE OR REPLACE TABLE cohort_retention AS
WITH bounds AS (
    SELECT
        DATE_TRUNC('week', MIN(event_time_utc))::DATE AS min_week,
        DATE_TRUNC('week', MAX(event_time_utc))::DATE AS max_week
    FROM session_events
),
cohort_sizes AS (
    SELECT
        cohort_week,
        COUNT(*) AS cohort_visitors
    FROM visitor_cohorts
    CROSS JOIN bounds
    WHERE cohort_week > min_week
        AND cohort_week < max_week
    GROUP BY cohort_week
),
retained AS (
    SELECT
        cohorts.cohort_week,
        DATE_DIFF('week', cohorts.cohort_week, activity.activity_week)
            AS week_number,
        COUNT(DISTINCT cohorts.visitor_id) AS retained_visitors
    FROM visitor_cohorts AS cohorts
    JOIN visitor_weekly_activity AS activity USING (visitor_id)
    CROSS JOIN bounds
    WHERE cohorts.cohort_week > min_week
        AND activity.activity_week < max_week
        AND DATE_DIFF('week', cohorts.cohort_week, activity.activity_week)
            BETWEEN 0 AND 8
    GROUP BY
        cohorts.cohort_week,
        week_number
),
eligible_grid AS (
    SELECT
        cohort_sizes.cohort_week,
        week_number,
        cohort_sizes.cohort_visitors
    FROM cohort_sizes
    CROSS JOIN RANGE(0, 9) AS weeks(week_number)
    CROSS JOIN bounds
    WHERE cohort_sizes.cohort_week
        + week_number * INTERVAL 7 DAY < bounds.max_week
)
SELECT
    eligible_grid.cohort_week,
    eligible_grid.week_number,
    eligible_grid.cohort_visitors,
    COALESCE(retained.retained_visitors, 0) AS retained_visitors,
    100.0 * COALESCE(retained.retained_visitors, 0)
        / eligible_grid.cohort_visitors
        AS retention_rate_pct
FROM eligible_grid
LEFT JOIN retained
    ON eligible_grid.cohort_week = retained.cohort_week
    AND eligible_grid.week_number = retained.week_number
ORDER BY
    eligible_grid.cohort_week,
    eligible_grid.week_number;

CREATE OR REPLACE TABLE overall_retention_by_week AS
SELECT
    week_number,
    SUM(retained_visitors) AS retained_visitors,
    SUM(cohort_visitors) AS eligible_cohort_visitors,
    100.0 * SUM(retained_visitors) / SUM(cohort_visitors)
        AS weighted_retention_rate_pct
FROM cohort_retention
WHERE week_number BETWEEN 1 AND 8
GROUP BY week_number
ORDER BY week_number;

CREATE OR REPLACE TABLE activation_retention_w1 AS
WITH bounds AS (
    SELECT
        DATE_TRUNC('week', MIN(event_time_utc))::DATE AS min_week,
        DATE_TRUNC('week', MAX(event_time_utc))::DATE AS max_week
    FROM session_events
),
first_sessions AS (
    SELECT
        visitor_id,
        DATE_TRUNC('week', session_start_utc)::DATE AS cohort_week,
        CASE
            WHEN transaction_events > 0 THEN 'purchased'
            WHEN cart_events > 0 THEN 'cart_no_purchase'
            ELSE 'view_only'
        END AS first_session_stage
    FROM session_facts
    WHERE session_number = 1
),
eligible AS (
    SELECT first_sessions.*
    FROM first_sessions
    CROSS JOIN bounds
    WHERE cohort_week > min_week
        AND cohort_week + INTERVAL 7 DAY < max_week
),
aggregated AS (
    SELECT
        first_session_stage,
        COUNT(*) AS cohort_visitors,
        COUNT(*) FILTER (
            WHERE EXISTS (
                SELECT 1
                FROM visitor_weekly_activity AS activity
                WHERE activity.visitor_id = eligible.visitor_id
                    AND activity.activity_week
                        = eligible.cohort_week + INTERVAL 7 DAY
            )
        ) AS retained_w1
    FROM eligible
    GROUP BY first_session_stage
)
SELECT
    *,
    100.0 * retained_w1 / cohort_visitors AS w1_retention_rate_pct
FROM aggregated
ORDER BY cohort_visitors DESC;
