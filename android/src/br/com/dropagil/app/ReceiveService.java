package br.com.dropagil.app;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import org.json.*;
import java.util.concurrent.*;

/** User-enabled LAN receiver. A persistent notification makes availability explicit. */
public class ReceiveService extends Service {
    public static volatile boolean running=false;
    final ScheduledExecutorService worker=Executors.newSingleThreadScheduledExecutor();
    String lastOffer="";
    SharedPreferences prefs(){return getSharedPreferences("dropagil",0);}
    JSONObject request(String method,String path,JSONObject data)throws Exception {
        return Api.request(prefs().getString("host",""),prefs().getString("token",""),method,path,data);
    }
    PendingIntent action(String action,int id){return PendingIntent.getForegroundService(this,id,new Intent(this,ReceiveService.class).setAction(action),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);}
    @Override public void onCreate(){
        super.onCreate();running=true;
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("receiver","Receber do DropAgíl",NotificationManager.IMPORTANCE_DEFAULT));
        Notification status=new Notification.Builder(this,"transfers").setSmallIcon(R.drawable.ic_notification).setContentTitle("DropAgíl disponível para receber")
            .setContentText("Dispositivos da sua rede podem enviar arquivos.").setOngoing(true)
            .setContentIntent(PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE))
            .addAction(new Notification.Action.Builder(null,"Desativar",action("stop",20)).build()).build();
        nm.createNotificationChannel(new NotificationChannel("transfers","Transferências DropAgíl",NotificationManager.IMPORTANCE_LOW));
        startForeground(10,status,ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        worker.scheduleWithFixedDelay(()->{try{poll();}catch(Exception ignored){}},0,3,TimeUnit.SECONDS);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent!=null&&"stop".equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}
        if(intent!=null&&("accept".equals(intent.getAction())||"reject".equals(intent.getAction()))){
            String action=intent.getAction();worker.execute(()->{try{respond(action);}catch(Exception e){notice("Não foi possível receber",e.getMessage());}});
        }
        return START_NOT_STICKY;
    }
    JSONObject downloads(){try{return new JSONObject(prefs().getString("incomingDownloads","{}"));}catch(Exception e){return new JSONObject();}}
    void save(JSONObject tracked){prefs().edit().putString("incomingDownloads",tracked.toString()).commit();}
    void poll()throws Exception {
        request("POST","/api/devices",new JSONObject().put("name",Build.MODEL));
        JSONObject tracked=downloads();DownloadManager dm=(DownloadManager)getSystemService(DOWNLOAD_SERVICE);
        java.util.ArrayList<String> finished=new java.util.ArrayList<>();
        java.util.Iterator<String> keys=tracked.keys();
        while(keys.hasNext()){
            String id=keys.next();long download=tracked.getLong(id);
            try(Cursor c=dm.query(new DownloadManager.Query().setFilterById(download))){
                if(c==null||!c.moveToFirst()){finished.add(id);continue;}
                int state=c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
                if(state==DownloadManager.STATUS_SUCCESSFUL){request("POST","/api/inbox/"+id,new JSONObject().put("action","received"));finished.add(id);}
                else if(state==DownloadManager.STATUS_FAILED){finished.add(id);notice("Download interrompido","O arquivo continua disponível para tentar novamente.");}
            }
        }
        for(String id:finished)tracked.remove(id);save(tracked);
        JSONArray inbox=request("GET","/api/inbox",null).getJSONArray("items");
        StringBuilder signature=new StringBuilder();int count=0;String sender="outro dispositivo",name="";
        for(int i=0;i<inbox.length();i++){JSONObject file=inbox.getJSONObject(i);if(tracked.has(file.getString("id")))continue;signature.append(file.getString("id"));count++;sender=file.optString("sender","outro dispositivo");name=file.getString("path");}
        if(count==0){getSystemService(NotificationManager.class).cancel(11);lastOffer="";return;}
        if(signature.toString().equals(lastOffer))return;lastOffer=signature.toString();
        Notification notification=new Notification.Builder(this,"receiver").setSmallIcon(R.drawable.ic_notification).setColor(0xff244d40)
            .setContentTitle(count==1?"Receber arquivo?":"Receber "+count+" arquivos?")
            .setContentText(count==1?sender+" • "+name:"Arquivos enviados para este celular. Salvar em Downloads/DropAgil?")
            .setStyle(new Notification.BigTextStyle().bigText(count==1?sender+" enviou "+name+". Salvar em Downloads/DropAgil?":"Aceitar baixa todos os arquivos pendentes para este celular."))
            .addAction(new Notification.Action.Builder(null,"Aceitar",action("accept",21)).build())
            .addAction(new Notification.Action.Builder(null,"Recusar",action("reject",22)).build()).setOnlyAlertOnce(true).build();
        getSystemService(NotificationManager.class).notify(11,notification);
    }
    void respond(String action)throws Exception {
        JSONArray inbox=request("GET","/api/inbox",null).getJSONArray("items");JSONObject tracked=downloads();
        for(int i=0;i<inbox.length();i++){
            JSONObject file=inbox.getJSONObject(i);String id=file.getString("id");if(tracked.has(id))continue;
            request("POST","/api/inbox/"+id,new JSONObject().put("action",action));
            if(action.equals("accept")){
                String path=file.getString("path");
                DownloadManager.Request download=new DownloadManager.Request(Uri.parse(prefs().getString("host","")+"/api/inbox/"+id+"/download"))
                    .setTitle(path).setDescription("Recebido pelo DropAgíl").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,"DropAgil/"+id.substring(0,8)+"/"+path)
                    .addRequestHeader("Authorization","Bearer "+prefs().getString("token",""));
                long task=((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(download);tracked.put(id,task);save(tracked);
            }
        }
        lastOffer="";getSystemService(NotificationManager.class).cancel(11);
    }
    void notice(String title,String detail){getSystemService(NotificationManager.class).notify(12,new Notification.Builder(this,"receiver").setSmallIcon(R.drawable.ic_notification).setContentTitle(title).setContentText(detail).setAutoCancel(true).build());}
    @Override public void onDestroy(){running=false;worker.shutdownNow();super.onDestroy();}
    @Override public IBinder onBind(Intent intent){return null;}
}
