import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'clientes/python'))
import app

class PureTests(unittest.TestCase):
 def test_hash_vector(self):
  self.assertEqual(app.h(''),0xe3b0c44298fc1c14)
 def test_range(self):
  from collections import Counter
  self.assertEqual(dict(Counter(app.distribution('ABC','faixa').values())),{'A':334,'B':333,'C':333})
 def test_add_only_moves_to_new_node(self):
  for mode in ['anel','virtual']:
   a,b=app.distribution('ABC',mode),app.distribution('ABCD',mode)
   self.assertEqual(len(a),1000)
   self.assertTrue(any(a[k]!=b[k] for k in a))
   self.assertTrue(all(b[k]=='D' for k in a if a[k]!=b[k]))
 def test_ring_boundary(self):
  p=[(20,'A',0),(50,'B',0),(80,'C',0)]
  self.assertEqual(app.answer.sucessor(50,p),'B')
  self.assertEqual(app.answer.sucessor(90,p),'A')
 def test_saga_paths(self):
  self.assertEqual(app.answer.proxima('COMPENSACAO_PENDENTE'),'liberar')
  self.assertEqual(app.answer.apos_pagamento('rejeitado'),'COMPENSACAO_PENDENTE')
  self.assertEqual(app.answer.proxima('CANCELADO'),'fim')
 def test_movement_counts_physical_node(self):
  self.assertEqual(app.answer.movidas({'k':'A'},{'k':'A'}),0)
  self.assertEqual(app.answer.movidas({'k':'A'},{'k':'B'}),1)

if __name__=='__main__':unittest.main()
