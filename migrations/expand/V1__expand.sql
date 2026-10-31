SET lock_timeout='5s';
ALTER TABLE cliente ADD COLUMN email text;
CREATE FUNCTION sync_email() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 -- contato_email é a autoridade enquanto houver v1; copia inclusive NULL na mesma transação.
 NEW.email := NEW.contato_email;
 RETURN NEW;
END $$;
CREATE TRIGGER cliente_email BEFORE INSERT OR UPDATE OF contato_email ON cliente FOR EACH ROW EXECUTE FUNCTION sync_email();
