-- Phase 7: richer attempt evidence for BKT

ALTER TABLE attempts ADD COLUMN hints_used INTEGER DEFAULT 0;
ALTER TABLE attempts ADD COLUMN max_hint_level INTEGER DEFAULT 0;
ALTER TABLE attempts ADD COLUMN response_time_ms INTEGER;
ALTER TABLE attempts ADD COLUMN solution_revealed INTEGER DEFAULT 0;
ALTER TABLE attempts ADD COLUMN concept_ids TEXT;
ALTER TABLE attempts ADD COLUMN misconception_type TEXT;
