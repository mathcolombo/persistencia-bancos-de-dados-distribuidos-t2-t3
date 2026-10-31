SET lock_timeout='5s';
-- Mesmo lock exclusivo usado pelo gate; cada operação do cliente usa lock compartilhado.
SELECT pg_advisory_xact_lock(8101);
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM lab_gate WHERE id=1 AND phase='final' AND window_count>=10 AND returned) THEN RAISE EXCEPTION 'Gate nao liberado'; END IF;
 IF EXISTS(SELECT 1 FROM cliente WHERE email IS DISTINCT FROM contato_email) THEN RAISE EXCEPTION 'Backfill divergente'; END IF;
END $$;
DROP TRIGGER cliente_email ON cliente;
DROP FUNCTION sync_email();
ALTER TABLE cliente DROP COLUMN contato_email;
UPDATE lab_gate SET phase='contracted' WHERE id=1;
