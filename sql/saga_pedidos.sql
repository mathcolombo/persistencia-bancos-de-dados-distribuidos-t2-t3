CREATE TABLE saga(op text PRIMARY KEY,modo text NOT NULL CHECK(modo IN ('aprovado','rejeitado')),estado text NOT NULL DEFAULT 'PENDENTE');
CREATE TABLE evento(id bigserial PRIMARY KEY,op text NOT NULL,estado text NOT NULL,instante timestamptz NOT NULL DEFAULT clock_timestamp());
