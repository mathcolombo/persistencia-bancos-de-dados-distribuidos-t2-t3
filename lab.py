#!/usr/bin/env python3
"""Interface multiplataforma. Só requer Python 3.10+ e Docker Compose no host."""
import argparse, subprocess, sys, json, time, re, csv, os
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent
EVID=ROOT/'evidencias'/'execucoes'
GROUPS={'basic':['basic'],'replica':['primary','standby'],'migration':['migration'],'saga':['saga'],'pitr':['origin','destination','restore-prep','fault-destination','fault-prep']}
VOLUMES={'basic':['basic_data'],'replica':['primary_data','standby_data'],'migration':['migration_data'],'saga':['saga_data'],'pitr':['origin_data','destination_data','archive_data','backup_data','fault_destination_data','empty_archive_data']}
BASE=['docker','compose','-p','horizonte-lab','-f',str(ROOT/'compose.yaml')]
LOG=None

def run(args,check=True,input=None,quiet=False):
    p=subprocess.run(args,cwd=ROOT,input=input,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if not quiet:print(p.stdout,end='',flush=True)
    if LOG:
        with LOG.open('a',encoding='utf-8') as f:f.write('$ '+' '.join(args)+'\n'+p.stdout+f'\n[exit={p.returncode}]\n')
    if check and p.returncode:raise RuntimeError(f'Comando terminou com código {p.returncode}; consulte o log.')
    return p

def dc(*args,**kw):return run(BASE+list(args),**kw)
def sql(service,query,db='horizonte',quiet=False):
    if service not in sum(GROUPS.values(),[]):raise ValueError('Serviço inválido')
    return dc('exec','-T',service,'psql','-X','-v','ON_ERROR_STOP=1','-U','postgres','-d',db,'-At','-c',query,quiet=quiet).stdout.strip()
def file_sql(service,path,db='horizonte'):
    f=(ROOT/path).resolve()
    if not f.is_relative_to(ROOT):raise ValueError('Arquivo fora do kit')
    return dc('exec','-T',service,'psql','-X','-v','ON_ERROR_STOP=1','-U','postgres','-d',db,input=f.read_text(encoding='utf-8'))
def lit(x):return "'"+str(x).replace("'","''")+"'"
def save(name,data):
    EVID.mkdir(parents=True,exist_ok=True);(EVID/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
def utc():return datetime.now(timezone.utc).isoformat()
def load(name):return json.loads((EVID/name).read_text(encoding='utf-8'))
def tool(lang,*args,check=True,host='basic'):
    cmd=['python','clientes/python/app.py'] if lang=='python' else ['sh','infra/java.sh']
    user=['--user',str(os.getuid())+':'+str(os.getgid())] if sys.platform=='linux' else []
    return dc('run','--rm','--no-deps',*user,'-e','DB_HOST='+host,'tools',*cmd,*args,check=check)
def up(group):
    services=['origin'] if group=='pitr' else GROUPS[group]
    dc('up','-d','--wait','--wait-timeout','120',*services)
def reset(group,confirm):
    if confirm!='APAGAR-LAB':raise ValueError('Use --confirmar APAGAR-LAB somente após guardar evidências. Remove apenas os volumes do perfil indicado.')
    dc('stop',*GROUPS[group]);dc('rm','-f',*GROUPS[group])
    for v in VOLUMES[group]:
        name='horizonte-lab_'+v
        inspect=run(['docker','volume','inspect',name],check=False,quiet=True)
        if inspect.returncode:continue
        data=json.loads(inspect.stdout)[0]
        if data.get('Labels',{}).get('com.docker.compose.project')!='horizonte-lab':raise RuntimeError('Volume não pertence ao projeto')
        run(['docker','volume','rm',name])
    if group=='pitr' and (EVID/'pitr-controle.json').exists():
        (EVID/'pitr-controle.json').rename(EVID/('pitr-controle-arquivado-'+str(time.time_ns())+'.json'))
    print('Perfil limpo; evidências preservadas.')

def gate(action):
    if action not in ['retirar','retorno','janela','liberar']:raise ValueError(action)
    phase={'retirar':'window','retorno':'return-test','janela':'window','liberar':'final'}[action]
    pre=""
    if action=='retirar':pre="IF p<>'old' THEN RAISE EXCEPTION 'Retirada exige fase old'; END IF;"
    if action=='retorno':pre="IF p<>'window' THEN RAISE EXCEPTION 'Retorno exige janela'; END IF;"
    if action=='janela':pre="IF p<>'return-test' OR NOT r THEN RAISE EXCEPTION 'Execute v1 durante teste de retorno'; END IF;"
    if action=='liberar':pre="IF p<>'window' OR n<10 OR NOT r THEN RAISE EXCEPTION 'Exige retorno testado e dez ciclos completos'; END IF;"
    statement=f"""BEGIN; SELECT pg_advisory_xact_lock(8101);
DO $$ DECLARE p text; n integer; r boolean; BEGIN
 SELECT phase,window_count,returned INTO p,n,r FROM lab_gate WHERE id=1;
 {pre}
 IF EXISTS(SELECT 1 FROM cliente WHERE email IS DISTINCT FROM contato_email) THEN RAISE EXCEPTION 'Dados divergentes'; END IF;
END $$;
UPDATE lab_gate SET phase={lit(phase)}{',window_count=0' if action!='liberar' else ''} WHERE id=1; COMMIT;
SELECT * FROM lab_gate;"""
    sql('migration',statement)

def flyway(phase):
    if phase=='expand':
        if 'TODO_ALUNO' in (ROOT/'migrations/expand/V1__expand.sql').read_text():raise ValueError('Complete a migração V1 antes de executá-la.')
        # Base inicial não vazia; baseline explícito v0, sem migrar/limpar dados.
        dc('run','--rm','flyway','-locations=filesystem:/flyway/sql/expand','-baselineOnMigrate=true','-baselineVersion=0','migrate','info')
    else:
        dc('run','--rm','flyway','-locations=filesystem:/flyway/sql/expand,filesystem:/flyway/sql/contract','migrate','info')

def pitr(stage):
    control=EVID/'pitr-controle.json'
    if stage=='backup':
        if control.exists():raise ValueError('Há experimento anterior. Exporte evidências e use reset pitr antes de repetir.')
        up('pitr')
        sql('origin',"CREATE TABLE registro_recuperacao(id integer PRIMARY KEY,descricao text NOT NULL,instante timestamptz NOT NULL DEFAULT clock_timestamp()); INSERT INTO registro_recuperacao(id,descricao) VALUES(1,'BASE');")
        start=time.monotonic()
        dc('exec','-T','-u','postgres','-e','PGPASSWORD=horizonte_local','origin','pg_basebackup','-h','127.0.0.1','-U','postgres','-D','/backup/base','-Fp','-Xs','-c','fast','-P')
        dc('exec','-T','-u','postgres','origin','pg_verifybackup','/backup/base')
        save('pitr-controle.json',{'execucao':'lab_'+str(time.time_ns()),'backup_segundos':time.monotonic()-start,'base_fim':utc(),'operacoes':[]})
    elif stage=='incidente':
        c=load('pitr-controle.json')
        if 'incidente_mono' in c:raise ValueError('Incidente já registrado')
        sql('origin',"INSERT INTO registro_recuperacao(id,descricao) VALUES(2,'ANTES_DO_MARCADOR');")
        c['operacoes'].append({'id':2,'utc':utc(),'mono':time.monotonic()})
        c['lsn']=sql('origin','SELECT pg_create_restore_point('+lit(c['execucao'])+');',quiet=True)
        dc('exec','-T','-u','postgres','origin','bash','-c','printf "%s\\n" "$1" > /backup/target.txt','_',c['execucao'])
        sql('origin',"INSERT INTO registro_recuperacao(id,descricao) VALUES(3,'DEPOIS_DO_MARCADOR');")
        c['operacoes'].append({'id':3,'utc':utc(),'mono':time.monotonic()})
        sql('origin','DELETE FROM registro_recuperacao; SELECT count(*) FROM registro_recuperacao;')
        c['incidente_utc']=utc();c['incidente_mono']=time.monotonic();save('pitr-controle.json',c)
        segment=sql('origin','SELECT pg_walfile_name(pg_current_wal_insert_lsn());',quiet=True)
        if not re.fullmatch('[0-9A-F]{24}',segment):raise ValueError('Nome WAL inválido')
        sql('origin','SELECT pg_switch_wal();')
        end=time.monotonic()+60
        while time.monotonic()<end:
            if dc('exec','-T','origin','test','-f','/archive/'+segment,check=False,quiet=True).returncode==0:break
            time.sleep(.5)
        else:raise TimeoutError('WAL não foi arquivado. Não avançar para restore.')
        c['wal_final']=segment;save('pitr-controle.json',c)
        print('Marcador deste experimento:',c['execucao'])
        print('Incidente registrado. Execute pitr restaurar e depois pitr medir; o relógio de RTO já está contando.')
    elif stage=='restaurar':
        c=load('pitr-controle.json')
        if 'wal_final' not in c:raise ValueError('Arquivamento não confirmado')
        chosen=json.loads((ROOT/'exercicios/pitr.json').read_text(encoding='utf-8'))['nome_do_ponto']
        target=c['execucao'] if chosen=='AUTO' else chosen
        if not re.fullmatch('lab_[a-zA-Z0-9_]+',target):raise ValueError('Preencha exercicios/pitr.json com o marcador informado no incidente')
        dc('exec','-T','-u','postgres','origin','bash','-c','printf "%s\\n" "$1" > /backup/target.txt','_',target)
        dc('stop','destination')
        dc('run','--rm','--no-deps','restore-prep')
        dc('up','-d','destination')
        end=time.monotonic()+90
        while time.monotonic()<end:
            p=dc('exec','-T','destination','psql','-X','-U','postgres','-d','horizonte','-At','-c','SELECT pg_is_in_recovery()',check=False,quiet=True)
            if p.returncode==0 and p.stdout.strip()=='f':break
            time.sleep(1)
        else:
            dc('logs','destination');raise TimeoutError('Alvo não confirmado. Verifique WAL, nome e logs; não promova manualmente.')
        ids=sql('destination','SELECT id FROM registro_recuperacao ORDER BY id',quiet=True)
        if ids!='1\n2':raise AssertionError('Estado inesperado no destino: '+ids)
        if sql('origin','SELECT count(*) FROM registro_recuperacao',quiet=True)!='0':raise AssertionError('Origem inesperada')
        logs=dc('logs','--no-color','destination').stdout
        if c['execucao'] not in logs:raise AssertionError('Log não contém o ponto de recuperação')
        c['validado_utc']=utc();c['validado_mono']=time.monotonic();c['ids_destino']=[1,2];save('pitr-controle.json',c)
        print('PASS: destino contém 1 e 2; não contém 3; origem continua vazia; alvo consta no log.')
    elif stage=='medir':
        c=load('pitr-controle.json')
        if 'validado_mono' not in c:raise ValueError('Restore não validado')
        rto=c['validado_mono']-c['incidente_mono'];rpo=c['incidente_mono']-c['operacoes'][0]['mono']
        result={'RTO_observado_s':rto,'janela_perda_observada_s':rpo,'RTO_meta_600s_atendida':rto<=600,'RPO_meta_60s_atendida':rpo<=60,'ids_legitimos_fora_do_alvo':[3],'base_segundos':c['backup_segundos'],'metodo':'mesmo relógio monotônico do host; inclui espera entre comandos; não reiniciar host durante ensaio'}
        save('pitr-metricas.json',result)
        with (EVID/'pitr-operacoes.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['id','utc','mono']);w.writeheader();w.writerows(c['operacoes'])
        print(json.dumps(result,indent=2,ensure_ascii=False))
    else:raise ValueError(stage)

def main():
    global LOG
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor');sub.add_parser('build');sub.add_parser('status');sub.add_parser('stop')
    p=sub.add_parser('up');p.add_argument('perfil',choices=GROUPS)
    p=sub.add_parser('reset');p.add_argument('perfil',choices=GROUPS);p.add_argument('--confirmar',required=True)
    p=sub.add_parser('sql');p.add_argument('servico',choices=sum(GROUPS.values(),[]));p.add_argument('--db',default='horizonte');g=p.add_mutually_exclusive_group(required=True);g.add_argument('-q');g.add_argument('-f')
    p=sub.add_parser('client');p.add_argument('linguagem',choices=['python','java']);p.add_argument('args',nargs=argparse.REMAINDER)
    p=sub.add_parser('migrate');p.add_argument('fase',choices=['expand','contract'])
    p=sub.add_parser('gate');p.add_argument('acao',choices=['retirar','retorno','janela','liberar'])
    p=sub.add_parser('pitr');p.add_argument('fase',choices=['backup','incidente','restaurar','medir','completo'])
    p=sub.add_parser('test');p.add_argument('suite',choices=['unit','t1','saga','migration','replica','pitr','pitr-wal-ausente','all']);p.add_argument('--linguagem',choices=['python','java'],default='python')
    a=parser.parse_args();EVID.mkdir(parents=True,exist_ok=True);LOG=EVID/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns())+'-'+a.cmd+'.log')
    if a.cmd=='doctor':
        run(['docker','version']);dc('version');dc('config','--quiet');run(['docker','info','--format','{{.OSType}}'])
        print('PASS ferramentas. Imagens precisam de internet no primeiro download. Não é um teste dos exercícios.')
    elif a.cmd=='build':dc('build','tools');dc('pull','basic','flyway')
    elif a.cmd=='up':up(a.perfil)
    elif a.cmd=='status':dc('ps','-a');dc('images');run(['docker','image','inspect','postgres:18.6-bookworm@sha256:3725f4e2499eef5134592b3b4ab79a543ed7f8e533b05b5b637af926630f6650','--format','{{json .RepoDigests}}'])
    elif a.cmd=='stop':dc('stop')
    elif a.cmd=='reset':reset(a.perfil,a.confirmar)
    elif a.cmd=='sql':file_sql(a.servico,a.f,a.db) if a.f else sql(a.servico,a.q,a.db)
    elif a.cmd=='client':tool(a.linguagem,*a.args)
    elif a.cmd=='migrate':flyway(a.fase)
    elif a.cmd=='gate':gate(a.acao)
    elif a.cmd=='pitr':
        for stage in (['backup','incidente','restaurar','medir'] if a.fase=='completo' else [a.fase]):pitr(stage)
    elif a.cmd=='test':
        sys.path.insert(0,str(ROOT/'tests'));import integration
        integration.execute(a.suite,a.linguagem,sys.modules[__name__])
    print('Log:',LOG.relative_to(ROOT))

if __name__=='__main__':
    try:main()
    except Exception as ex:print('ERRO:',ex,file=sys.stderr);sys.exit(1)
