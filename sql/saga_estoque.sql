-- Uma linha de estoque por cenário: massas isoladas, mesmo produto didático 10.
CREATE TABLE estoque(op text PRIMARY KEY,produto_id integer NOT NULL DEFAULT 10,disponivel integer NOT NULL DEFAULT 5 CHECK(disponivel>=0));
CREATE TABLE reserva(op text PRIMARY KEY REFERENCES estoque(op),estado text NOT NULL CHECK(estado IN ('ATIVA','LIBERADA')));
