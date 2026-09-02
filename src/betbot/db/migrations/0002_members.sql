-- Apex membership layer: tiers, switchable features, members, auth, per-member feeds.

CREATE TABLE tiers (
  name TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  rank INTEGER NOT NULL DEFAULT 0
);
INSERT INTO tiers (name, display_name, rank) VALUES
  ('paddock',  'The Paddock',  0),
  ('founding', 'Founding 50', 15),
  ('member',   'Apex Member', 10),
  ('pro',      'Apex Pro',    20);

CREATE TABLE features (
  key TEXT PRIMARY KEY,
  description TEXT NOT NULL
);
INSERT INTO features (key, description) VALUES
  ('selections',   'Live selections feed (see tips as they are published)'),
  ('full_log',     'Full results log with reasoning'),
  ('bank_tracker', 'Bank tracker charts'),
  ('debrief',      'Monthly debrief videos'),
  ('qa',           'Member Q&A access'),
  ('auto_bet',     'Auto-Bet: personal feed URL for their own BF Bot Manager');

-- Tier defaults: flip these live from the admin panel; member overrides win.
CREATE TABLE tier_features (
  tier TEXT NOT NULL REFERENCES tiers(name),
  feature_key TEXT NOT NULL REFERENCES features(key),
  enabled INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (tier, feature_key)
);
INSERT INTO tier_features (tier, feature_key, enabled) VALUES
  ('member',   'selections', 1), ('member',   'full_log', 1),
  ('founding', 'selections', 1), ('founding', 'full_log', 1),
  ('pro', 'selections', 1), ('pro', 'full_log', 1), ('pro', 'bank_tracker', 1),
  ('pro', 'debrief', 1), ('pro', 'qa', 1), ('pro', 'auto_bet', 1);

CREATE TABLE members (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  name TEXT,
  tier TEXT NOT NULL REFERENCES tiers(name) DEFAULT 'paddock',
  billing_period TEXT NOT NULL DEFAULT 'free'
    CHECK (billing_period IN ('free','monthly','yearly','lifetime')),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','trialing','past_due','canceled','paused')),
  delivery_mode TEXT NOT NULL DEFAULT 'manual' CHECK (delivery_mode IN ('manual','auto')),
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  feed_token TEXT UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX ix_members_stripe_customer ON members(stripe_customer_id);

-- Per-member overrides: enabled=1 grants regardless of tier, 0 revokes; absent row = tier default.
CREATE TABLE member_features (
  member_id INTEGER NOT NULL REFERENCES members(id),
  feature_key TEXT NOT NULL REFERENCES features(key),
  enabled INTEGER NOT NULL,
  PRIMARY KEY (member_id, feature_key)
);

CREATE TABLE magic_links (
  token TEXT PRIMARY KEY,
  member_id INTEGER NOT NULL REFERENCES members(id),
  expires_at TEXT NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE sessions (
  token TEXT PRIMARY KEY,
  member_id INTEGER NOT NULL REFERENCES members(id),
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE member_feed_downloads (
  id INTEGER PRIMARY KEY,
  member_id INTEGER NOT NULL REFERENCES members(id),
  at TEXT NOT NULL,
  remote_ip TEXT,
  rows_served INTEGER NOT NULL
);
