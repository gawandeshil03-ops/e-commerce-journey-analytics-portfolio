-- Profile the source and quantify risks that can change product metrics.

CREATE OR REPLACE TABLE data_quality_summary AS
WITH duplicate_groups AS (
    SELECT COUNT(*) AS duplicate_group_count
    FROM (
        SELECT
            event_time_ms,
            visitor_id,
            event_type,
            item_id,
            transaction_id
        FROM events_raw
        GROUP BY ALL
        HAVING COUNT(*) > 1
    )
)
SELECT
    (SELECT COUNT(*) FROM events_raw) AS raw_event_rows,
    (SELECT COUNT(*) FROM events_clean) AS clean_event_rows,
    (SELECT COUNT(*) FROM events_raw) - (SELECT COUNT(*) FROM events_clean)
        AS duplicate_rows_removed,
    duplicate_group_count,
    (
        SELECT COUNT(*)
        FROM events_raw
        WHERE event_time_ms IS NULL
            OR visitor_id IS NULL
            OR event_type IS NULL
            OR item_id IS NULL
    ) AS rows_with_missing_required_fields,
    (
        SELECT COUNT(*)
        FROM events_raw
        WHERE event_type NOT IN ('view', 'addtocart', 'transaction')
    ) AS invalid_event_type_rows,
    (
        SELECT COUNT(*)
        FROM events_raw
        WHERE event_type = 'transaction' AND transaction_id IS NULL
    ) AS transactions_without_id,
    (
        SELECT COUNT(*)
        FROM events_raw
        WHERE event_type <> 'transaction' AND transaction_id IS NOT NULL
    ) AS non_transactions_with_id,
    (SELECT COUNT(DISTINCT visitor_id) FROM events_clean) AS visitors,
    (SELECT COUNT(DISTINCT item_id) FROM events_clean) AS items,
    (
        SELECT COUNT(DISTINCT transaction_id)
        FROM events_clean
        WHERE event_type = 'transaction'
    ) AS transactions,
    (SELECT MIN(epoch_ms(event_time_ms)) FROM events_clean) AS min_event_time_utc,
    (SELECT MAX(epoch_ms(event_time_ms)) FROM events_clean) AS max_event_time_utc
FROM duplicate_groups;

CREATE OR REPLACE TABLE event_type_summary AS
SELECT
    event_type,
    COUNT(*) AS event_rows,
    COUNT(DISTINCT visitor_id) AS visitors,
    COUNT(DISTINCT item_id) AS items,
    COUNT(DISTINCT transaction_id) AS transactions
FROM events_clean
GROUP BY event_type
ORDER BY event_rows DESC;

CREATE OR REPLACE TABLE session_gap_sensitivity AS
WITH gaps(gap_minutes) AS (
    VALUES (15), (30), (60)
),
lagged AS (
    SELECT
        gaps.gap_minutes,
        events_clean.*,
        LAG(event_time_ms) OVER (
            PARTITION BY gaps.gap_minutes, visitor_id
            ORDER BY
                event_time_ms,
                event_type,
                item_id,
                COALESCE(transaction_id, -1)
        ) AS previous_event_time_ms
    FROM events_clean
    CROSS JOIN gaps
),
numbered AS (
    SELECT
        *,
        SUM(
            CASE
                WHEN previous_event_time_ms IS NULL
                    OR event_time_ms - previous_event_time_ms > gap_minutes * 60000
                THEN 1
                ELSE 0
            END
        ) OVER (
            PARTITION BY gap_minutes, visitor_id
            ORDER BY
                event_time_ms,
                event_type,
                item_id,
                COALESCE(transaction_id, -1)
            ROWS UNBOUNDED PRECEDING
        ) AS session_number
    FROM lagged
),
sessionized AS (
    SELECT
        gap_minutes,
        visitor_id,
        session_number,
        MAX(event_type = 'addtocart')::BOOLEAN AS has_cart,
        MAX(event_type = 'transaction')::BOOLEAN AS has_transaction
    FROM numbered
    GROUP BY
        gap_minutes,
        visitor_id,
        session_number
)
SELECT
    gap_minutes,
    COUNT(*) AS sessions,
    SUM(has_cart::INTEGER) AS cart_sessions,
    SUM(has_transaction::INTEGER) AS transaction_sessions,
    100.0 * SUM(has_cart::INTEGER) / COUNT(*) AS cart_session_rate_pct,
    100.0 * SUM(has_transaction::INTEGER) / COUNT(*)
        AS transaction_session_rate_pct
FROM sessionized
GROUP BY gap_minutes
ORDER BY gap_minutes;
