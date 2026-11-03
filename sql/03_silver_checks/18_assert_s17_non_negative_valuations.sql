-- S17 (BLOCKING): player valuations and transfer fees must be non-negative.
ASSERT (
    (
        SELECT COUNT(*) = 0
        FROM `PROJECT.silver.player_valuations`
        WHERE market_value_eur < 0
    ) AND (
        SELECT COUNT(*) = 0
        FROM `PROJECT.silver.transfers`
        WHERE transfer_fee_eur < 0 OR market_value_at_transfer_eur < 0
    )
) AS 'S17: negative valuations or transfer fees detected in Silver';
