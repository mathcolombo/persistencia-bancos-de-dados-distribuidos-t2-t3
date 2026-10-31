CREATE TABLE cliente(id integer PRIMARY KEY,nome text NOT NULL,contato_email text);
INSERT INTO cliente VALUES(18,'Bruno','bruno@exemplo.test'),(42,'Ana','ana@exemplo.test');
INSERT INTO cliente SELECT n,'Cliente '||n,CASE WHEN n%10=0 THEN NULL ELSE 'c'||n||'@exemplo.test' END FROM generate_series(1000,1197) n;
CREATE TABLE lab_gate(id integer PRIMARY KEY CHECK(id=1),phase text NOT NULL,window_count integer NOT NULL DEFAULT 0,returned boolean NOT NULL DEFAULT false);
INSERT INTO lab_gate VALUES(1,'old',0,false);
CREATE TABLE lab_ops(id bigserial PRIMARY KEY,versao text NOT NULL,instante timestamptz NOT NULL DEFAULT clock_timestamp(),duracao_ms numeric NOT NULL,sucesso boolean NOT NULL);
CREATE TABLE lab_checkpoint(id integer PRIMARY KEY CHECK(id=1),last_id integer NOT NULL DEFAULT 0);
INSERT INTO lab_checkpoint VALUES(1,0);
