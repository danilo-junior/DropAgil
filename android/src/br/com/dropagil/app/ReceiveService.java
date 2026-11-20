package br.com.dropagil.app;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.widget.RemoteViews;
import java.util.*;
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
    PendingIntent offerAction(String verb,int code,String[] ids){return PendingIntent.getForegroundService(this,code,new Intent(this,ReceiveService.class).setAction(verb).putExtra("ids",ids),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);}
    RemoteViews offerView(int layout,String title,String detail,String[] ids) {
        RemoteViews view=new RemoteViews(getPackageName(),layout);
        view.setTextViewText(R.id.offer_title,title);
        if(layout==R.layout.receive_expanded)view.setTextViewText(R.id.offer_detail,detail);
        view.setOnClickPendingIntent(R.id.offer_accept,offerAction("accept",21,ids));
        view.setOnClickPendingIntent(R.id.offer_reject,offerAction("reject",22,ids));
        return view;
    }
    @Override public void onCreate(){
        super.onCreate();running=true;
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("receiver_requests_v4","Receber do DropAgíl",NotificationManager.IMPORTANCE_HIGH));
        Notification status=new Notification.Builder(this,"transfers").setSmallIcon(R.drawable.ic_notification).setContentTitle("DropAgíl disponível para receber")
            .setContentText("Dispositivos da sua rede podem enviar arquivos.").setOngoing(true)
            .setContentIntent(PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE))
            .addAction(new Notification.Action.Builder(null,"Desativar",action("stop",20)).build()).build();
        nm.createNotificationChannel(new NotificationChannel("transfers","Transferências DropAgíl",NotificationManager.IMPORTANCE_LOW));
        startForeground(10,status,ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        worker.scheduleWithFixedDelay(()->{try{poll();}catch(Exception ignored){}},0,3,TimeUnit.SECONDS);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent!=null&&"stop".equals(intent.getAction())){prefs().edit().putBoolean("receivingEnabled",false).apply();stopSelf();return START_NOT_STICKY;}
        if(!ReceiverStartup.enabled(this)){stopSelf();return START_NOT_STICKY;}
        if(intent!=null&&("accept".equals(intent.getAction())||"reject".equals(intent.getAction()))){
            String action=intent.getAction();String[] ids=intent.getStringArrayExtra("ids");worker.execute(()->{try{respond(action,ids);}catch(Exception e){notice("Não foi possível receber",e.getMessage());}});
        }
        return START_STICKY;
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
        ArrayList<String> offeredIds=new ArrayList<>();StringBuilder signature=new StringBuilder();int count=0;String sender="outro dispositivo",name="";
        for(int i=0;i<inbox.length();i++){JSONObject file=inbox.getJSONObject(i);if(tracked.has(file.getString("id")))continue;signature.append(file.getString("id"));offeredIds.add(file.getString("id"));count++;sender=file.optString("sender","outro dispositivo");name=file.getString("path");}
        if(count==0){getSystemService(NotificationManager.class).cancel(11);lastOffer="";return;}
        if(signature.toString().equals(lastOffer))return;lastOffer=signature.toString();
        String title=count==1?"Receber arquivo?":"Receber "+count+" arquivos?";
        String detail=count==1?sender+" enviou "+name+". Salvar em Downloads/DropAgil?":"Os "+count+" arquivos serão salvos em Downloads/DropAgil.";
        String[] ids=offeredIds.toArray(new String[0]);
        PendingIntent open=PendingIntent.getActivity(this,23,new Intent(this,ReceiveActivity.class).putExtra("ids",ids).putExtra("detail",detail),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification notification=new Notification.Builder(this,"receiver_requests_v4").setSmallIcon(R.drawable.ic_notification).setColor(0xff244d40)
            .setContentTitle(title).setContentText(detail).setCategory(Notification.CATEGORY_STATUS)
            .setVisibility(Notification.VISIBILITY_PRIVATE).setContentIntent(open)
            .setStyle(new Notification.DecoratedCustomViewStyle())
            .setCustomContentView(offerView(R.layout.receive_compact,title,detail,ids))
            .setCustomBigContentView(offerView(R.layout.receive_expanded,title,detail,ids))
            .setCustomHeadsUpContentView(offerView(R.layout.receive_expanded,title,detail,ids))
            .setOnlyAlertOnce(true).build();
        getSystemService(NotificationManager.class).notify(11,notification);
    }
    void respond(String action,String[] ids)throws Exception {
        if(ids==null||ids.length==0)return;Set<String> allowed=new HashSet<>(Arrays.asList(ids));
        JSONArray inbox=request("GET","/api/inbox",null).getJSONArray("items");JSONObject tracked=downloads();
        for(int i=0;i<inbox.length();i++){
            JSONObject file=inbox.getJSONObject(i);String id=file.getString("id");if(tracked.has(id)||!allowed.contains(id))continue;
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
    void notice(String title,String detail){getSystemService(NotificationManager.class).notify(12,new Notification.Builder(this,"receiver_requests_v4").setSmallIcon(R.drawable.ic_notification).setContentTitle(title).setContentText(detail).setAutoCancel(true).build());}
    @Override public void onDestroy(){running=false;worker.shutdownNow();super.onDestroy();}
    @Override public IBinder onBind(Intent intent){return null;}
}
