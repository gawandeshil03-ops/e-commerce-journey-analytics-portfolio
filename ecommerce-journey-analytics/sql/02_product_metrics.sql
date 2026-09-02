-- Product KPIs, the observed funnel, weekly trends, and sensitivity cuts.

CREATE OR REPLACE TABLE funnel_summary AS
SELECT
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE view_events > 0) AS view_sessions,
    COUNT(*) FILTER (
        WHERE view_events > 0
            AND cart_events > 0
            AND first_cart_ms >= first_view_ms
    ) AS ordered_view_to_cart_sessions,
    COUNT(*) FILTER (
        WHERE view_events > 0
            AND cart_events > 0
            AND transaction_events > 0
            AND first_cart_ms >= first_view_ms
            AND first_transaction_ms >= first_cart_ms
    ) AS ordered_view_to_cart_to_transaction_sessions,
    COUNT(*) FILTER (WHERE cart_events > 0) AS cart_sessions,
    COUNT(*) FILTER (
        WHERE cart_events > 0 AND transaction_events > 0
    ) AS cart_with_transaction_sessions,
    COUNT(*) FILTER (
        WHERE cart_events > 0 AND transaction_events = 0
    ) AS cart_without_transaction_sessions,
    COUNT(*) FILTER (WHERE transaction_events > 0) AS transaction_sessions,
    100.0 * ordered_view_to_cart_sessions / view_sessions
        AS ordered_view_to_cart_rate_pct,
    100.0 * ordered_view_to_cart_to_transaction_sessions
        / NULLIF(ordered_view_to_cart_sessions, 0)
        AS ordered_cart_to_transaction_rate_pct,
    100.0 * ordered_view_to_cart_to_transaction_sessions / view_sessions
        AS ordered_view_to_transaction_rate_pct,
    100.0 * cart_with_transaction_sessions / NULLIF(cart_sessions, 0)
        AS same_session_cart_to_transaction_rate_pct,
    100.0 * transaction_sessions / total_sessions
        AS transaction_session_rate_pct
FROM session_facts;

CREATE OR REPLACE TABLE visitor_status_metrics AS
SELECT
    CASE
        WHEN session_number = 1 THEN 'new'
        ELSE 'returning'
    END AS visitor_status,
    COUNT(*) AS sessions,
    COUNT(*) FILTER (WHERE cart_events > 0) AS cart_sessions,
    COUNT(*) FILTER (WHERE transaction_events > 0) AS transaction_sessions,
    100.0 * cart_sessions / sessions AS cart_session_rate_pct,
    100.0 * transaction_sessions / sessions AS transaction_session_rate_pct
FROM session_facts
GROUP BY visitor_status
ORDER BY visitor_status;

CREATE OR REPLACE TABLE weekly_metrics AS
WITH bounds AS (
    SELECT
        DATE_TRUNC('week', MIN(event_time_utc))::DATE AS min_week,
        DATE_TRUNC('week', MAX(event_time_utc))::DATE AS max_week
    FROM session_events
)
SELECT
    DATE_TRUNC('week', session_start_utc)::DATE AS week_start,
    COUNT(*) AS sessions,
    COUNT(*) FILTER (WHERE cart_events > 0) AS cart_sessions,
    COUNT(*) FILTER (WHERE transaction_events > 0) AS transaction_sessions,
    100.0 * cart_sessions / sessions AS cart_session_rate_pct,
    100.0 * transaction_sessions / sessions AS transaction_session_rate_pct
FROM session_facts
CROSS JOIN bounds
WHERE DATE_TRUNC('week', session_start_utc)::DATE > min_week
    AND DATE_TRUNC('week', session_start_utc)::DATE < max_week
GROUP BY week_start
ORDER BY week_start;

CREATE OR REPLACE TABLE visitor_concentration AS
WITH cutoff AS (
    SELECT QUANTILE_DISC(session_count, 0.999) AS p999_session_count
    FROM visitor_summary
),
labeled AS (
    SELECT
        session_facts.*,
        visitor_summary.session_count,
        cutoff.p999_session_count,
        CASE
            WHEN visitor_summary.session_count > cutoff.p999_session_count
                THEN 'top_0_1_percent'
            ELSE 'remaining_visitors'
        END AS visitor_activity_segment
    FROM session_facts
    JOIN visitor_summary USING (visitor_id)
    CROSS JOIN cutoff
),
aggregated AS (
    SELECT
        visitor_activity_segment,
        MAX(p999_session_count) AS p999_session_count,
        COUNT(DISTINCT visitor_id) AS visitors,
        COUNT(*) AS sessions,
        COUNT(*) FILTER (WHERE transaction_events > 0) AS transaction_sessions
    FROM labeled
    GROUP BY visitor_activity_segment
)
SELECT
    *,
    100.0 * sessions / SUM(sessions) OVER () AS session_share_pct,
    100.0 * transaction_sessions / SUM(transaction_sessions) OVER ()
        AS transaction_session_share_pct
FROM aggregated
ORDER BY visitor_activity_segment;

CREATE OR REPLACE TABLE visitor_status_sensitivity AS
WITH cutoff AS (
    SELECT QUANTILE_DISC(session_count, 0.999) AS p999_session_count
    FROM visitor_summary
),
scopes AS (
    SELECT
        'all_visitors' AS analysis_scope,
        session_facts.*
    FROM session_facts

    UNION ALL

    SELECT
        'excluding_top_0_1_percent' AS analysis_scope,
        session_facts.*
    FROM session_facts
    JOIN visitor_summary USING (visitor_id)
    CROSS JOIN cutoff
    WHERE visitor_summary.session_count <= cutoff.p999_session_count
)
SELECT
    analysis_scope,
    CASE
        WHEN session_number = 1 THEN 'new'
        ELSE 'returning'
    END AS visitor_status,
    COUNT(*) AS sessions,
    COUNT(*) FILTER (WHERE transaction_events > 0) AS transaction_sessions,
    100.0 * transaction_sessions / sessions AS transaction_session_rate_pct
FROM scopes
GROUP BY
    analysis_scope,
    visitor_status
ORDER BY
    analysis_scope,
    visitor_status;

CREATE OR REPLACE TABLE product_kpi_summary AS
WITH one_session_visitors AS (
    SELECT
        COUNT(*) AS visitors,
        COUNT(*) FILTER (WHERE session_count = 1) AS one_session_visitors
    FROM visitor_summary
)
SELECT
    funnel_summary.*,
    (SELECT COUNT(*) FROM events_clean) AS clean_event_rows,
    (SELECT COUNT(DISTINCT visitor_id) FROM events_clean) AS visitors,
    100.0 * one_session_visitors / one_session_visitors.visitors
        AS one_session_visitor_share_pct
FROM funnel_summary
CROSS JOIN one_session_visitors;
