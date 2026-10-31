CREATE TABLE pagamento(op text PRIMARY KEY,resultado text NOT NULL CHECK(resultado IN ('aprovado','rejeitado')),cobrancas integer NOT NULL CHECK(cobrancas IN (0,1)));
