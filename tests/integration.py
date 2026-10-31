"""Testes de aceitação reais. Exigem Docker; não apagam perfis automaticamente."""
import sys,time,json
from concurrent.futures import ThreadPoolExecutor

def execute(suite,lang,L):
 def client(*a,check=True):return L.tool(lang,*a,check=check)
 def eq(actual,expected):
  if actual!=expected:raise AssertionError(f'Esperado {expected!r}, obtido {actual!r}')
 if suite=='all':
  for name in ['unit','t1','saga','migration','replica','pitr']:execute(name,lang,L)
  return
 if suite=='unit':
  L.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_unit.py','-v']);return
 if suite=='t1':
  L.up('basic');L.file_sql('basic','sql/sanity.sql')
  L.file_sql('basic','sql/03_consultas.sql')
  eq(L.sql('basic',"SELECT string_agg(id::text,',' ORDER BY id) FROM produto WHERE categoria='TRILHA' AND preco_atual BETWEEN 80 AND 120",quiet=True),'10')
  eq(L.sql('basic','SELECT sum(quantidade*preco_unitario) FROM item_pedido WHERE pedido_id=702',quiet=True),'195.00')
  for lo,hi,expected in [('80','120','[10,'),('40','60','[30,'),('500','600','[]')]:
   result=client('catalogo','TRILHA',lo,hi)
   if expected not in result.stdout:raise AssertionError('Cliente não retornou a saída esperada: '+expected)
  if client('catalogo','TRILHA','120','80',check=False).returncode==0:raise AssertionError('Faixa inválida foi aceita')
 elif suite=='saga':
  L.up('saga');prefix=lang+'_'+str(time.time_ns())
  def verify(op,success):
   client('snapshot',op)
   eq(L.sql('saga','SELECT estado FROM saga WHERE op='+L.lit(op),'pedidos',quiet=True),'CONFIRMADO' if success else 'CANCELADO')
   eq(L.sql('saga','SELECT disponivel FROM estoque WHERE op='+L.lit(op),'estoque',quiet=True),'4' if success else '5')
   eq(L.sql('saga','SELECT estado FROM reserva WHERE op='+L.lit(op),'estoque',quiet=True),'ATIVA' if success else 'LIBERADA')
   eq(L.sql('saga','SELECT cobrancas FROM pagamento WHERE op='+L.lit(op),'pagamentos',quiet=True),'1' if success else '0')
  a=prefix+'_S1';client('saga',a,'aprovado');verify(a,True)
  b=prefix+'_S2';client('saga',b,'rejeitado');verify(b,False)
  client('liberar',b);client('liberar',b);verify(b,False) # S3
  for name,fault in [('S4','after-reserve'),('S5','after-release')]:
   op=prefix+'_'+name
   p=client('saga',op,'rejeitado',fault,check=False)
   if p.returncode!=17 or 'FALHA_INJETADA' not in p.stdout:raise AssertionError('Falha injetada não observada corretamente')
   client('saga',op,'rejeitado');verify(op,False)
  client('saga',a,'aprovado');verify(a,True) # S6
 elif suite=='replica':
  L.up('replica')
  try:
   for mode in ['async','on','remote_apply','timeout']:client('replica',mode)
  finally:
   L.sql('standby','SELECT pg_wal_replay_resume()')
   L.sql('primary',"ALTER SYSTEM SET synchronous_standby_names=''")
   L.sql('primary','SELECT pg_reload_conf()')
 elif suite=='migration':
  L.up('migration');client('migration','v1','1');L.flyway('expand')
  L.sql('migration',"UPDATE cliente SET contato_email='ana.nova@exemplo.test' WHERE id=42; INSERT INTO cliente VALUES(55,'Nulo',NULL,NULL)")
  eq(L.sql('migration','SELECT count(*) FROM cliente WHERE id IN (42,55) AND email IS DISTINCT FROM contato_email',quiet=True),'0')
  with ThreadPoolExecutor(max_workers=2) as pool:
   v1=pool.submit(client,'migration','v1','12');v2=pool.submit(client,'migration','v2','12')
   client('backfill','2')
   L.sql('migration','SELECT * FROM lab_checkpoint')
   # Repetir um lote desde início: operação idempotente pela mesma autoridade.
   L.sql('migration','UPDATE lab_checkpoint SET last_id=0 WHERE id=1')
   client('backfill','100');v1.result();v2.result()
  eq(L.sql('migration','SELECT count(*) FROM cliente WHERE email IS DISTINCT FROM contato_email',quiet=True),'0')
  L.gate('retirar');L.gate('retorno');client('migration','v1','1');L.gate('janela');client('migration','v2','10');L.gate('liberar');L.flyway('contract');client('migration','final','2')
  eq(L.sql('migration',"SELECT count(*) FROM information_schema.columns WHERE table_name='cliente' AND column_name='contato_email'",quiet=True),'0')
  L.sql('migration','SELECT versao,count(*),max(duracao_ms) FROM lab_ops GROUP BY versao')
 elif suite=='pitr-wal-ausente':
  c=L.load('pitr-controle.json')
  if 'wal_final' not in c:raise ValueError('Execute pitr backup e pitr incidente antes deste teste')
  L.dc('stop','fault-destination')
  L.dc('run','--rm','--no-deps','fault-prep')
  L.dc('up','-d','fault-destination')
  try:
   end=time.monotonic()+45
   while time.monotonic()<end:
    logs=L.dc('logs','--no-color','fault-destination',quiet=True).stdout
    if 'recovery ended before configured recovery target was reached' in logs:break
    time.sleep(1)
   else:raise AssertionError('Não apareceu a falha esperada de WAL; analisar logs, sem classificar como PASS')
   print(logs)
  finally:L.dc('stop','fault-destination')
 elif suite=='pitr':
  for s in ['backup','incidente','restaurar','medir']:L.pitr(s)
 else:raise ValueError(suite)
 print('PASS suite='+suite+' linguagem='+lang)
