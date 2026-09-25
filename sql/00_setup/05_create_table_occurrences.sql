-- Every QUARANTINE or WARNING raised by a validation rule lands here.
-- BLOCKING rules are ASSERTs instead: they stop the pipeline and write nothing.
CREATE TABLE IF NOT EXISTS `PROJECT.quality.occurrences` (
    rule        STRING    OPTIONS (description = 'Rule id, e.g. S7, S9, S14'),
    severity    STRING    OPTIONS (description = 'QUARANTINE or WARNING'),
    row_count   INT64     OPTIONS (description = 'Rows affected by the occurrence'),
    detail      STRING    OPTIONS (description = 'Human readable description'),
    detected_at TIMESTAMP OPTIONS (description = 'When the rule ran')
);
