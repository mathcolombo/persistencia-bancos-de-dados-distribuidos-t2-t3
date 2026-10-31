import os, sys, json, csv, time, hashlib, argparse
from pathlib import Path
from decimal import Decimal
from collections import Counter
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'exercicios'))
import respostas as answer

def connect(host=None, db='horizonte', autocommit=False):
    import psycopg
    return psycopg.connect(host=host or os.getenv('DB_HOST','basic'),dbname=db,user='postgres',password=os.getenv('DB_PASSWORD','horizonte_local'),connect_timeout=10,autocommit=autocommit)

def emit(**x):
    print(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),**x},ensure_ascii=False,default=str),flush=True)

def catalog(args):
    low,high=Decimal(args[1]),Decimal(args[2])
    if not low.is_finite() or not high.is_finite() or low<0 or low>high:
        raise ValueError('Faixa inválida: valores finitos, mínimo >= 0 e mínimo <= máximo.')
    with connect() as c:
        rows=c.execute(answer.catalogo_sql(),(args[0],low,high)).fetchall()
        emit(comando='catalogo',colunas=['id','nome','preco_atual'],linhas=rows)

def h(s): return int.from_bytes(hashlib.sha256(s.encode('utf-8')).digest()[:8],'big')
def distribution(nodes,mode):
    nodes=sorted(nodes)
    points=sorted((h(f'N:{n}:{i:02d}'),n,i) for n in nodes for i in range(16 if mode=='virtual' else 1))
    result={}
    for i in range(1000):
        k=f'K:{i:04d}'
        if mode=='faixa':n='A' if i<=333 else 'B' if i<=666 else 'C'
        elif mode=='modulo':n=answer.modulo(h(k),nodes)
        else:n=answer.sucessor(h(k),points)
        result[k]=n
    return result

def shard(out):
    folder=Path(out);folder.mkdir(parents=True,exist_ok=True)
    for mode in ['faixa','modulo','anel','virtual']:
        before=distribution('ABC',mode); after=before if mode=='faixa' else distribution('ABCD',mode)
        with (folder/f'{mode}.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['chave','antes','depois']);w.writerows((k,before[k],after[k]) for k in before)
        counts=Counter(after.values());m=answer.movidas(before,after)
        emit(tipo='SIMULADO',modo=mode,antes=dict(Counter(before.values())),depois=dict(counts),menor=min(counts.values()),maior=max(counts.values()),movidas=m,percentual=m/10)

def scalar(c,q,args=()):return c.execute(q,args).fetchone()[0]
def wait_for(fn,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if fn():return
        time.sleep(.1)
    raise TimeoutError('Condição não atingida dentro do limite')

def replica(mode):
    import threading
    if mode not in ['async','on','remote_apply','timeout']:raise ValueError(mode)
    identifier={'async':2001,'on':2002,'remote_apply':2003,'timeout':2004}[mode]
    with connect('primary',autocommit=True) as p,connect('standby',autocommit=True) as s:
        assert not scalar(p,'SELECT pg_is_in_recovery()') and scalar(s,'SELECT pg_is_in_recovery()')
        p.execute("ALTER SYSTEM SET synchronous_standby_names = ''" if mode=='async' else "ALTER SYSTEM SET synchronous_standby_names = 'FIRST 1 (standby1)'")
        p.execute('SELECT pg_reload_conf()')
        wait_for(lambda: scalar(p,"SHOW synchronous_standby_names")==('' if mode=='async' else 'FIRST 1 (standby1)'))
        if mode!='async':wait_for(lambda: scalar(p,"SELECT count(*) FROM pg_stat_replication WHERE application_name='standby1' AND sync_state='sync'")==1)
        if scalar(p,'SELECT count(*) FROM evento_lab WHERE id=%s',(identifier,)):
            raise ValueError('ID já usado; execute reset replica para repetir, preservando os logs.')
        s.execute('SELECT pg_wal_replay_pause()')
        wait_for(lambda: scalar(s,'SELECT pg_get_wal_replay_pause_state()')=='paused')
        result={}
        def write():
            start=time.monotonic()
            try:
                with connect('primary') as w:
                    w.execute("SET synchronous_commit TO "+('remote_apply' if mode=='timeout' else 'on' if mode=='async' else mode))
                    w.execute("SET statement_timeout TO "+("'1500ms'" if mode=='timeout' else "'30s'"))
                    w.execute('INSERT INTO evento_lab VALUES(%s,%s,%s)',(identifier,identifier-1993,mode))
                    w.commit()
                result['resultado']='confirmado'
            except Exception as ex:result.update(resultado='desconhecido',erro=str(ex))
            result['duracao_ms']=(time.monotonic()-start)*1000
        thread=threading.Thread(target=write);thread.start()
        try:
            if mode in ['async','on']:
                thread.join(30)
                if thread.is_alive():raise TimeoutError('Commit não concluiu com replay pausado')
                assert result.get('resultado')=='confirmado', result
            else:
                time.sleep(3)
                if mode=='remote_apply':assert thread.is_alive(),'remote_apply deveria aguardar replay'
            visible=scalar(s,'SELECT count(*) FROM evento_lab WHERE id=%s',(identifier,))
            assert visible==0
            emit(tipo='REAL',modo=mode,replay='paused',id=identifier,linhas_standby=visible,cliente_esperando=thread.is_alive(),resultado=result)
        finally:
            s.execute('SELECT pg_wal_replay_resume()')
            thread.join(35)
            p.execute("ALTER SYSTEM SET synchronous_standby_names = ''");p.execute('SELECT pg_reload_conf()')
        if thread.is_alive():raise TimeoutError('Cliente ainda ativo após retomada')
        committed=scalar(p,'SELECT count(*) FROM evento_lab WHERE id=%s',(identifier,))
        if committed:wait_for(lambda:scalar(s,'SELECT count(*) FROM evento_lab WHERE id=%s',(identifier,))==1)
        emit(tipo='REAL',modo=mode,replay='resumed',confirmacao_consultada_no_primario=committed,resultado=result)
        if mode!='timeout':assert committed==1

def state(c,op,new):
    c.execute('UPDATE saga SET estado=%s WHERE op=%s',(new,op))
    c.execute('INSERT INTO evento(op,estado) VALUES(%s,%s)',(op,new))
    c.commit();emit(op=op,estado=new)

def reserve(op):
    with connect('saga','estoque') as c:
        c.execute('INSERT INTO estoque(op) VALUES(%s) ON CONFLICT DO NOTHING',(op,))
        c.execute('SELECT disponivel FROM estoque WHERE op=%s FOR UPDATE',(op,))
        row=c.execute('SELECT estado FROM reserva WHERE op=%s',(op,)).fetchone()
        if row:return row[0]
        assert c.execute('UPDATE estoque SET disponivel=disponivel-1 WHERE op=%s AND disponivel>=1 RETURNING op',(op,)).fetchone()
        c.execute("INSERT INTO reserva VALUES(%s,'ATIVA')",(op,))
    return 'ATIVA'

def release(op):
    with connect('saga','estoque') as c:
        c.execute('SELECT disponivel FROM estoque WHERE op=%s FOR UPDATE',(op,))
        row=c.execute(answer.liberar_sql(),(op,)).fetchone()
        if row:c.execute('UPDATE estoque SET disponivel=disponivel+1 WHERE op=%s',(op,))
        elif not c.execute('SELECT 1 FROM reserva WHERE op=%s',(op,)).fetchone():raise ValueError('Reserva inexistente')

def pay(op,mode):
    with connect('saga','pagamentos') as c:
        c.execute('INSERT INTO pagamento VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(op,mode,int(mode=='aprovado')))
        previous=scalar(c,'SELECT resultado FROM pagamento WHERE op=%s',(op,))
        if previous!=mode:raise ValueError('Mesma intenção com modo diferente')
        return previous

def saga(op,mode,fault='none'):
    with connect('saga','pedidos') as c:
        c.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',(op,));c.commit()
        c.execute('INSERT INTO saga(op,modo) VALUES(%s,%s) ON CONFLICT DO NOTHING',(op,mode));c.commit()
        if scalar(c,'SELECT modo FROM saga WHERE op=%s',(op,))!=mode:raise ValueError('Modo mudou para a mesma intenção')
        for _ in range(10):
            old=scalar(c,'SELECT estado FROM saga WHERE op=%s',(op,));c.commit()
            action=answer.proxima(old)
            if action=='fim':emit(op=op,estado=old);return
            if action=='reservar':
                reserve(op)
                if fault=='after-reserve':raise RuntimeError('FALHA_INJETADA after-reserve')
                state(c,op,'RESERVADO')
            elif action=='pagar':state(c,op,answer.apos_pagamento(pay(op,mode)))
            elif action=='confirmar':state(c,op,'CONFIRMADO')
            elif action=='liberar':
                release(op)
                if fault=='after-release':raise RuntimeError('FALHA_INJETADA after-release')
                state(c,op,'CANCELADO')
            else:raise ValueError('Ação não reconhecida: '+action)
        raise RuntimeError('Saga não convergiu')

def snapshot(op):
    result={'op':op}
    for db,q,key in [('pedidos','SELECT estado FROM saga WHERE op=%s','estado'),('estoque','SELECT disponivel FROM estoque WHERE op=%s','estoque'),('estoque','SELECT estado FROM reserva WHERE op=%s','reserva'),('pagamentos','SELECT cobrancas FROM pagamento WHERE op=%s','cobrancas')]:
        with connect('saga',db) as c:
            r=c.execute(q,(op,)).fetchone();result[key]=None if r is None else r[0]
    emit(**result)

def migration(version,count):
    if version not in ['v1','v2','final']:raise ValueError(version)
    for i in range(count):
        start=time.monotonic()
        with connect('migration') as c:
            c.execute('SELECT pg_advisory_xact_lock_shared(8101)')
            phase=scalar(c,'SELECT phase FROM lab_gate WHERE id=1')
            if version=='v1' and phase not in ['old','return-test']:raise ValueError('v1 retirado pelo gate')
            if version=='v2' and phase in ['final','contracted']:raise ValueError('v2 compatível retirado')
            if version=='final' and phase!='contracted':raise ValueError('Cliente final liberado após contração')
            col='email' if version=='final' else 'contato_email'
            value=None if i%5==0 else f'ana.{i}@exemplo.test'
            c.execute(f'UPDATE cliente SET {col}=%s WHERE id=42',(value,))
            read='contato_email' if version=='v1' else 'email' if version=='final' else 'COALESCE(email,contato_email)'
            actual=scalar(c,f'SELECT {read} FROM cliente WHERE id=42')
            assert actual==value
            if version=='v1' and phase=='return-test':c.execute('UPDATE lab_gate SET returned=true WHERE id=1')
            if version=='v2' and phase=='window':c.execute('UPDATE lab_gate SET window_count=window_count+1 WHERE id=1')
            c.execute('INSERT INTO lab_ops(versao,duracao_ms,sucesso) VALUES(%s,%s,true)',(version,(time.monotonic()-start)*1000))
        emit(cliente=version,iteracao=i,valor=actual,duracao_ms=(time.monotonic()-start)*1000)
        time.sleep(1)

def backfill(limit):
    for _ in range(limit):
        with connect('migration') as c:
            checkpoint=scalar(c,'SELECT last_id FROM lab_checkpoint WHERE id=1 FOR UPDATE')
            ids=[r[0] for r in c.execute('SELECT id FROM cliente WHERE id>%s ORDER BY id LIMIT 25',(checkpoint,))]
            if not ids:return
            # Fonte autoritativa lida pelo próprio UPDATE, sem copiar valores antigos em memória.
            c.execute('UPDATE cliente SET email=contato_email WHERE id>%s AND id<=%s',(checkpoint,max(ids)))
            c.execute('UPDATE lab_checkpoint SET last_id=%s WHERE id=1',(max(ids),))
            emit(limite_inicial=checkpoint,limite_final=max(ids),linhas=len(ids),checkpoint=max(ids))

if __name__=='__main__':
    try:
        cmd,*a=sys.argv[1:]
        if cmd=='catalogo':catalog(a)
        elif cmd=='shard':shard(a[0] if a else 'evidencias/execucoes/shard-python')
        elif cmd=='replica':replica(a[0])
        elif cmd=='saga':saga(*a)
        elif cmd=='liberar':release(a[0]);snapshot(a[0])
        elif cmd=='snapshot':snapshot(a[0])
        elif cmd=='migration':migration(a[0],int(a[1]))
        elif cmd=='backfill':backfill(int(a[0]) if a else 100)
        else:raise ValueError('Comando desconhecido')
    except Exception as ex:
        emit(erro=str(ex),classe=type(ex).__name__);sys.exit(17 if 'FALHA_INJETADA' in str(ex) else 1)
