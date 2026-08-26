-- betbot initial schema. Money is INTEGER cents; timestamps are UTC ISO-8601 TEXT.

CREATE TABLE sources (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL CHECK(platform IN ('telegram','whatsapp')),
  chat_id TEXT NOT NULL,
  sender_id TEXT,
  display_name TEXT NOT NULL,
  is_whitelisted INTEGER NOT NULL DEFAULT 0,
  stake_multiplier REAL NOT NULL DEFAULT 1.0,
  price_floor_pct REAL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  UNIQUE(platform, chat_id, sender_id)
);

CREATE TABLE raw_messages (
  id INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(id),
  platform TEXT NOT NULL,
  platform_message_id TEXT,
  is_edit INTEGER NOT NULL DEFAULT 0,
  received_at TEXT NOT NULL,
  message_text TEXT,
  image_path TEXT,
  content_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'received'
    CHECK(status IN ('received','parsed','not_a_tip','parse_failed','skipped_not_whitelisted','skipped_duplicate'))
);
CREATE INDEX ix_raw_hash ON raw_messages(content_hash, received_at);
CREATE INDEX ix_raw_status ON raw_messages(status);

CREATE TABLE tips (
  id INTEGER PRIMARY KEY,
  raw_message_id INTEGER NOT NULL REFERENCES raw_messages(id),
  source_id INTEGER NOT NULL REFERENCES sources(id),
  course TEXT NOT NULL,
  race_time_local TEXT NOT NULL,
  horse_name TEXT NOT NULL,
  side TEXT NOT NULL CHECK(side IN ('BACK','LAY')),
  tipped_price_cents INTEGER,
  rating TEXT,
  parse_confidence REAL NOT NULL,
  parse_model TEXT NOT NULL,
  parse_raw_json TEXT NOT NULL,
  market_id TEXT,
  selection_id INTEGER,
  event_name TEXT,
  market_start_time TEXT,
  match_score REAL,
  dedupe_key TEXT,
  status TEXT NOT NULL DEFAULT 'parsed'
    CHECK(status IN ('parsed','matched','match_failed','duplicate','rejected','bet_created')),
  created_at TEXT NOT NULL
);
CREATE INDEX ix_tips_dedupe ON tips(dedupe_key, created_at);
CREATE INDEX ix_tips_status ON tips(status);

CREATE TABLE bets (
  id INTEGER PRIMARY KEY,
  tip_id INTEGER NOT NULL REFERENCES tips(id),
  state TEXT NOT NULL
    CHECK(state IN ('APPROVED','PUBLISHED','CONSUMED','SETTLED_WON','SETTLED_LOST','SETTLED_VOID','ABORTED','EXPIRED')),
  side TEXT NOT NULL,
  stake_cents INTEGER NOT NULL,
  stake_pct REAL NOT NULL,
  bankroll_at_stake_cents INTEGER NOT NULL,
  tipped_price_cents INTEGER,
  validated_price_cents INTEGER NOT NULL,
  price_floor_cents INTEGER,
  matched_price_cents INTEGER,
  matched_stake_cents INTEGER,
  approved_at TEXT NOT NULL,
  published_at TEXT,
  consumed_at TEXT,
  expires_at TEXT NOT NULL,
  settled_at TEXT,
  result TEXT CHECK(result IN ('WON','LOST','VOID')),
  gross_pnl_cents INTEGER,
  commission_cents INTEGER,
  net_pnl_cents INTEGER,
  settlement_source TEXT
    CHECK(settlement_source IN ('bfbm_export','delayed_api_estimated','cleared_orders','manual')),
  abort_reason TEXT,
  needs_review INTEGER NOT NULL DEFAULT 0,
  executor TEXT NOT NULL DEFAULT 'bfbm_feed'
);
CREATE INDEX ix_bets_state ON bets(state);
CREATE INDEX ix_bets_tip ON bets(tip_id);

CREATE TABLE price_snapshots (
  id INTEGER PRIMARY KEY,
  tip_id INTEGER REFERENCES tips(id),
  market_id TEXT NOT NULL,
  selection_id INTEGER NOT NULL,
  taken_at TEXT NOT NULL,
  snapshot_type TEXT NOT NULL CHECK(snapshot_type IN ('at_validation','at_approval','pre_off','at_close')),
  back_price_cents INTEGER,
  back_size_cents INTEGER,
  lay_price_cents INTEGER,
  lay_size_cents INTEGER,
  total_matched_cents INTEGER
);
CREATE INDEX ix_snapshots_tip ON price_snapshots(tip_id);

CREATE TABLE bankroll_ledger (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  delta_cents INTEGER NOT NULL,
  balance_after_cents INTEGER NOT NULL,
  reason TEXT NOT NULL
    CHECK(reason IN ('opening','bet_settlement','settlement_correction','deposit','withdrawal','manual_adjustment')),
  bet_id INTEGER REFERENCES bets(id),
  note TEXT
);

CREATE TABLE guardrail_events (
  id INTEGER PRIMARY KEY,
  tip_id INTEGER,
  bet_id INTEGER,
  rule TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('pass','warn','abort')),
  detail TEXT,
  at TEXT NOT NULL
);
CREATE INDEX ix_guardrail_tip ON guardrail_events(tip_id);

CREATE TABLE feed_downloads (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  remote_ip TEXT,
  rows_served INTEGER NOT NULL,
  bet_ids TEXT
);

CREATE TABLE runtime_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE heartbeats (
  component TEXT PRIMARY KEY,
  last_seen_at TEXT NOT NULL,
  meta TEXT
);
