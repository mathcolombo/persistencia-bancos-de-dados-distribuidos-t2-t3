SELECT 'cliente' AS tabela,count(*) FROM cliente UNION ALL SELECT 'produto',count(*) FROM produto UNION ALL SELECT 'estoque',count(*) FROM estoque UNION ALL SELECT 'pedido',count(*) FROM pedido UNION ALL SELECT 'item_pedido',count(*) FROM item_pedido;
DO $$ BEGIN
 IF (SELECT count(*) FROM cliente)<>2 OR (SELECT count(*) FROM produto)<>3 OR (SELECT count(*) FROM estoque)<>3 OR (SELECT count(*) FROM pedido)<>2 OR (SELECT count(*) FROM item_pedido)<>4 THEN RAISE EXCEPTION 'Contagens divergentes'; END IF;
 BEGIN
  INSERT INTO item_pedido VALUES(701,30,0,50);
  RAISE EXCEPTION 'CHECK nao rejeitou';
 EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK CHECK quantidade'; END;
 BEGIN
  INSERT INTO pedido VALUES(999,999,'CRIADO',1);
  RAISE EXCEPTION 'FK nao rejeitou';
 EXCEPTION WHEN foreign_key_violation THEN RAISE NOTICE 'OK FK cliente'; END;
END $$;
