# Solução de problemas

## Docker indisponível

Execute `docker version` e `docker compose version`. Inicie o serviço/aplicativo de Docker e confirme contêineres Linux. O kit não instala Docker. No Windows, `py -3 lab.py doctor`; em macOS/Linux, `python3 lab.py doctor`.

## Download ou build falha

Guardar o erro completo. Verificar acesso aos registros Docker, PyPI, Maven Central e repositórios Debian. Um proxy corporativo pode precisar de configuração na instalação de Docker. Não desabilitar verificação TLS para contornar o problema. As imagens e drivers não estão dentro do ZIP.

## TODO_ALUNO ou UnsupportedOperationException

O arquivo do exercício ainda não foi completado. Consulte o mapa em VERSAO.md. Isso é diferente de falha de rede ou banco. Não substituir o kit todo pelo pacote do professor para produzir evidências de autoria.

## Schema existe, mas alterações no seed não aparecem

Os scripts de inicialização só executam quando o volume está vazio. Após preservar evidências, reinicie **o perfil correto** com `reset`. Não apagar volumes de todos os trabalhos para recarregar T1.

## Réplica não fica pronta

`docker compose logs primary standby` mostra clonagem, autenticação e início do replay. Certifique-se de que primário e standby pertencem ao mesmo ensaio. Reiniciar apenas um volume e manter o outro antigo pode deixar históricos incompatíveis: use o reset do perfil replica. Nunca fazer failover neste trabalho.

## Commit permanece esperando

Abra outro terminal e retome replay no standby, conforme T2.md. Depois remova a exigência de standby síncrono e consulte o id no primário. Não repetir com novo id antes da reconciliação. Os ensaios usam no máximo quatro pequenas escritas, não uma carga contínua de WAL.

## Migração recusa contração

Verifique `SELECT * FROM lab_gate;` e a contagem de `email IS DISTINCT FROM contato_email`. O roteiro exige retorno de v1 testado, dez ciclos após a retirada definitiva e fase final liberada. Não remover o gate para fazer Flyway passar. Erro de checksum indica alteração de migração já aplicada; em laboratório, preservar o diagnóstico e reiniciar o perfil para novo ensaio.

## FALHA_INJETADA na Saga

É esperada apenas quando solicitado after-reserve/after-release. O processo terminou depois de um efeito persistido. Retome **o mesmo op** sem o argumento de falha. No teste automático, somente exit 17 com a mensagem apropriada é tratado como falha controlada.

## PITR não alcança o alvo

Consultar `docker compose logs destination` e o JSON de controle. Verificar nome do ponto e arquivamento. O comando não deve declarar sucesso apenas porque psql respondeu: precisa encontrar os ids, o marcador no log e recuperação concluída. Não promover manualmente. Um arquivo WAL necessário ausente impede alcançar o alvo. A origem e o arquivo de backup permanecem preservados para diagnóstico.

## Destino já contém recuperação

A cópia de preparação recusa sobrescrever dados existentes. Para ensaio novo, arquive evidências e use reset pitr. Isso também apaga o backup desse laboratório; não fazer antes de terminar sua análise.

## Permissão nos arquivos de evidência

O cliente é executado com UID/GID do usuário em Linux. Em Windows/macOS, o compartilhamento de pasta do Docker precisa permitir acesso à raiz extraída. Não mover somente o lab.py para outra pasta: os caminhos dependem da estrutura completa.

## Falha inesperada em teste

Enviar: sistema operacional, Docker/Compose, linguagem, comando, mensagem, log e hipótese. Identificar quais passos passaram e onde interrompeu. Não editar logs de erro para aparentar sucesso. A execução conjunta na máquina de outro integrante é permitida, com contribuições registradas.
