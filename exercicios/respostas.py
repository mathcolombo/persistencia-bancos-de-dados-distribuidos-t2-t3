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
    return {'PENDENTE':'reservar','RESERVADO':'pagar','PAGAMENTO_CONFIRMADO':'confirmar',
            'COMPENSACAO_PENDENTE':'liberar','CONFIRMADO':'fim','CANCELADO':'fim'}[estado]

def apos_pagamento(resultado):
    return {'aprovado':'PAGAMENTO_CONFIRMADO','rejeitado':'COMPENSACAO_PENDENTE'}[resultado]

def liberar_sql():
    return "UPDATE reserva SET estado='LIBERADA' WHERE op=%s AND estado='ATIVA' RETURNING op"

