package br.com.dropagil.app;

import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageInstaller;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

/** Checks the paired computer on every app opening and installs newer signed APKs. */
final class AutoUpdater {
    private static final ExecutorService worker = Executors.newSingleThreadExecutor();
    private static boolean checking;

    static synchronized void check(MainActivity activity) {
        String host = activity.prefs().getString("host", "");
        String token = activity.prefs().getString("token", "");
        if (checking || host.isEmpty() || token.isEmpty()) return;
        checking = true;
        worker.execute(() -> {
            try {
                JSONObject info = Api.request(host, token, "GET", "/api/android-update", (JSONObject)null);
                long version = info.getLong("versionCode");
                long current = activity.getPackageManager().getPackageInfo(activity.getPackageName(), 0).getLongVersionCode();
                if (version <= current) { finished(); return; }
                activity.runOnUiThread(() -> prepare(activity, host, token, info, version));
            } catch (Exception ignored) {
                // The computer may be offline. Try again the next time the app opens.
                finished();
            }
        });
    }

    private static synchronized void finished() { checking = false; }

    private static void prepare(MainActivity activity, String host, String token, JSONObject info, long version) {
        if (activity.isFinishing() || activity.isDestroyed() || activity.attemptedUpdateVersion == version) {
            finished(); return;
        }
        if (!activity.getPackageManager().canRequestPackageInstalls()) {
            if (!activity.askedInstallPermission) {
                activity.askedInstallPermission = true;
                new AlertDialog.Builder(activity).setTitle("Atualização disponível")
                    .setMessage("Para receber atualizações pela sua rede, permita que o DropAgíl instale novas versões. O Android pode pedir uma confirmação na primeira vez.")
                    .setNegativeButton("Depois", (dialog, which) -> finished())
                    .setPositiveButton("Permitir", (dialog, which) -> {
                        finished();
                        Intent settings = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                            Uri.parse("package:" + activity.getPackageName()));
                        activity.startActivityForResult(settings, 11);
                    }).setOnCancelListener(dialog -> finished()).show();
            } else finished();
            return;
        }
        activity.attemptedUpdateVersion = version;
        worker.execute(() -> {
            try {
                downloadAndInstall(activity, host, token, info, version);
                activity.message("Atualização baixada. Instalando pelo Android…");
            } catch (Exception error) {
                activity.runOnUiThread(() -> activity.attemptedUpdateVersion = 0);
                activity.message("Não foi possível atualizar: " + error.getMessage());
            } finally { finished(); }
        });
    }

    private static void downloadAndInstall(MainActivity activity, String host, String token,
                                            JSONObject info, long version) throws Exception {
        long expectedSize = info.getLong("size");
        String expectedHash = info.getString("sha256");
        if (expectedSize <= 0 || expectedSize > 250L * 1024 * 1024 ||
            !expectedHash.matches("[0-9a-fA-F]{64}") || !"/api/android-apk".equals(info.getString("url")))
            throw new Exception("A central enviou metadados inválidos.");
        File apk = File.createTempFile("dropagil-update-", ".apk", activity.getCacheDir());
        try {
            HttpURLConnection connection = (HttpURLConnection)new URL(host + "/api/android-apk").openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(120000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            long received = 0;
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try {
                if (connection.getResponseCode() != 200) throw new Exception("O APK não está disponível na central.");
                try (InputStream input = connection.getInputStream(); OutputStream output = new FileOutputStream(apk)) {
                    byte[] buffer = new byte[65536]; int count;
                    while ((count = input.read(buffer)) != -1) {
                        received += count;
                        if (received > expectedSize) throw new Exception("Tamanho do APK inesperado.");
                        digest.update(buffer, 0, count);
                        output.write(buffer, 0, count);
                    }
                }
            } finally { connection.disconnect(); }
            if (received != expectedSize || !hex(digest.digest()).equalsIgnoreCase(expectedHash))
                throw new Exception("A atualização baixada não passou na verificação.");
            verifyPackage(activity, apk, version);
            install(activity, apk, expectedSize);
        } finally { apk.delete(); }
    }

    private static void verifyPackage(MainActivity activity, File apk, long version) throws Exception {
        PackageManager manager = activity.getPackageManager();
        PackageInfo archive = manager.getPackageArchiveInfo(apk.getAbsolutePath(), PackageManager.GET_SIGNING_CERTIFICATES);
        if (archive == null || !activity.getPackageName().equals(archive.packageName) ||
            archive.getLongVersionCode() != version || archive.signingInfo == null)
            throw new Exception("O APK não corresponde ao DropAgíl esperado.");
        Signature[] signers = archive.signingInfo.getApkContentsSigners();
        if (signers == null || signers.length == 0) throw new Exception("APK sem assinatura válida.");
        for (Signature signer : signers) {
            byte[] certificate = MessageDigest.getInstance("SHA-256").digest(signer.toByteArray());
            if (!manager.hasSigningCertificate(activity.getPackageName(), certificate, PackageManager.CERT_INPUT_SHA256))
                throw new Exception("A assinatura da atualização é diferente da instalação atual.");
        }
    }

    private static void install(MainActivity activity, File apk, long size) throws Exception {
        PackageInstaller installer = activity.getPackageManager().getPackageInstaller();
        PackageInstaller.SessionParams params = new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        params.setAppPackageName(activity.getPackageName());
        params.setSize(size);
        if (Build.VERSION.SDK_INT >= 31)
            params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED);
        int sessionId = installer.createSession(params);
        PackageInstaller.Session session = installer.openSession(sessionId);
        boolean committed = false;
        try {
            try (InputStream input = new FileInputStream(apk);
                 OutputStream output = session.openWrite("base.apk", 0, size)) {
                byte[] buffer = new byte[65536]; int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                session.fsync(output);
            }
            Intent result = new Intent(activity, UpdateReceiver.class).setAction("br.com.dropagil.app.UPDATE_RESULT");
            int flags = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 31 ? PendingIntent.FLAG_MUTABLE : 0);
            PendingIntent callback = PendingIntent.getBroadcast(activity, sessionId, result, flags);
            session.commit(callback.getIntentSender());
            committed = true;
        } finally {
            session.close();
            if (!committed) installer.abandonSession(sessionId);
        }
    }

    private static String hex(byte[] bytes) {
        char[] digits = "0123456789abcdef".toCharArray();
        char[] out = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            out[2*i] = digits[(bytes[i] >> 4) & 15];
            out[2*i+1] = digits[bytes[i] & 15];
        }
        return new String(out);
    }
}
