import java.sql.*;
import java.util.*;
import java.util.concurrent.*;
import java.math.BigDecimal;
import java.nio.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;

public class App {
 static Connection db(String host,String name) throws Exception {
  Connection c=DriverManager.getConnection("jdbc:postgresql://"+host+":5432/"+name+"?connectTimeout=10", "postgres",System.getenv().getOrDefault("DB_PASSWORD","horizonte_local"));c.setAutoCommit(false);return c;
 }
 static List<List<Object>> q(Connection c,String sql,Object...args)throws Exception {
  try(PreparedStatement p=c.prepareStatement(sql)){
   for(int i=0;i<args.length;i++)p.setObject(i+1,args[i]);
   if(!p.execute())return List.of();
   try(ResultSet rs=p.getResultSet()){
    List<List<Object>> rows=new ArrayList<>();
    while(rs.next()){List<Object> row=new ArrayList<>();for(int i=1;i<=rs.getMetaData().getColumnCount();i++)row.add(rs.getObject(i));rows.add(row);}return rows;
   }
  }
 }
 static Object one(Connection c,String sql,Object...args)throws Exception{return q(c,sql,args).get(0).get(0);}
 static void log(String text){System.out.println(Instant.now()+" "+text);}
 static void catalog(String[]a)throws Exception{
  BigDecimal lo=new BigDecimal(a[1]),hi=new BigDecimal(a[2]);if(lo.signum()<0||lo.compareTo(hi)>0)throw new IllegalArgumentException("Faixa inválida");
  try(Connection c=db(System.getenv().getOrDefault("DB_HOST","basic"),"horizonte")){log("colunas=id,nome,preco_atual linhas="+q(c,Respostas.catalogoSql(),a[0],lo,hi));c.commit();}
 }
 public record Point(long hash,String node,int virtual){}
 static long hash(String s)throws Exception{return ByteBuffer.wrap(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8))).getLong();}
 static Map<String,String> distribution(String names,String mode)throws Exception{
  List<String> nodes=names.chars().mapToObj(c->String.valueOf((char)c)).sorted().toList();List<Point> points=new ArrayList<>();
  for(String n:nodes)for(int i=0;i<(mode.equals("virtual")?16:1);i++)points.add(new Point(hash(String.format(Locale.ROOT,"N:%s:%02d",n,i)),n,i));
  points.sort((a,b)->{int c=Long.compareUnsigned(a.hash(),b.hash());if(c!=0)return c;c=a.node().compareTo(b.node());return c!=0?c:Integer.compare(a.virtual(),b.virtual());});
  Map<String,String> out=new LinkedHashMap<>();
  for(int i=0;i<1000;i++){String k=String.format(Locale.ROOT,"K:%04d",i);String n=mode.equals("faixa")?(i<=333?"A":i<=666?"B":"C"):mode.equals("modulo")?Respostas.modulo(hash(k),nodes):Respostas.sucessor(hash(k),points);out.put(k,n);}return out;
 }
 static void shard(String dir)throws Exception{
  Files.createDirectories(Path.of(dir));
  for(String mode:List.of("faixa","modulo","anel","virtual")){
   Map<String,String>a=distribution("ABC",mode),b=mode.equals("faixa")?a:distribution("ABCD",mode);StringBuilder csv=new StringBuilder("chave,antes,depois\n");
   Map<String,Integer> counts=new TreeMap<>();for(String k:a.keySet()){csv.append(k+","+a.get(k)+","+b.get(k)+"\n");counts.merge(b.get(k),1,Integer::sum);}
   Files.writeString(Path.of(dir,mode+".csv"),csv,StandardCharsets.UTF_8);long moved=Respostas.movidas(a,b);
   log("SIMULADO modo="+mode+" depois="+counts+" menor="+Collections.min(counts.values())+" maior="+Collections.max(counts.values())+" movidas="+moved+" percentual="+(moved/10.0));
  }
 }
 interface Condition{boolean ok()throws Exception;}
 static void waitFor(Condition f)throws Exception{long end=System.nanoTime()+30_000_000_000L;while(System.nanoTime()<end){if(f.ok())return;Thread.sleep(100);}throw new Exception("Timeout aguardando condição");}
 static boolean countIs(Connection c,int id,long n)throws Exception{return ((Number)one(c,"SELECT count(*) FROM evento_lab WHERE id=?",id)).longValue()==n;}
 static void replica(String mode)throws Exception{
  int id=switch(mode){case "async"->2001;case "on"->2002;case "remote_apply"->2003;case "timeout"->2004;default->throw new IllegalArgumentException(mode);};
  try(Connection p=db("primary","horizonte");Connection s=db("standby","horizonte")){
   p.setAutoCommit(true);s.setAutoCommit(true);
   if((Boolean)one(p,"SELECT pg_is_in_recovery()")||!(Boolean)one(s,"SELECT pg_is_in_recovery()"))throw new Exception("Identidades incorretas");
   q(p,mode.equals("async")?"ALTER SYSTEM SET synchronous_standby_names=''":"ALTER SYSTEM SET synchronous_standby_names='FIRST 1 (standby1)'");q(p,"SELECT pg_reload_conf()");
   waitFor(()->one(p,"SHOW synchronous_standby_names").equals(mode.equals("async")?"":"FIRST 1 (standby1)"));
   if(!mode.equals("async"))waitFor(()->((Number)one(p,"SELECT count(*) FROM pg_stat_replication WHERE application_name='standby1' AND sync_state='sync'")).intValue()==1);
   if(!countIs(p,id,0))throw new Exception("ID já usado; reset replica após exportar logs");
   q(s,"SELECT pg_wal_replay_pause()");waitFor(()->one(s,"SELECT pg_get_wal_replay_pause_state()").equals("paused"));
   Map<String,String> result=new ConcurrentHashMap<>();
   Thread t=new Thread(()->{long start=System.nanoTime();try(Connection w=db("primary","horizonte")){
    q(w,"SET synchronous_commit TO "+(mode.equals("async")?"on":mode.equals("timeout")?"remote_apply":mode));
    q(w,"SET statement_timeout TO '"+(mode.equals("timeout")?"1500ms":"30s")+"'");
    q(w,"INSERT INTO evento_lab VALUES(?,?,?)",id,id-1993,mode);w.commit();result.put("resultado","confirmado");
   }catch(Exception ex){result.put("resultado","desconhecido");result.put("erro",ex.toString());}finally{result.put("duracao_ms",String.valueOf((System.nanoTime()-start)/1e6));}});t.start();
   try{
    if(mode.equals("async")||mode.equals("on")){t.join(30000);if(t.isAlive()||!"confirmado".equals(result.get("resultado")))throw new Exception("Commit não confirmou: "+result);}
    else {Thread.sleep(3000);if(mode.equals("remote_apply")&&!t.isAlive())throw new Exception("remote_apply deveria aguardar");}
    if(!countIs(s,id,0))throw new Exception("Linha visível durante pausa");log("REAL modo="+mode+" replay=paused standby=0 esperando="+t.isAlive()+" "+result);
   }finally{q(s,"SELECT pg_wal_replay_resume()");t.join(35000);q(p,"ALTER SYSTEM SET synchronous_standby_names=''");q(p,"SELECT pg_reload_conf()");}
   if(t.isAlive())throw new Exception("Cliente não terminou");boolean committed=countIs(p,id,1);if(committed)waitFor(()->countIs(s,id,1));
   log("REAL modo="+mode+" replay=resumed confirmado_no_primario="+committed+" "+result);if(!mode.equals("timeout")&&!committed)throw new Exception("Linha ausente");
  }
 }
 static void reserve(String op)throws Exception{
  try(Connection c=db("saga","estoque")){
   q(c,"INSERT INTO estoque(op) VALUES(?) ON CONFLICT DO NOTHING",op);q(c,"SELECT disponivel FROM estoque WHERE op=? FOR UPDATE",op);
   if(q(c,"SELECT estado FROM reserva WHERE op=?",op).isEmpty()){
    if(q(c,"UPDATE estoque SET disponivel=disponivel-1 WHERE op=? AND disponivel>=1 RETURNING op",op).isEmpty())throw new Exception("Sem estoque");
    q(c,"INSERT INTO reserva VALUES(?,'ATIVA')",op);
   }c.commit();
  }
 }
 static void release(String op)throws Exception{
  try(Connection c=db("saga","estoque")){
   q(c,"SELECT disponivel FROM estoque WHERE op=? FOR UPDATE",op);
   if(!q(c,Respostas.liberarSql(),op).isEmpty())q(c,"UPDATE estoque SET disponivel=disponivel+1 WHERE op=?",op);
   else if(q(c,"SELECT 1 FROM reserva WHERE op=?",op).isEmpty())throw new Exception("Reserva inexistente");c.commit();
  }
 }
 static String pay(String op,String mode)throws Exception{
  try(Connection c=db("saga","pagamentos")){
   q(c,"INSERT INTO pagamento VALUES(?,?,?) ON CONFLICT DO NOTHING",op,mode,mode.equals("aprovado")?1:0);
   String r=(String)one(c,"SELECT resultado FROM pagamento WHERE op=?",op);if(!r.equals(mode))throw new Exception("Modo diferente para mesma intenção");c.commit();return r;
  }
 }
 static void state(Connection c,String op,String next)throws Exception{q(c,"UPDATE saga SET estado=? WHERE op=?",next,op);q(c,"INSERT INTO evento(op,estado) VALUES(?,?)",op,next);c.commit();log("op="+op+" estado="+next);}
 static void saga(String op,String mode,String fault)throws Exception{
  try(Connection c=db("saga","pedidos")){
   q(c,"SELECT pg_advisory_lock(hashtextextended(?,0))",op);c.commit();
   q(c,"INSERT INTO saga(op,modo) VALUES(?,?) ON CONFLICT DO NOTHING",op,mode);c.commit();if(!one(c,"SELECT modo FROM saga WHERE op=?",op).equals(mode))throw new Exception("Modo alterado");
   for(int i=0;i<10;i++){
    String old=(String)one(c,"SELECT estado FROM saga WHERE op=?",op);c.commit();
    switch(Respostas.proxima(old)){
     case "fim":log("op="+op+" estado="+old);return;
     case "reservar":reserve(op);if(fault.equals("after-reserve"))throw new Exception("FALHA_INJETADA after-reserve");state(c,op,"RESERVADO");break;
     case "pagar":state(c,op,Respostas.aposPagamento(pay(op,mode)));break;
     case "confirmar":state(c,op,"CONFIRMADO");break;
     case "liberar":release(op);if(fault.equals("after-release"))throw new Exception("FALHA_INJETADA after-release");state(c,op,"CANCELADO");break;
     default:throw new Exception("Ação inválida");
    }
   }throw new Exception("Saga não convergiu");
  }
 }
 static void snapshot(String op)throws Exception{
  String[] dbs={"pedidos","estoque","estoque","pagamentos"},sql={"SELECT estado FROM saga WHERE op=?","SELECT disponivel FROM estoque WHERE op=?","SELECT estado FROM reserva WHERE op=?","SELECT cobrancas FROM pagamento WHERE op=?"};
  for(int i=0;i<dbs.length;i++)try(Connection c=db("saga",dbs[i])){log(op+" "+dbs[i]+" "+q(c,sql[i],op));c.commit();}
 }
 static void migration(String version,int count)throws Exception{
  if(!List.of("v1","v2","final").contains(version))throw new Exception("Versão inválida");
  for(int i=0;i<count;i++){
   long start=System.nanoTime();
   try(Connection c=db("migration","horizonte")){
    q(c,"SELECT pg_advisory_xact_lock_shared(8101)");String phase=(String)one(c,"SELECT phase FROM lab_gate WHERE id=1");
    if(version.equals("v1")&&!List.of("old","return-test").contains(phase))throw new Exception("v1 retirado");
    if(version.equals("v2")&&List.of("final","contracted").contains(phase))throw new Exception("v2 compatível retirado");
    if(version.equals("final")&&!phase.equals("contracted"))throw new Exception("Cliente final exige contração");
    String col=version.equals("final")?"email":"contato_email",val=i%5==0?null:"ana."+i+"@exemplo.test";
    q(c,"UPDATE cliente SET "+col+"=? WHERE id=42",val);
    String read=version.equals("v1")?"contato_email":version.equals("final")?"email":"COALESCE(email,contato_email)";
    if(!Objects.equals(one(c,"SELECT "+read+" FROM cliente WHERE id=42"),val))throw new Exception("Leitura divergente");
    if(version.equals("v1")&&phase.equals("return-test"))q(c,"UPDATE lab_gate SET returned=true WHERE id=1");
    if(version.equals("v2")&&phase.equals("window"))q(c,"UPDATE lab_gate SET window_count=window_count+1 WHERE id=1");
    q(c,"INSERT INTO lab_ops(versao,duracao_ms,sucesso) VALUES(?,?,true)",version,(System.nanoTime()-start)/1e6);c.commit();
   }log("cliente="+version+" iteracao="+i+" duracao_ms="+(System.nanoTime()-start)/1e6);Thread.sleep(1000);
  }
 }
 static void backfill(int batches)throws Exception{
  for(int i=0;i<batches;i++)try(Connection c=db("migration","horizonte")){
   int last=((Number)one(c,"SELECT last_id FROM lab_checkpoint WHERE id=1 FOR UPDATE")).intValue();List<List<Object>> ids=q(c,"SELECT id FROM cliente WHERE id>? ORDER BY id LIMIT 25",last);
   if(ids.isEmpty()){c.commit();return;}int next=((Number)ids.get(ids.size()-1).get(0)).intValue();
   q(c,"UPDATE cliente SET email=contato_email WHERE id>? AND id<=?",last,next);q(c,"UPDATE lab_checkpoint SET last_id=? WHERE id=1",next);c.commit();log("limite_inicial="+last+" limite_final="+next+" linhas="+ids.size()+" checkpoint="+next);
  }
 }
 public static void main(String[]args){
  try{String[]a=Arrays.copyOfRange(args,1,args.length);switch(args[0]){
   case "catalogo":catalog(a);break;
   case "shard":shard(a.length>0?a[0]:"evidencias/execucoes/shard-java");break;
   case "replica":replica(a[0]);break;
   case "saga":saga(a[0],a[1],a.length>2?a[2]:"none");break;
   case "liberar":release(a[0]);snapshot(a[0]);break;
   case "snapshot":snapshot(a[0]);break;
   case "migration":migration(a[0],Integer.parseInt(a[1]));break;
   case "backfill":backfill(a.length>0?Integer.parseInt(a[0]):100);break;
   default:throw new IllegalArgumentException("Comando desconhecido");
  }}catch(Exception ex){log("ERRO "+ex);System.exit(ex.toString().contains("FALHA_INJETADA")?17:1);}
 }
}
