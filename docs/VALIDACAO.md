# Validação e liberação para a turma

## O que foi verificado na autoria

Data: 23/09/2026. Não havia Docker Engine/Compose disponível neste ambiente.

| Verificação | Resultado | Limite |
|---|---|---|
| Compilação sintática dos módulos Python | Passou | Não abre conexões reais |
| Seis testes unitários de hash, anel, movimentação e decisões da Saga | Passaram | Não validam persistência nem falhas reais |
| Java compilado pelo Eclipse ECJ 3.38, alvo Java 17 | Passou | O kit usa JDK 21; compilação na imagem ainda pendente |
| Simuladores Java e Python executados | Passaram | Simulação em memória |
| Comparação dos quatro CSVs, mil chaves cada | Idênticos entre linguagens | Não é benchmark ou cluster real |
| Dez arquivos SQL analisados com parser PostgreSQL | Passaram | Não executa DDL, PL/pgSQL ou Flyway |
| Scripts shell analisados com bash -n | Passaram | Não testa permissões de volumes |
| Compose validado contra schema da especificação | Passou | Não cria rede/serviços |
| Quatro manifestos de imagem consultados | Encontrados; digests fixados | Não foram baixadas/executadas as imagens |
| Testes Docker de T1, réplica, migração, Saga e PITR | **Não executados** | Obrigatórios antes da liberação |
| Ensaios Windows/macOS/Linux e tempos de alunos | **Não executados** | Medir em máquina representativa |

Os CSVs produzidos pelos simuladores estão no pacote do professor, identificados como execução de simulação. Não há logs fictícios de PostgreSQL, Flyway ou PITR.

## Roteiro de aceite local do professor ou responsável pelo laboratório

Use **a versão de referência**, em pasta separada da versão dos alunos. Registre sistema, CPU/arquitetura, memória disponibilizada ao Docker e tempo real. Este procedimento instala apenas as dependências previstas, sem usar conta cloud.

```text
python lab.py doctor
python lab.py build
python lab.py test unit
python lab.py test t1 --linguagem python
python lab.py test t1 --linguagem java
python lab.py test saga --linguagem python
python lab.py test saga --linguagem java
```

Os testes da Saga geram IDs novos e podem ser repetidos. Para migração e réplica, os testes exigem massa nova:

```text
python lab.py test migration --linguagem python
python lab.py reset migration --confirmar APAGAR-LAB
python lab.py test migration --linguagem java
python lab.py test replica --linguagem python
python lab.py reset replica --confirmar APAGAR-LAB
python lab.py test replica --linguagem java
python lab.py test pitr
```

Não fazer reset antes de copiar os logs necessários. O teste PITR é comum às linguagens porque executa ferramentas PostgreSQL e a interface padrão do host; a parte Java/Python de T3 está nos clientes de migração/backfill e Saga.

Ensaio adicional de WAL ausente, após guardar o primeiro resultado:

```text
python lab.py reset pitr --confirmar APAGAR-LAB
python lab.py pitr backup
python lab.py pitr incidente
python lab.py test pitr-wal-ausente
python lab.py pitr restaurar
python lab.py pitr medir
```

O segundo ensaio contém falha e demora deliberadas: seu RTO não é comparável diretamente ao primeiro. O destino de falha não usa nem altera o arquivo de WAL original.

## Critérios para liberar

- Comandos terminam com PASS onde esperado; faixa inválida e falha injetada têm rejeição identificada.
- Consultas mostram os totais 260/195 e os catálogos corretos nas duas linguagens.
- Réplica confirma identidades, espera de remote_apply, retomada e reconciliação após timeout.
- Migração demonstra convivência, NULL, checkpoint, retorno e gate; coluna antiga some só no final.
- S1–S6 mantêm estoque 4 no sucesso ou 5 no cancelamento, sem duplicar cobrança/devolução.
- PITR preserva 1/2, exclui 3, mantém origem vazia e registra alvo e tempos.
- O ensaio de falta de WAL identifica o erro esperado e não produz falso PASS.
- O fluxo de saída após interrupção e o reset preservam os arquivos de evidência e os outros perfis.
- Um integrante consegue seguir README sem conhecer a montagem interna; tempos cabem nos blocos previstos com infraestrutura já preparada.

Se houver falha, registrar o comando, ambiente e saída e corrigir o kit **antes** de classificar como dificuldade do aluno. Este documento não certifica resultados que ainda não foram observados.

## Verificação da edição do aluno

O pacote do aluno não contém soluções do professor nem CSVs completos resolvidos. Ao instalar, a sanidade do banco deve funcionar. Os testes de código dos pontos a completar devem falhar de forma explícita até o aluno implementá-los. Após a implementação, executar os testes correspondentes. A avaliação ainda exige análise, matriz, ADRs, DR e contribuições; PASS técnico não atribui automaticamente nota integral.
