# Exercícios de interpretação de documentos chaves e grafos
Estes exercícios não exigem servidores adicionais. Leiam os dados e a consulta, confiram o resultado fornecido e expliquem sua semântica em duas a quatro frases. Não tratem as saídas fornecidas como execução realizada pelo grupo.
## T1 E5 Documento de catálogo
Considere a coleção produtos com três documentos: id 10 nome Mochila 25L atributos capacidade_l 25; id 20 nome Livro de SQL atributos paginas 240; id 30 nome Garrafa 1L atributos volume_l 1. Os demais campos não interferem na consulta.
```text
db.produtos.find(
  {"atributos.capacidade_l": {$gte: 20}},
  {_id: 0, id: 1, nome: 1}
).sort({id: 1})
```
Resultado fornecido: documento com id 10 e nome Mochila 25L. Expliquem o filtro, a projeção e por que o livro não é selecionado. Proponham um campo obrigatório e uma regra de validação para a ficha. Respondam quando prefeririam embutir dados e quando usariam uma referência ao lojista.
## T1 E6 Chave valor e expiração
```text
SET sessao:abc "cliente=42" EX 900
GET sessao:abc
```
Premissas: SET acontece em t igual a zero; não há nova escrita nem renovação. GET em t igual a 10 segundos retorna cliente=42. GET em t igual a 901 segundos retorna ausência de valor. Expliquem o significado de EX 900, calculem a duração em minutos e indiquem por que o único registro de um pedido não deveria usar essa política de expiração.
Distingam cache reconstruível e fonte oficial. Proponham como a aplicação identifica que a sessão expirou sem concluir que o cliente foi apagado do cadastro.
## T1 E7 Caminhos em um grafo
Dados: clientes A e B usam dispositivo X; cliente C usa dispositivo Y; A realizou pedido 701. Existe exatamente uma relação USA por par cliente dispositivo no conjunto.
```text
MATCH (a:Cliente {id:'A'})-[:USA]->(d:Dispositivo)
      <-[:USA]-(outro:Cliente)
WHERE outro.id <> a.id
RETURN DISTINCT outro.id ORDER BY outro.id
```
Resultado fornecido: B. Descrevam o caminho percorrido e a função de DISTINCT. Expliquem por que a consulta não retorna C e por que compartilhar dispositivo não constitui, por si só, prova de fraude. Indiquem um custo de ampliar indiscriminadamente a profundidade de navegação.

# Exercícios de interpretação temporal e vetorial
## T1 E8 Janela de tempo e agregação
A tabela medicao contém servico checkout e as observações em UTC de 22 setembro 2026: 10h00 com 90 ms; 10h01 com 110 ms; 10h02 com 210 ms; 10h03 com 120 ms. Não há outras linhas no intervalo.
```sql
SELECT AVG(latencia_ms) AS media_ms,
       MAX(latencia_ms) AS pico_ms
FROM medicao
WHERE servico = 'checkout'
  AND instante >= TIMESTAMPTZ '2026-09-22 10:00:00+00'
  AND instante < TIMESTAMPTZ '2026-09-22 10:04:00+00';
```
Resultados fornecidos: média 132.5 ms e pico 210 ms. Refaçam a conta, expliquem o limite superior exclusivo e indiquem uma informação que a média não preserva. Proponham retenção para detalhe recente e resumo histórico, explicitando que os prazos são decisões do grupo, não exigências universais.
## T1 E9 Similaridade por distância
Use os vetores didáticos q=(1;0), A=(0,9;0,1) e B=(0;1). O ponto e vírgula separa coordenadas; a vírgula representa decimal. Em uma tabela com coluna embedding do tipo vector, considere a ordenação por distância euclidiana do pgvector.
```sql
SELECT id, embedding <-> '[1,0]' AS distancia
FROM candidato
ORDER BY distancia, id
LIMIT 2;
```
Resultados fornecidos: A com aproximadamente 0.141421 e B com aproximadamente 1.414214. Mostrem o cálculo das duas distâncias, justifiquem a ordem e indiquem por que isso não representa probabilidade de o produto ser adequado. Os vetores foram fornecidos; não é necessário gerar embeddings ou instalar pgvector para esta interpretação.
Diferenciem uma busca exata da consulta apoiada por um índice aproximado. Citem uma regra de compra que deve continuar sendo verificada após recuperar candidatos.
## T1 E10 Matriz de seleção
Preencham uma linha para cada família: relacional, documentos, chave valor, grafos, séries temporais e vetorial. Colunas obrigatórias: estrutura, operação da Loja Horizonte, consulta dominante, garantia necessária, crescimento esperado, custo operacional e limitação. Crescimento pode ser descrito por padrão de carga, sem inventar benchmark.
## T1 E11 Duas decisões arquiteturais
Produzam ADR 01 para pedidos e reservas e ADR 02 para catálogo e busca. Cada registro contém contexto, decisão, requisito atendido, alternativa rejeitada, compromisso assumido e condição concreta de revisão. Cada ADR deve ter entre 150 e 220 palavras. Combinar capacidades em um mesmo produto é permitido quando justificado.
