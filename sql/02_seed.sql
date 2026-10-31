BEGIN;
INSERT INTO cliente VALUES(42,'Ana','ana@exemplo.test'),(18,'Bruno','bruno@exemplo.test');
INSERT INTO produto VALUES(10,'Mochila 25L','TRILHA',100,'{"capacidade_l":25}'),(20,'Livro de SQL','LIVRO',60,'{"autor":"L Silva","paginas":240}'),(30,'Garrafa 1L','TRILHA',50,'{"volume_l":1}');
INSERT INTO estoque VALUES(10,5),(20,4),(30,8);
INSERT INTO pedido VALUES(701,42,'CRIADO',1),(702,18,'PAGO',1);
INSERT INTO item_pedido VALUES(701,10,2,100),(701,20,1,60),(702,10,1,95),(702,30,2,50);
COMMIT;
