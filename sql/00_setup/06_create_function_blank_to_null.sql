-- B4: '', 'None', 'null', 'NaN' and 'nan' mean absence, not value.
-- Persistent UDF so every silver script can call it standalone.
CREATE OR REPLACE FUNCTION `PROJECT.silver.blank_to_null`(x STRING) AS (
    IF(TRIM(x) IN ('', 'None', 'null', 'NaN', 'nan'), NULL, TRIM(x))
);
