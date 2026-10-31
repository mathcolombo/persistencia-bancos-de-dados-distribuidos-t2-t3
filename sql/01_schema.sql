BEGIN;
CREATE TABLE cliente(id integer PRIMARY KEY,nome text NOT NULL,contato_email text);
CREATE TABLE produto(id integer PRIMARY KEY,nome text NOT NULL,categoria text NOT NULL,preco_atual numeric(12,2) NOT NULL CHECK(preco_atual>=0),atributos jsonb NOT NULL);
CREATE TABLE estoque(produto_id integer PRIMARY KEY REFERENCES produto,disponivel integer NOT NULL CHECK(disponivel>=0));
CREATE TABLE pedido(id integer PRIMARY KEY,cliente_id integer NOT NULL REFERENCES cliente,estado text NOT NULL CHECK(estado IN ('CRIADO','PAGO','CANCELADO')),versao integer NOT NULL CHECK(versao>0));
CREATE TABLE item_pedido(pedido_id integer REFERENCES pedido,produto_id integer REFERENCES produto,quantidade integer NOT NULL CHECK(quantidade>0),preco_unitario numeric(12,2) NOT NULL CHECK(preco_unitario>=0),PRIMARY KEY(pedido_id,produto_id));
COMMIT;
