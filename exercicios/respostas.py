"""Complete apenas os pontos da linguagem escolhida. Consulte docs/T1.md e T2/T3."""
from bisect import bisect_left

def catalogo_sql():
    # TODO_ALUNO T1 E4: placeholders %s, ordem categoria, minimo, maximo.
    raise NotImplementedError('TODO_ALUNO catalogo_sql')

def modulo(h, nodes):
    return nodes[h % len(nodes)]

def sucessor(h, points):
    i = bisect_left(points, (h,))
    return points[i % len(points)][1]

def movidas(before, after):
    return sum(1 for k in before if before[k] != after[k])

def proxima(estado):
    # TODO_ALUNO T3 E3: retorna reservar, pagar, confirmar, liberar ou fim.
    raise NotImplementedError('TODO_ALUNO proxima')

def apos_pagamento(resultado):
    # TODO_ALUNO T3 E3: resultado aprovado ou rejeitado conhecido.
    raise NotImplementedError('TODO_ALUNO apos_pagamento')

def liberar_sql():
    # TODO_ALUNO T3 E3: transição condicional de ATIVA para LIBERADA.
    # Retorne SQL com placeholder %s e RETURNING op.
    raise NotImplementedError('TODO_ALUNO liberar_sql')
