-- Phase 5: message metadata for tutor orchestrator

ALTER TABLE messages ADD COLUMN model_name TEXT;
ALTER TABLE messages ADD COLUMN prompt_version TEXT;
ALTER TABLE messages ADD COLUMN verification_status TEXT;
