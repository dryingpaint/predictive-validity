-- pg_trgm served only trigram indexes on the legacy tables migration 92 dropped; nothing uses it.

BEGIN;
SET LOCAL lock_timeout = '3s';
DROP EXTENSION IF EXISTS pg_trgm;
COMMIT;
