-- S12 (BLOCKING): every temporal column promoted to silver must be a real TIMESTAMP,
-- never a STRING that merely looks like a date.
ASSERT (
    SELECT COUNT(*) = 0
    FROM `PROJECT.silver.INFORMATION_SCHEMA.COLUMNS`
    WHERE (column_name LIKE '%kickoff_utc' OR column_name LIKE '%_date')
      AND data_type <> 'TIMESTAMP'
) AS 'S12: temporal column promoted without conversion to TIMESTAMP';
