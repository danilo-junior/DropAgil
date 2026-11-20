package br.com.dropagil.app;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.provider.DocumentsContract;
import android.provider.OpenableColumns;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

public class TransferService extends Service {
    static final Object LOCK=new Object();
    static JSONArray jobs=new JSONArray();
    static volatile boolean running=false;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private volatile boolean destroyed=false;
    private PowerManager.WakeLock wake;
    private long lastNotify=0;
    static String state(JSONObject j){return j.optString("state","queued");}
    static boolean terminal(JSONObject j){return state(j).equals("done")||state(j).equals("cancelled");}
    static JSONArray snapshot(Context ctx) {
        synchronized(LOCK){try{
            JSONArray source=new JSONArray(running?jobs.toString():ctx.getSharedPreferences("dropagil",0).getString("queue","[]"));
            JSONArray visible=new JSONArray();long now=System.currentTimeMillis();
            for(int i=0;i<source.length();i++){JSONObject job=source.getJSONObject(i);if(state(job).equals("done")&&now-job.optLong("finished",0)>=30000)continue;visible.put(job);}
            if(visible.length()!=source.length()){
                if(running)jobs=visible;
                ctx.getSharedPreferences("dropagil",0).edit().putString("queue",visible.toString()).apply();
            }
            return visible;
        }catch(Exception e){return new JSONArray();}}
    }
    void persist(){synchronized(LOCK){getSharedPreferences("dropagil",0).edit().putString("queue",jobs.toString()).commit();}}
    @Override public void onCreate(){
        super.onCreate();
        synchronized(LOCK){try{jobs=new JSONArray(getSharedPreferences("dropagil",0).getString("queue","[]"));for(int i=0;i<jobs.length();i++){JSONObject j=jobs.getJSONObject(i);if(state(j).equals("sending")||state(j).equals("scanning"))j.put("state","paused");}}catch(Exception e){jobs=new JSONArray();}}
        running=true;
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("transfers","Transferências DropAgíl",NotificationManager.IMPORTANCE_LOW));
        nm.cancel(8);
        startForeground(7,notification("Preparando transferência",0),ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"DropAgil:upload");wake.acquire(6*60*60*1000L);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null){stopSelf();return START_NOT_STICKY;}
        String action=intent.getAction();
        if("cancel".equals(action)||"pause".equals(action)||"resume".equals(action)){
            synchronized(LOCK){try{for(int i=0;i<jobs.length();i++){JSONObject j=jobs.getJSONObject(i);if(terminal(j))continue;if("cancel".equals(action)){j.put("state","cancelled").put("finished",System.currentTimeMillis());}else if("pause".equals(action))j.put("state","paused");else if(state(j).equals("paused")||state(j).equals("error"))j.put("state","queued").put("error","");}}catch(Exception ignored){}}
            persist();
        }else if("send".equals(action)){
            ArrayList<String> uris=intent.getStringArrayListExtra("uris"); boolean folder=intent.getBooleanExtra("folder",false);
            if(uris!=null&&!uris.isEmpty())synchronized(LOCK){try{
                JSONObject job=new JSONObject().put("name",folder?"Pasta":uris.size()==1?"Arquivo":uris.size()+" arquivos").put("target",intent.getStringExtra("target")==null?"":intent.getStringExtra("target")).put("sources",new JSONArray(uris)).put("folder",folder).put("host",getSharedPreferences("dropagil",0).getString("host","")).put("token",getSharedPreferences("dropagil",0).getString("token","")).put("state","queued").put("total",0L).put("sent",0L).put("started",System.currentTimeMillis());
                jobs.put(job);
            }catch(Exception ignored){}}
        }
        persist();worker.execute(()->drain(startId));return START_NOT_STICKY;
    }
    void drain(int startId){
        for(;;){
            JSONObject job=null;
            synchronized(LOCK){for(int i=0;i<jobs.length();i++){JSONObject j=jobs.optJSONObject(i);if(j!=null&&state(j).equals("queued")){job=j;try{job.put("state","sending");}catch(Exception ignored){}break;}}}
            if(job==null||destroyed)break;
            try{send(job);}catch(Exception e){synchronized(LOCK){try{if(!state(job).equals("cancelled")&&!state(job).equals("paused"))job.put("state","error").put("error",e.getMessage()==null?"Envio interrompido. Toque em Retomar.":e.getMessage());}catch(Exception ignored){}}}
            persist();
        }
        cleanupCancelled();
        if(!destroyed&&stopSelfResult(startId)){stopForeground(STOP_FOREGROUND_REMOVE);showOutcome();}
    }
    void enumerate(Uri uri,String prefix,boolean tree,JSONArray items,JSONObject job) throws Exception {
        if(destroyed||!state(job).equals("sending"))throw new InterruptedIOException("Envio pausado");
        Uri document=tree?DocumentsContract.buildDocumentUriUsingTree(uri,DocumentsContract.getTreeDocumentId(uri)):uri;
        try(Cursor cursor=getContentResolver().query(document,null,null,null,null)){
            if(cursor==null||!cursor.moveToFirst())throw new Exception("Não foi possível ler o arquivo selecionado.");
            int ni=cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME),si=cursor.getColumnIndex(OpenableColumns.SIZE),mi=cursor.getColumnIndex(DocumentsContract.Document.COLUMN_MIME_TYPE);
            String name=ni>=0?cursor.getString(ni):"arquivo";
            if(name.contains("/")||name.contains("\\"))throw new Exception("Nome inválido: "+name);
            String path=prefix+name;
            String mime=mi>=0?cursor.getString(mi):getContentResolver().getType(document);
            if(DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)){
                if(prefix.isEmpty())job.put("name",name);
                String id=DocumentsContract.getDocumentId(document);
                Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(uri,id);
                try(Cursor child=getContentResolver().query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID},null,null,null)){
                    if(child==null)throw new Exception("Não foi possível ler a pasta.");
                    while(child.moveToNext())enumerate(DocumentsContract.buildDocumentUriUsingTree(uri,child.getString(0)),path+"/",false,items,job);
                }
            }else{
                long size=si>=0&&!cursor.isNull(si)?cursor.getLong(si):-1;
                if(size<0)try(android.content.res.AssetFileDescriptor afd=getContentResolver().openAssetFileDescriptor(document,"r")){if(afd!=null)size=afd.getLength();}
                if(size<0)throw new Exception("O app de origem não informou o tamanho. Salve o arquivo no celular e selecione pelo app Arquivos.");
                items.put(new JSONObject().put("uri",document.toString()).put("path",path).put("size",size).put("offset",0L).put("done",false));
            }
        }
    }
    void send(JSONObject job) throws Exception {
        if(!job.has("items")){
            JSONArray items=new JSONArray(), sources=job.getJSONArray("sources");
            for(int i=0;i<sources.length();i++)enumerate(Uri.parse(sources.getString(i)),"",job.optBoolean("folder"),items,job);
            if(items.length()==0)throw new Exception("A pasta não contém arquivos.");
            long total=0;for(int i=0;i<items.length();i++)total+=items.getJSONObject(i).getLong("size");
            synchronized(LOCK){job.put("items",items).put("total",total);if(!job.optBoolean("folder")&&items.length()==1)job.put("name",items.getJSONObject(0).getString("path"));}
            persist();
        }
        updateNotification(job);
        JSONArray items=job.getJSONArray("items");String host=job.getString("host"),token=job.getString("token");
        for(int i=0;i<items.length();i++){
            if(destroyed||!state(job).equals("sending"))return;
            JSONObject item=items.getJSONObject(i);if(item.optBoolean("done"))continue;
            String path=item.getString("path");long size=item.getLong("size");
            JSONObject upload=Api.request(host,token,"POST","/api/uploads",new JSONObject().put("target",job.optString("target","")).put("path",path).put("size",size).put("id",item.optString("id","")).put("fingerprint","android:"+item.getString("uri")+":"+size+":"+job.getLong("started")));
            synchronized(LOCK){item.put("id",upload.getString("id")).put("offset",upload.getLong("offset"));}persist();
            try(InputStream in=getContentResolver().openInputStream(Uri.parse(item.getString("uri")))){
                if(in==null)throw new Exception("Sem acesso ao arquivo. Compartilhe ou selecione novamente.");
                long offset=item.getLong("offset"),skip=offset;
                byte[] buffer=new byte[8*1024*1024];
                while(skip>0){long n=in.skip(skip);if(n<=0){int read=in.read(buffer,0,(int)Math.min(skip,buffer.length));if(read<0)throw new EOFException("Arquivo de origem mudou.");n=read;}skip-=n;}
                while(offset<size){
                    if(destroyed||!state(job).equals("sending"))return;
                    int need=(int)Math.min(buffer.length,size-offset),read=0;
                    while(read<need){int n=in.read(buffer,read,need-read);if(n<0)throw new EOFException("Arquivo incompleto na origem.");read+=n;}
                    byte[] block=need==buffer.length?buffer:Arrays.copyOf(buffer,need);
                    long started=System.currentTimeMillis();JSONObject reply=null;
                    for(int attempt=0;attempt<4;attempt++){
                        try{reply=Api.request(host,token,"PUT","/api/uploads/"+item.getString("id"),block,offset,null);break;}
                        catch(Exception error){if(destroyed||!state(job).equals("sending"))return;if(attempt==3)throw error;Thread.sleep(1000L*(attempt+1));JSONObject actual=Api.request(host,token,"GET","/api/uploads/"+item.getString("id"),null);if(actual.getLong("offset")==offset+need){reply=actual;break;}if(actual.getLong("offset")!=offset)throw new Exception("Posição alterada. Retome o envio.");}
                    }
                    offset=reply.getLong("offset");long sent=0;
                    synchronized(LOCK){item.put("offset",offset);for(int k=0;k<items.length();k++)sent+=items.getJSONObject(k).optLong("offset");job.put("sent",sent).put("speed",need*1000.0/Math.max(1,System.currentTimeMillis()-started));}
                    persist();updateNotification(job);
                }
            }
            if(destroyed||!state(job).equals("sending"))return;
            Api.request(host,token,"POST","/api/uploads/"+item.getString("id")+"/complete",new JSONObject());
            synchronized(LOCK){item.put("done",true);}persist();
        }
        synchronized(LOCK){if(state(job).equals("sending"))job.put("state","done").put("finished",System.currentTimeMillis());}
        persist();
    }
    void cleanupCancelled(){
        ArrayList<JSONObject> cancelled=new ArrayList<>();
        synchronized(LOCK){for(int i=0;i<jobs.length();i++){JSONObject job=jobs.optJSONObject(i);if(job!=null&&state(job).equals("cancelled"))cancelled.add(job);}}
        for(JSONObject job:cancelled){JSONArray items=job.optJSONArray("items");if(items==null)continue;for(int j=0;j<items.length();j++){JSONObject item=items.optJSONObject(j);if(item!=null&&item.has("id")&&!item.optBoolean("done"))try{Api.request(job.getString("host"),job.getString("token"),"DELETE","/api/uploads/"+item.getString("id"),null);synchronized(LOCK){item.remove("id");}}catch(Exception ignored){}}}
        persist();
    }
    Notification notification(String title,int percent){
        Intent open=new Intent(this,MainActivity.class);
        Intent cancel=new Intent(this,TransferService.class).setAction("cancel");
        return new Notification.Builder(this,"transfers").setSmallIcon(R.drawable.ic_notification).setColor(0xff244d40).setContentTitle("DropAgíl · "+title).setContentText(percent+"% · toque para abrir a fila").setProgress(100,percent,false).setOnlyAlertOnce(true).setOngoing(true).setContentIntent(PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).addAction(new Notification.Action.Builder(null,"Cancelar tudo",PendingIntent.getService(this,1,cancel,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build()).build();
    }
    void showOutcome() {
        JSONObject latest=null; int errors=0, paused=0;
        synchronized(LOCK) {
            for(int i=0;i<jobs.length();i++) {
                JSONObject job=jobs.optJSONObject(i);if(job==null)continue;
                latest=job;if(state(job).equals("error"))errors++;if(state(job).equals("paused"))paused++;
            }
        }
        if(latest==null)return;
        String title=errors>0?"Envio não concluído":paused>0?"Envio pausado":state(latest).equals("cancelled")?"Fila cancelada":"Envio concluído";
        String detail=errors>0?"Abra a fila para ver o erro e retomar.":paused>0?"Abra a fila para retomar o envio.":latest.optString("name")+(state(latest).equals("done")?(latest.optString("target","").isEmpty()?" • disponível na rede":" • aguardando aceite no destino"):"");
        Notification result=new Notification.Builder(this,"transfers").setSmallIcon(R.drawable.ic_notification).setColor(0xff244d40)
            .setContentTitle("DropAgíl • "+title).setContentText(detail).setStyle(new Notification.BigTextStyle().bigText(detail))
            .setTimeoutAfter(30000).setAutoCancel(true).setContentIntent(PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build();
        getSystemService(NotificationManager.class).notify(8,result);
    }
    void updateNotification(JSONObject job){if(System.currentTimeMillis()-lastNotify<400)return;lastNotify=System.currentTimeMillis();long total=job.optLong("total");int percent=total==0?0:(int)Math.min(99,job.optLong("sent")*100.0/total);getSystemService(NotificationManager.class).notify(7,notification(job.optString("name"),percent));}
    @Override public void onTimeout(int startId,int fgsType){synchronized(LOCK){try{for(int i=0;i<jobs.length();i++){JSONObject j=jobs.getJSONObject(i);if(!terminal(j))j.put("state","paused");}}catch(Exception ignored){}}persist();showOutcome();stopSelf();}
    @Override public void onDestroy(){destroyed=true;running=false;if(wake!=null&&wake.isHeld())wake.release();worker.shutdownNow();persist();super.onDestroy();}
    @Override public IBinder onBind(Intent intent){return null;}
}
