-- Natural post-abandonment purchase behavior and experiment sizing inputs.

CREATE OR REPLACE TABLE first_cart_abandonment AS
WITH eligible_sessions AS (
    SELECT
        visitor_id,
        session_number,
        session_start_ms,
        session_end_ms,
        session_start_utc,
        session_end_utc,
        ROW_NUMBER() OVER (
            PARTITION BY visitor_id
            ORDER BY session_end_ms
        ) AS eligibility_number
    FROM session_facts
    WHERE cart_events > 0
        AND transaction_events = 0
)
SELECT
    visitor_id,
    session_number,
    session_start_ms,
    session_end_ms,
    session_start_utc,
    session_end_utc
FROM eligible_sessions
WHERE eligibility_number = 1;

CREATE OR REPLACE TABLE cart_recovery_events AS
SELECT
    abandonment.visitor_id,
    abandonment.session_number,
    abandonment.session_end_ms,
    abandonment.session_end_utc,
    MIN(events.event_time_ms) FILTER (
        WHERE events.event_type = 'transaction'
            AND events.event_time_ms > abandonment.session_end_ms
    ) AS next_transaction_ms,
    epoch_ms(
        MIN(events.event_time_ms) FILTER (
            WHERE events.event_type = 'transaction'
                AND events.event_time_ms > abandonment.session_end_ms
        )
    ) AS next_transaction_utc
FROM first_cart_abandonment AS abandonment
LEFT JOIN events_clean AS events USING (visitor_id)
GROUP BY
    abandonment.visitor_id,
    abandonment.session_number,
    abandonment.session_end_ms,
    abandonment.session_end_utc;

CREATE OR REPLACE TABLE cart_recovery_curve AS
WITH horizons(days) AS (
    VALUES (1), (7), (14), (30)
),
max_time AS (
    SELECT MAX(event_time_ms) AS max_event_time_ms
    FROM events_clean
),
aggregated AS (
    SELECT
        days,
        COUNT(*) FILTER (
            WHERE session_end_ms
                <= max_event_time_ms - days::BIGINT * 86400000::BIGINT
        ) AS eligible_visitors,
        COUNT(*) FILTER (
            WHERE session_end_ms
                <= max_event_time_ms - days::BIGINT * 86400000::BIGINT
                AND next_transaction_ms
                    <= session_end_ms + days::BIGINT * 86400000::BIGINT
        ) AS recovered_visitors
    FROM cart_recovery_events
    CROSS JOIN horizons
    CROSS JOIN max_time
    GROUP BY days
)
SELECT
    days,
    eligible_visitors,
    recovered_visitors,
    100.0 * recovered_visitors / eligible_visitors AS recovery_rate_pct
FROM aggregated
ORDER BY days;

CREATE OR REPLACE TABLE cart_recovery_weekly_eligibility AS
WITH bounds AS (
    SELECT
        DATE_TRUNC('week', MIN(event_time_utc))::DATE AS min_week,
        DATE_TRUNC('week', MAX(event_time_utc))::DATE AS max_week
    FROM session_events
)
SELECT
    DATE_TRUNC('week', session_end_utc)::DATE AS week_start,
    COUNT(*) AS eligible_visitors
FROM first_cart_abandonment
CROSS JOIN bounds
WHERE DATE_TRUNC('week', session_end_utc)::DATE > min_week
    AND DATE_TRUNC('week', session_end_utc)::DATE < max_week
GROUP BY week_start
ORDER BY week_start;
