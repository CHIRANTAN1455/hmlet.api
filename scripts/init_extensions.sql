-- Run automatically by the postgres container on first boot.
--
-- btree_gist lets a GiST exclusion constraint mix a scalar equality operator
-- (unit_id WITH =) with a range overlap operator (daterange WITH &&). Without
-- it, the constraint that makes double-booking impossible cannot be created.
CREATE EXTENSION IF NOT EXISTS btree_gist;
