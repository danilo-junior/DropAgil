package br.com.dropagil.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.os.Build;
import android.widget.Toast;

/** Handles the Android installer result and any system-required confirmation. */
public final class UpdateReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirmation == null) return;
            confirmation.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try { context.startActivity(confirmation); }
            catch (Exception error) { notifyConfirmation(context, confirmation); }
        } else if (status != PackageInstaller.STATUS_SUCCESS) {
            String detail = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
            Toast.makeText(context, "Atualização não instalada" + (detail == null ? "." : ": " + detail), Toast.LENGTH_LONG).show();
        }
    }

    private void notifyConfirmation(Context context, Intent confirmation) {
        NotificationManager manager = (NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
        String channel = "dropagil-updates";
        if (Build.VERSION.SDK_INT >= 26)
            manager.createNotificationChannel(new NotificationChannel(channel, "Atualizações do DropAgíl", NotificationManager.IMPORTANCE_HIGH));
        PendingIntent action = PendingIntent.getActivity(context, 71, confirmation,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification notice = new Notification.Builder(context, channel)
            .setSmallIcon(br.com.dropagil.app.R.drawable.ic_notification)
            .setContentTitle("Atualização pronta")
            .setContentText("Toque para concluir a instalação do DropAgíl.")
            .setContentIntent(action).setAutoCancel(true).build();
        manager.notify(71, notice);
    }
}
