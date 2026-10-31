# T2 E4 Quorum e cenário de partição
Esta atividade é uma simulação em conjunto fixo de três réplicas A B C, sem réplicas substitutas. W é número de confirmações de escrita e R é número de respostas de leitura. Não associem esses números automaticamente à configuração de PostgreSQL usada nas páginas anteriores.
## Casos obrigatórios
Para cada par W e R igual a 1 e 1, 2 e 2, 3 e 1, listem os conjuntos mínimos possíveis e respondam se toda leitura intersecta toda escrita. Mostrem um exemplo de interseção ou um contraexemplo com grupos disjuntos.
Considerando uma réplica inacessível, indiquem se restam participantes suficientes para cada limiar. Essa conta não inclui eleição de líder ou outras condições de protocolo. Mostrem por que R mais W maior que N é uma propriedade de interseção, e não uma prova completa de linearizabilidade.
## Partição dois mais um
Estado inicial x igual a zero em A B C. A e B podem conversar; C não troca mensagens com eles, mas continua acessível a um cliente. Em uma política que exige dois participantes para a operação, analisem quais lados atingem o limiar. Não afirmem que C está fisicamente desligado.
Histórico obrigatório: uma escrita x igual a um é confirmada em A B. Depois dessa confirmação, outro cliente inicia leitura em C. Respondam o que acontece se C devolve zero, espera por comunicação ou responde erro sem executar a leitura solicitada. Expliquem a tensão entre linearizabilidade e disponibilidade no modelo CAP.
Não é possível deduzir o valor correto apenas do silêncio. Descrevam outro histórico indistinguível para C em que a escrita em A não ocorreu. Separem o C de CAP das restrições de integridade do ACID.
## T2 E5 Garantias de sessão e BASE
Histórico H1 contém leituras da mesma sessão e do mesmo objeto, em ordem: versão 8 e depois 7. Histórico H2 contém uma escrita própria confirmada de versão 9 e, como primeira leitura posterior da sessão, versão 8. Para cada histórico, nomeiem a garantia violada e indiquem quais operações são comparadas.
Proponham um mecanismo para evitar H1, como roteamento com controle de progresso ou token de versão. Expliquem a condição em que fixar a sessão em uma réplica deixa de ser suficiente. Para H2, descrevam como assegurar que a leitura reflita a própria escrita.
Por fim, expliquem BASE sem tratá-lo como protocolo único. Informem as condições necessárias à convergência eventual e por que eventual não define um prazo máximo nem uma sequência monotônica para cada sessão.
