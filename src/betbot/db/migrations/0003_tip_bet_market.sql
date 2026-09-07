-- Tips remember which Betfair market they bet (WIN or the separate PLACE
-- "To Be Placed" market) so later re-pricing matches the same market type.
ALTER TABLE tips ADD COLUMN bet_market TEXT NOT NULL DEFAULT 'WIN';
