package br.com.dropagil.app;

import android.app.*;
import android.os.Bundle;
import android.content.Intent;
import android.widget.Toast;

/** One tap on the notification opens accessible, full-size confirmation controls. */
public class ReceiveActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        String[] ids=getIntent().getStringArrayExtra("ids");
        if(ids==null||ids.length==0){finish();return;}
        new AlertDialog.Builder(this).setTitle(ids.length==1?"Receber arquivo?":"Receber "+ids.length+" arquivos?")
            .setMessage(getIntent().getStringExtra("detail"))
            .setPositiveButton("Aceitar e baixar",(dialog,which)->respond("accept",ids))
            .setNegativeButton("Recusar",(dialog,which)->respond("reject",ids))
            .setNeutralButton("Depois",(dialog,which)->finish()).setOnCancelListener(dialog->finish()).show();
    }
    void respond(String action,String[] ids) {
        try{startForegroundService(new Intent(this,ReceiveService.class).setAction(action).putExtra("ids",ids));}
        catch(Exception e){Toast.makeText(this,"Abra o DropAgíl para receber os arquivos.",Toast.LENGTH_LONG).show();}
        finish();
    }
}
