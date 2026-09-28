-- 00-init.sql — PostgreSQL initialization
-- Enable extensions, set timezone, configure performance knobs.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- fuzzy search for book/title/author
CREATE EXTENSION IF NOT EXISTS "unaccent";     -- accent-insensitive search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID v4 (used by some tables)
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Timezone
SET TIME ZONE 'Asia/Shanghai';

-- Performance knobs for crawler workload (small server, can tune up later)
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '768MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET work_mem = '8MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET log_min_duration_statement = '500';
ALTER SYSTEM SET statement_timeout = '300000';   -- 5min for long migrations
ALTER SYSTEM SET idle_in_transaction_session_timeout = '60000';
