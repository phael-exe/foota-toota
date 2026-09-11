-- S15: the source mixes three position vocabularies (19 distinct values).
-- This lookup collapses them into four canonical codes. Built before player_match_stats,
-- which joins against it.
CREATE OR REPLACE TABLE `PROJECT.silver.position_map` AS
SELECT raw, canonical
FROM UNNEST([
    STRUCT('Goalkeeper' AS raw, 'GK' AS canonical),
    ('GK',                 'GK'),
    ('Defender',           'DEF'),
    ('DEF',                'DEF'),
    ('Centre-Back',        'DEF'),
    ('Left-Back',          'DEF'),
    ('Right-Back',         'DEF'),
    ('Midfielder',         'MID'),
    ('MID',                'MID'),
    ('Central Midfield',   'MID'),
    ('Defensive Midfield', 'MID'),
    ('Attacking Midfield', 'MID'),
    ('Attacker',           'FWD'),
    ('FWD',                'FWD'),
    ('Forward',            'FWD'),
    ('Centre-Forward',     'FWD'),
    ('Left Wing',          'FWD'),
    ('Right Winger',       'FWD'),
    ('Winger',             'FWD')
]);
