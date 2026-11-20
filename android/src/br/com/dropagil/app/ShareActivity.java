package br.com.dropagil.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import org.json.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
import android.widget.Toast;
import java.util.ArrayList;
import java.util.LinkedHashSet;

/** A transparent bridge from Android's share sheet to the upload service. */
public class ShareActivity extends Activity {
    private boolean dispatched;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        dispatched = state != null && state.getBoolean("dispatched");
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        state.putBoolean("dispatched", dispatched);
        super.onSaveInstanceState(state);
    }
    @Override protected void onPostResume() {
        super.onPostResume();
        ReceiverStartup.start(this);
        if (dispatched) { finish(); return; }
        dispatched = true;
        Intent source = getIntent();
        LinkedHashSet<Uri> selected = new LinkedHashSet<>();
        if (Intent.ACTION_SEND.equals(source.getAction())) {
            Uri uri = source.getParcelableExtra(Intent.EXTRA_STREAM);
            if (uri != null) selected.add(uri);
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(source.getAction())) {
            ArrayList<Uri> list = source.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
            if (list != null) selected.addAll(list);
        }
        if (source.getClipData() != null) for (int i=0;i<source.getClipData().getItemCount();i++) {
            Uri uri = source.getClipData().getItemAt(i).getUri();
            if (uri != null) selected.add(uri);
        }
        ArrayList<String> uris = new ArrayList<>();
        ClipData clip = null;
        for (Uri uri : selected) if ("content".equals(uri.getScheme())) {
            uris.add(uri.toString());
            if (clip == null) clip = ClipData.newRawUri("DropAgíl", uri);
            else clip.addItem(new ClipData.Item(uri));
        }
        if (uris.isEmpty()) {
            Toast.makeText(this,"Selecione fotos, vídeos ou arquivos para enviar.",Toast.LENGTH_LONG).show();
            finish(); return;
        }
        boolean configured = !getSharedPreferences("dropagil",0).getString("token", "").isEmpty();
        boolean notifications = Build.VERSION.SDK_INT < 33 || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
        try {
            if (configured && notifications) {
                Intent service = new Intent(this, TransferService.class).setAction("send")
                    .putStringArrayListExtra("uris",uris).putExtra("folder",false)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                service.setClipData(clip);
                chooseDestination(service);
                return;
            } else {
                Intent setup = new Intent(this, MainActivity.class).setAction(Intent.ACTION_SEND_MULTIPLE)
                    .putParcelableArrayListExtra(Intent.EXTRA_STREAM,new ArrayList<>(selected))
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                setup.setClipData(clip);
                startActivity(setup);
            }
        } catch (Exception e) {
            Toast.makeText(this,"Não foi possível iniciar o envio. Abra o DropAgíl e tente novamente.",Toast.LENGTH_LONG).show();
        }
        finish(); overridePendingTransition(0,0);
    }
    void chooseDestination(Intent service) {
        AlertDialog loading=new AlertDialog.Builder(this).setTitle("Enviar com DropAgíl").setMessage("Buscando dispositivos na rede…").setNegativeButton("Cancelar",(d,w)->finish()).create();
        loading.setOnCancelListener(d->finish());loading.show();
        new Thread(()->{
            JSONArray devices=new JSONArray();
            try{android.content.SharedPreferences p=getSharedPreferences("dropagil",0);devices=Api.request(p.getString("host",""),p.getString("token",""),"GET","/api/devices",null).getJSONArray("devices");}catch(Exception ignored){}
            final JSONArray found=devices;
            runOnUiThread(()->{
                if(isFinishing()||isDestroyed())return;loading.dismiss();
                String[] labels=new String[found.length()+1];labels[0]="Rede • todos os dispositivos";
                for(int i=0;i<found.length();i++)labels[i+1]=found.optJSONObject(i).optString("name");
                new AlertDialog.Builder(this).setTitle("Enviar para…").setItems(labels,(dialog,index)->{
                    service.putExtra("target",index==0?"":found.optJSONObject(index-1).optString("id"));
                    try{startForegroundService(service);}catch(Exception e){Toast.makeText(this,"Não foi possível iniciar o envio.",Toast.LENGTH_LONG).show();}
                    finish();overridePendingTransition(0,0);
                }).setNegativeButton("Cancelar",(d,w)->finish()).setOnCancelListener(d->finish()).show();
            });
        },"DropAgil-destinations").start();
    }

}
