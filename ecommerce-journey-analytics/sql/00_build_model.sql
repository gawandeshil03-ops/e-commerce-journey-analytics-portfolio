-- Build a visitor-event model and 30-minute sessions from the fixed CSV source.

CREATE OR REPLACE TABLE events_raw AS
SELECT
    "timestamp"::BIGINT AS event_time_ms,
    visitorid::BIGINT AS visitor_id,
    event::VARCHAR AS event_type,
    itemid::BIGINT AS item_id,
    transactionid::BIGINT AS transaction_id
FROM read_csv(
    '{{EVENTS_CSV}}',
    header = true,
    columns = {
        'timestamp': 'BIGINT',
        'visitorid': 'BIGINT',
        'event': 'VARCHAR',
        'itemid': 'BIGINT',
        'transactionid': 'BIGINT'
    },
    nullstr = ''
);

CREATE OR REPLACE TABLE events_clean AS
SELECT DISTINCT
    event_time_ms,
    visitor_id,
    event_type,
    item_id,
    transaction_id
FROM events_raw;

CREATE OR REPLACE TABLE session_events AS
WITH ordered_events AS (
    SELECT
        *,
        CASE event_type
            WHEN 'view' THEN 1
            WHEN 'addtocart' THEN 2
            WHEN 'transaction' THEN 3
        END AS event_type_order,
        LAG(event_time_ms) OVER (
            PARTITION BY visitor_id
            ORDER BY
                event_time_ms,
                event_type_order,
                item_id,
                COALESCE(transaction_id, -1)
        ) AS previous_event_time_ms
    FROM events_clean
),
session_flags AS (
    SELECT
        *,
        CASE
            WHEN previous_event_time_ms IS NULL
                OR event_time_ms - previous_event_time_ms > {{SESSION_GAP_MS}}
            THEN 1
            ELSE 0
        END AS is_new_session
    FROM ordered_events
)
SELECT
    event_time_ms,
    epoch_ms(event_time_ms) AS event_time_utc,
    visitor_id,
    event_type,
    item_id,
    transaction_id,
    SUM(is_new_session) OVER (
        PARTITION BY visitor_id
        ORDER BY
            event_time_ms,
            event_type_order,
            item_id,
            COALESCE(transaction_id, -1)
        ROWS UNBOUNDED PRECEDING
    )::INTEGER AS session_number
FROM session_flags;

CREATE OR REPLACE TABLE session_facts AS
SELECT
    visitor_id,
    session_number,
    MIN(event_time_ms) AS session_start_ms,
    MAX(event_time_ms) AS session_end_ms,
    MIN(event_time_utc) AS session_start_utc,
    MAX(event_time_utc) AS session_end_utc,
    (MAX(event_time_ms) - MIN(event_time_ms)) / 60000.0 AS duration_minutes,
    COUNT(*) AS event_count,
    COUNT(DISTINCT item_id) AS unique_items,
    COUNT(*) FILTER (WHERE event_type = 'view') AS view_events,
    COUNT(*) FILTER (WHERE event_type = 'addtocart') AS cart_events,
    COUNT(*) FILTER (WHERE event_type = 'transaction') AS transaction_events,
    MIN(event_time_ms) FILTER (WHERE event_type = 'view') AS first_view_ms,
    MIN(event_time_ms) FILTER (WHERE event_type = 'addtocart') AS first_cart_ms,
    MIN(event_time_ms) FILTER (WHERE event_type = 'transaction') AS first_transaction_ms
FROM session_events
GROUP BY
    visitor_id,
    session_number;

CREATE OR REPLACE TABLE visitor_summary AS
SELECT
    visitor_id,
    MIN(session_start_utc) AS first_seen_utc,
    MAX(session_end_utc) AS last_seen_utc,
    COUNT(*) AS session_count,
    SUM(event_count) AS event_count,
    SUM(transaction_events) AS transaction_item_events,
    MAX(transaction_events > 0)::BOOLEAN AS ever_purchased
FROM session_facts
GROUP BY visitor_id;
