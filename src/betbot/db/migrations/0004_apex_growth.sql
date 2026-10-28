-- Apex growth layer: the official (Waller) log as the public source of truth,
-- Paddock subscribers in the members table, early Stripe events, page counts,
-- the Founder Wall.

-- The official log: what the site, the members area and the Sunday email show.
-- Money in pence (GBP); the bot's paper ledger (bets/bankroll_ledger) stays internal.
CREATE TABLE official_log (
  id            INTEGER PRIMARY KEY,
  race_date     TEXT NOT NULL,                 -- YYYY-MM-DD (UK date of the event)
  system        TEXT NOT NULL,                 -- 'Apex Anchor', 'Apex Football Gold'
  selection     TEXT NOT NULL,                 -- horse / match, or 'No bet' on a no-bet day
  venue         TEXT,                          -- course / competition
  event_time    TEXT,                          -- HH:MM UK
  market        TEXT,                          -- e.g. 'Place (3 places)'
  price_x100    INTEGER,                       -- decimal odds x100
  stake_pence   INTEGER,
  stake_pct     REAL,                          -- % of bank, checked against the published cap
  result        TEXT NOT NULL DEFAULT 'pending'
    CHECK (result IN ('pending','won','lost','void','no_bet')),
  position      TEXT,                          -- '2nd', '5th', 'NR'
  pnl_pence     INTEGER,                       -- signed, after commission
  reasoning     TEXT,
  free_pick     INTEGER NOT NULL DEFAULT 0,    -- sent to the Paddock as the weekly free pick
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX ix_official_log_date ON official_log(race_date DESC, id DESC);

-- Launch week, exactly as already published on apexcode.uk, stamped with when it was
-- published so the site's "last updated" line stays honest.
INSERT INTO official_log (race_date, system, selection, venue, event_time, market, result, position, pnl_pence, stake_pence, created_at, updated_at) VALUES
  ('2026-08-24','Apex Anchor','The Mean Fiddler',  NULL,       NULL,   'Place','won', '1st', 3112,   NULL, '2026-08-24T21:00:00Z', '2026-08-24T21:00:00Z'),
  ('2026-08-25','Apex Anchor','Luminous Warrior',  NULL,       NULL,   'Place','won', '2nd', 18300,  NULL, '2026-08-25T21:00:00Z', '2026-08-25T21:00:00Z'),
  ('2026-08-27','Apex Anchor','Kanzi',             NULL,       NULL,   'Place','lost','5th', -12235, NULL, '2026-08-27T21:00:00Z', '2026-08-27T21:00:00Z'),
  ('2026-08-28','Apex Anchor','Withtearsinmyeyes', NULL,       NULL,   'Place','won', '1st', 3865,   NULL, '2026-08-28T21:00:00Z', '2026-08-28T21:00:00Z'),
  ('2026-08-29','Apex Anchor','Majestic Flame',    NULL,       NULL,   'Place','lost','9th', -3000,  NULL, '2026-08-29T21:00:00Z', '2026-08-29T21:00:00Z'),
  ('2026-08-30','Apex Anchor','Galyx',             'Beverley', '13:40','Place','pending', NULL, NULL, 2910, '2026-08-30T21:00:00Z', '2026-08-30T21:00:00Z');

-- Paddock subscribers live in members (tier 'paddock'), with consent and unsubscribe.
ALTER TABLE members ADD COLUMN consent_at TEXT;
ALTER TABLE members ADD COLUMN unsubscribed_at TEXT;
ALTER TABLE members ADD COLUMN unsub_token TEXT;
ALTER TABLE members ADD COLUMN signup_source TEXT;
ALTER TABLE members ADD COLUMN welcomed_at TEXT;          -- paid-member welcome sent
ALTER TABLE members ADD COLUMN verdict_asked_at TEXT;     -- day-30 "honest verdict" sent
CREATE UNIQUE INDEX ix_members_unsub_token ON members(unsub_token);

-- Stripe doesn't guarantee event order: a subscription event can arrive before
-- checkout.session.completed has created the member. Park it here until then.
CREATE TABLE pending_subscription_events (
  stripe_customer_id     TEXT PRIMARY KEY,
  price_id               TEXT,
  status                 TEXT,
  stripe_subscription_id TEXT,
  received_at            TEXT NOT NULL
);

-- Cookieless page counts: no IPs, no ids — one row per day/path/source.
CREATE TABLE page_views (
  day          TEXT NOT NULL,
  path         TEXT NOT NULL,
  ref_domain   TEXT NOT NULL DEFAULT '',
  utm_source   TEXT NOT NULL DEFAULT '',
  utm_medium   TEXT NOT NULL DEFAULT '',
  utm_campaign TEXT NOT NULL DEFAULT '',
  views        INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, path, ref_domain, utm_source, utm_medium, utm_campaign)
);

-- Founder Wall: shown only with the founder's permission (approved=1).
CREATE TABLE founder_wall (
  id            INTEGER PRIMARY KEY,
  display_name  TEXT NOT NULL,
  joined_label  TEXT,
  line          TEXT,
  approved      INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL
);

-- Auto-Bet stays hidden from Pro until the bot passes its paper-trading review.
-- Flip it back on in /admin when it does.
UPDATE tier_features SET enabled = 0 WHERE tier = 'pro' AND feature_key = 'auto_bet';
