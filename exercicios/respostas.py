"""Complete apenas os pontos da linguagem escolhida. Consulte docs/T1.md e T2/T3."""
from bisect import bisect_left

def catalogo_sql():
    # TODO_ALUNO T1 E4: placeholders %s, ordem categoria, minimo, maximo.
    raise NotImplementedError('TODO_ALUNO catalogo_sql')

def modulo(h, nodes):
    # TODO_ALUNO T2 E1: índice entre 0 e N-1.
    raise NotImplementedError('TODO_ALUNO modulo')

def sucessor(h, points):
    # TODO_ALUNO T2 E1: points ordenados (hash, no_fisico, indice_virtual).
    # Igualdade pertence ao ponto; após último ponto, voltar ao primeiro.
    raise NotImplementedError('TODO_ALUNO sucessor')

def movidas(before, after):
    # TODO_ALUNO T2 E1: comparar o destino físico da mesma chave.
    raise NotImplementedError('TODO_ALUNO movidas')

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
