package br.com.dropagil.app;

import android.Manifest;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Build;

public class ReceiverStartup extends BroadcastReceiver {
    static boolean enabled(Context ctx) {
        SharedPreferences prefs=ctx.getSharedPreferences("dropagil",0);
        return prefs.getBoolean("receivingEnabled",true) && !prefs.getString("token","").isEmpty()
            && (Build.VERSION.SDK_INT<33 || ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED);
    }
    static void start(Context ctx) {
        if(!enabled(ctx)||ReceiveService.running)return;
        try{ctx.startForegroundService(new Intent(ctx,ReceiveService.class));}catch(IllegalStateException|SecurityException ignored){}
    }
    @Override public void onReceive(Context context,Intent intent) {
        if(Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())||Intent.ACTION_MY_PACKAGE_REPLACED.equals(intent.getAction()))start(context);
    }
}
