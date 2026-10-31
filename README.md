# Kit local — Loja Horizonte

Persistência de Dados e Bancos Distribuídos • Arquiteturas de Soluções Escaláveis

**Versão 1.0 — 23/09/2026.** Este pacote implementa os recursos dos trabalhos T1, T2 e T3. Leia `VERSAO.md` para identificar se recebeu o pacote do aluno ou a referência do professor.

**Situação da validação:** código Python verificado; Java compilado e simuladores executados; resultados de distribuição comparados entre linguagens; SQL e YAML analisados sintaticamente. **Os contêineres e os testes de integração não foram executados no ambiente de autoria, que não dispõe de Docker.** Antes de distribuir à turma, executar o roteiro `docs/VALIDACAO.md` em uma máquina com Docker. Não apresentar este pacote como ensaiado em Windows, macOS ou Linux até realizar esses testes.

## O que está incluído

- T1: PostgreSQL com a massa exata dos dois pedidos; SQL, restrições, catálogo em Java/Python e cinco exercícios de interpretação.
- T2: primário e standby reais; pausa de replay; modos assíncrono, `on` e `remote_apply`; timeout e reconciliação; simuladores de faixa, módulo e consistent hashing.
- T3: Flyway em fases, cliente antigo e compatível, backfill com checkpoint, retorno controlado e contração protegida; Saga em três bancos lógicos; falhas após efeito remoto; backup físico, WAL e recuperação em outro volume.
- Roteiros de execução, testes de aceitação e modelos de relatório, ADR, contribuição e DR.

As versões Java e Python implementam catálogo, sharding, replicação, clientes da migração, backfill, Saga e repetição da compensação. Escolher **uma** linguagem para o trabalho. SQL e Docker são comuns. Não há API de pagamento, conta cloud ou serviço pago utilizado pelo código.

## Pré-requisitos do computador

1. Docker Engine com plugin Compose v2 em Linux, ou uma instalação de Docker compatível com contêineres Linux em Windows/macOS. No Windows, habilitar o backend WSL 2 da instalação escolhida. Verificar as condições de licença da distribuição de Docker adotada pela instituição; o kit não depende de funcionalidades comerciais.
2. Python 3.10 ou posterior no host, apenas para `lab.py`. Este script usa a biblioteca padrão: **não instalar psycopg ou Java no host**. Windows pode usar `py -3`; macOS/Linux geralmente usam `python3`.
3. Internet para obter imagens e dependências na primeira preparação. Depois de construir e baixar as imagens, os exercícios não precisam de APIs externas.
4. Em máquinas ARM (como Apple Silicon), o serviço Flyway usa `linux/amd64` e requer emulação x86-64 habilitada no Docker. Os outros componentes possuem imagens ARM64. Em Linux ARM sem essa emulação, o perfil de migração não iniciará.
5. Como ponto inicial de planejamento, reservar cerca de 4 GB de memória para Docker e 5 GB de disco livre. São estimativas, não requisitos medidos; verificar o consumo na validação. Ativar um perfil de cada vez ajuda a reduzir o consumo.

Extraia o ZIP inteiro em uma pasta de trabalho e abra o terminal **nessa pasta**. Não execute dentro da visualização do ZIP. Preserve a estrutura de diretórios.

## Primeiros comandos

Nos comandos abaixo, `python` significa o Python do seu computador. Substitua por `py -3` no Windows ou `python3` no macOS/Linux, se necessário. Os argumentos são os mesmos no PowerShell, Terminal do macOS e bash. Não é necessário executar os arquivos `.sh` diretamente no host.

```text
python lab.py doctor
python lab.py build
python lab.py up basic
python lab.py sql basic -f sql/sanity.sql
python lab.py status
```

`doctor` confirma disponibilidade de Docker/Compose e leitura da configuração. `build` prepara Python, Java e driver JDBC em uma imagem e baixa PostgreSQL/Flyway. Na primeira vez, pode levar vários minutos. `up` espera a prontidão do servidor; `sanity.sql` verifica as contagens e as restrições. As mensagens esperadas incluem `OK CHECK quantidade` e `OK FK cliente`.

Em seguida, siga **`docs/T1.md` → `docs/T2.md` → `docs/T3.md`**. No pacote do aluno há pontos a completar antes de certos comandos funcionarem. Uma mensagem `TODO_ALUNO` identifica exercício incompleto, não um defeito de instalação.

## Organização

| Caminho | Finalidade |
|---|---|
| `lab.py` | Interface de comandos multiplataforma e registro das execuções |
| `compose.yaml` | Serviços e volumes isolados por perfil |
| `sql/` | Schema, massa, consultas e verificações |
| `clientes/python/app.py` | Cliente e serviços em Python |
| `clientes/java/App.java` | Cliente e serviços em Java |
| `exercicios/respostas.py` ou `Respostas.java` | Pontos a completar na linguagem escolhida |
| `migrations/expand` e `migrations/contract` | Migrações liberadas em momentos distintos |
| `exercicios/pitr.json` | Nome do alvo de recuperação |
| `evidencias/execucoes/` | Logs reais gerados pelos comandos e dados de medição |
| `evidencias/referencia/` | Exemplos identificados; não são execuções do grupo |
| `docs/` | Roteiros, preparação docente e solução de problemas |
| `modelos/` | Estruturas para relatório, ADR, DR e contribuições |
| `tests/` | Testes unitários e de integração |

## Perfis e isolamento

| Perfil | Serviços | Dados |
|---|---|---|
| basic | basic | Massa T1 |
| replica | primary, standby | Réplica T2; não há promoção automática |
| migration | migration | Cópia de clientes T3 e registros de migração |
| saga | saga | Bancos lógicos pedidos, estoque e pagamentos |
| pitr | origin, destination e auxiliares | Origem, backup, WAL e destino separados |

Os três bancos da Saga estão na **mesma instância local**, com transações e conexões independentes. Isso permite estudar fronteiras transacionais; não representa três máquinas nem resistência à perda de uma máquina. Os perfis de migração e PITR usam cópias separadas para preservar T1 e T2.

O Compose não publica portas do PostgreSQL no host. Os clientes se conectam pelos nomes internos. A senha `horizonte_local` e a senha de réplica `replica_local` são exclusivamente didáticas. Não usar este ambiente como serviço de produção.

As duas edições usam o mesmo nome de projeto Docker (`horizonte-lab`). Execute somente uma edição por vez na mesma instalação de Docker. Ao trocar da referência para o pacote do aluno, preserve os logs e reinicie os perfis que serão reutilizados; uma migração aplicada pela referência não deve ser reaproveitada como execução do aluno.

## Parar e reiniciar

```text
python lab.py stop
python lab.py up replica
```

Parar preserva os dados. `up` não recarrega o schema em volumes existentes.

Para refazer **um perfil**, primeiro exporte seus logs e então execute, por exemplo:

```text
python lab.py reset replica --confirmar APAGAR-LAB
python lab.py up replica
```

A opção de confirmação evita apagar acidentalmente o ensaio. O comando remove somente contêineres e volumes conhecidos daquele perfil, verifica o rótulo do projeto e preserva os arquivos de evidência. `reset pitr` remove também os backups/WAL locais desse ensaio; só fazer depois de terminar e guardar os resultados. **Não usar `docker system prune` para reiniciar o laboratório.**

## Evidências e versão

Cada chamada a `lab.py` cria um log com comando, saída e código de retorno em `evidencias/execucoes`. Os logs de falhas são preservados. O diretório é ignorado por Git por padrão: selecionar conscientemente os arquivos pedidos no enunciado, ou anexá-los à entrega. Não entregar volumes de banco.

Registrar imagem/digest, versões, linguagem e commit. `status` mostra os contêineres e o digest do PostgreSQL. As quatro imagens externas estão fixadas por tag e digest de manifesto consultado no registro oficial; registrar também o ambiente efetivamente usado na validação. A primeira construção baixa pacotes de sistema e dependências de suas fontes. O pacote não contém imagens Docker ou instaladores offline.

Prazo e peso permanecem os do Plano: T1 D+4 (25%), T2 D+9 (35%), T3 D+14 (40%); grupos de 3–4; 3+4+5 horas. O kit reduz montagem de infraestrutura, mas o tempo real ainda deve ser medido com uma máquina representativa. Construção de imagens e problemas de instalação devem ser tratados no suporte previsto.
