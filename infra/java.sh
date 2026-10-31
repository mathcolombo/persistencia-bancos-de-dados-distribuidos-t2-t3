#!/bin/sh
set -eu
mkdir -p /tmp/horizonte-classes
javac -encoding UTF-8 -d /tmp/horizonte-classes /work/clientes/java/App.java /work/exercicios/Respostas.java
exec java -cp /tmp/horizonte-classes:/opt/drivers/postgresql.jar App "$@"
