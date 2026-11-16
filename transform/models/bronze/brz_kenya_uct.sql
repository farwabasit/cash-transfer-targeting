-- Bronze: raw Kenya file as a view. Grain is NOT one row per household yet
-- (2,880 rows for 1,440 SURVEYIDs); fixed in silver.
select * from {{ source('raw', 'KENYA_UCT') }}
