package br.com.dropagil.app;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.util.*;
import java.util.concurrent.*;

public class MainActivity extends Activity {
    final ExecutorService io=Executors.newSingleThreadExecutor();
    final Handler timer=new Handler(Looper.getMainLooper());
    LinearLayout content,queueView,fileView; EditText address,pin; TextView connection;
    String folder=""; ArrayList<String> pendingUris=new ArrayList<>(); boolean pendingFolder=false; ClipData pendingClip;
    long attemptedUpdateVersion=0; boolean askedInstallPermission=false;
    static final int GREEN=0xff244d40, MUTED=0xff687b64;
    android.content.SharedPreferences prefs(){return getSharedPreferences("dropagil",0);}
    int dp(int n){return (int)(n*getResources().getDisplayMetrics().density);}
    TextView text(String value,int size,int color){TextView view=new TextView(this);view.setText(value);view.setTextSize(size);view.setTextColor(color);view.setPadding(0,dp(6),0,dp(6));return view;}
    ImageButton iconButton(String label,String icon,Runnable action){
        ImageButton button=new ImageButton(this);button.setImageDrawable(new ActionIcon(icon,GREEN));
        button.setScaleType(ImageView.ScaleType.FIT_CENTER);button.setPadding(dp(12),dp(12),dp(12),dp(12));
        button.setBackground(rounded(0xffedf2e7,14));button.setContentDescription(label);button.setTooltipText(label);
        button.setOnClickListener(v->action.run());return button;
    }
    LinearLayout.LayoutParams iconSpace(){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dp(48),dp(48));p.leftMargin=dp(6);return p;}
    void message(String value){runOnUiThread(()->Toast.makeText(this,value,Toast.LENGTH_LONG).show());}
    String appVersion(){try{return getPackageManager().getPackageInfo(getPackageName(),0).versionName;}catch(Exception ignored){return "";}}
    @Override public void onCreate(Bundle state){super.onCreate(state);build();if(state==null)receive(getIntent());else{ArrayList<String> saved=state.getStringArrayList("pending");if(saved!=null)pendingUris=saved;pendingFolder=state.getBoolean("pendingFolder");}if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},9);timer.post(tick);}
    @Override protected void onSaveInstanceState(Bundle state){state.putStringArrayList("pending",pendingUris);state.putBoolean("pendingFolder",pendingFolder);super.onSaveInstanceState(state);}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);receive(intent);}
    LinearLayout transferPage, filesPage, configPage;
    ImageButton[] tabs;
    Spinner destination; ArrayList<String> destinationIds=new ArrayList<>();
    ImageButton receiving;
    int currentTab = 0;
    android.graphics.drawable.GradientDrawable rounded(int color, int radius) {
        android.graphics.drawable.GradientDrawable shape = new android.graphics.drawable.GradientDrawable();
        shape.setColor(color); shape.setCornerRadius(dp(radius)); return shape;
    }
    LinearLayout column() { LinearLayout v=new LinearLayout(this); v.setOrientation(LinearLayout.VERTICAL); return v; }
    LinearLayout card(LinearLayout parent) {
        LinearLayout v=column(); v.setPadding(dp(18),dp(14),dp(18),dp(14)); v.setBackground(rounded(Color.WHITE,20));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2); lp.bottomMargin=dp(16); parent.addView(v,lp); return v;
    }
    void title(LinearLayout parent,String label,String detail) {
        TextView heading=text(label,25,GREEN);heading.setTypeface(null,android.graphics.Typeface.BOLD);parent.addView(heading);
        parent.addView(text(detail,14,MUTED));
    }
    void showTab(int tab) {
        currentTab=tab; transferPage.setVisibility(tab==0?View.VISIBLE:View.GONE);
        filesPage.setVisibility(tab==1?View.VISIBLE:View.GONE);configPage.setVisibility(tab==2?View.VISIBLE:View.GONE);
        for(int i=0;i<tabs.length;i++) {tabs[i].setBackground(rounded(i==tab?0xffddf5b0:0xffedf2e7,14));tabs[i].setSelected(i==tab);}
        if(tab==1)loadFiles();
    }
    void openPage() {
        String host=prefs().getString("host","");
        if(host.isEmpty()){showTab(2);message("Conecte ao computador primeiro.");return;}
        try { startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(host))); }
        catch(Exception e){message("Nenhum navegador disponível para abrir a página.");}
    }
    void build(){
        LinearLayout shell=column();shell.setBackgroundColor(0xfff5f7f2);setContentView(shell);
        shell.setOnApplyWindowInsetsListener((v,insets)->{if(Build.VERSION.SDK_INT>=30){android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.ime());v.setPadding(bars.left,bars.top,bars.right,bars.bottom);}else v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});
        LinearLayout brand=new LinearLayout(this);brand.setGravity(Gravity.CENTER_VERTICAL);brand.setPadding(dp(20),dp(12),dp(20),dp(12));brand.setBackgroundColor(0xff173f35);
        ImageView logo=new ImageView(this);logo.setImageResource(br.com.dropagil.app.R.drawable.ic_dropagil);brand.addView(logo,new LinearLayout.LayoutParams(dp(40),dp(40)));
        LinearLayout brandWords=column();brandWords.setPadding(dp(10),0,0,0);TextView wordmark=text("DropAgíl",23,Color.WHITE);wordmark.setTypeface(null,android.graphics.Typeface.BOLD);brandWords.addView(wordmark);TextView tagline=text("PERTINHO. RAPIDINHO.",10,0xffddf5b0);tagline.setLetterSpacing(.12f);brandWords.addView(tagline);brand.addView(brandWords,new LinearLayout.LayoutParams(0,-2,1));
        ImageButton web=iconButton("Abrir página","web",this::openPage);web.setImageDrawable(new ActionIcon("web",0xffddf5b0));web.setBackground(rounded(0xff386253,14));brand.addView(web,new LinearLayout.LayoutParams(dp(48),dp(48)));shell.addView(brand);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);shell.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        content=column();content.setPadding(dp(20),dp(12),dp(20),dp(24));scroll.addView(content);
        transferPage=column();filesPage=column();configPage=column();content.addView(transferPage);content.addView(filesPage);content.addView(configPage);
        LinearLayout hero=card(transferPage);hero.setBackground(rounded(GREEN,24));
        hero.addView(text("SEUS ARQUIVOS. SUA REDE.",11,0xffddf5b0));TextView headline=text("De perto, mais rápido.",28,Color.WHITE);headline.setTypeface(null,android.graphics.Typeface.BOLD);hero.addView(headline);
        hero.addView(text("Fotos, vídeos e pastas direto para o computador.",15,0xffe3eadf));
        hero.addView(text("ENVIAR PARA",11,0xffddf5b0));
        destination=new Spinner(this);destination.setBackground(rounded(0xffedf2e7,12));hero.addView(destination,new LinearLayout.LayoutParams(-1,dp(48)));
        destination.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onNothingSelected(android.widget.AdapterView<?> p){} public void onItemSelected(android.widget.AdapterView<?> p,View v,int pos,long id){if(pos<destinationIds.size())prefs().edit().putString("target",destinationIds.get(pos)).apply();}});
        LinearLayout heroActions=new LinearLayout(this);heroActions.setGravity(Gravity.END);heroActions.setPadding(0,dp(12),0,0);
        heroActions.addView(iconButton("Atualizar dispositivos","refresh",this::loadDestinations),iconSpace());loadDestinations();
        ImageButton send=iconButton("Enviar arquivos","upload",this::pickFiles);send.setBackground(rounded(0xffddf5b0,14));heroActions.addView(send,iconSpace());
        ImageButton folders=iconButton("Enviar uma pasta","folder",this::pickFolder);folders.setImageDrawable(new ActionIcon("folder",Color.WHITE));folders.setBackground(rounded(0xff386253,14));heroActions.addView(folders,iconSpace());hero.addView(heroActions);
        title(transferPage,"Transferências","Concluídos somem após 30 segundos. Os arquivos são mantidos.");
        LinearLayout controls=new LinearLayout(this);
        controls.setGravity(Gravity.END);controls.addView(iconButton("Pausar envios","pause",()->control("pause")),iconSpace());controls.addView(iconButton("Retomar envios","play",()->control("resume")),iconSpace());
        ImageButton cancel=iconButton("Cancelar tudo","cancel",()->control("cancel"));cancel.setImageDrawable(new ActionIcon("cancel",0xffa34536));controls.addView(cancel,iconSpace());transferPage.addView(controls);
        queueView=column();transferPage.addView(queueView);
        transferPage.addView(text("Dica: na galeria, toque em Compartilhar → DropAgíl. O envio aparece na notificação.",13,MUTED));
        receiving=iconButton("Receber arquivos neste celular","bell",()->{
            if(ReceiveService.running){prefs().edit().putBoolean("receivingEnabled",false).apply();stopService(new Intent(this,ReceiveService.class));updateReceiving();}
            else if(prefs().getString("token","").isEmpty()){showTab(2);message("Conecte ao computador primeiro.");}
            else if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},9);message("Permita notificações e ative o recebimento novamente.");}
            else {prefs().edit().putBoolean("receivingEnabled",true).apply();startForegroundService(new Intent(this,ReceiveService.class));updateReceiving();message("Disponível na rede. Confirme os arquivos pela notificação.");}
        });LinearLayout receiveRow=new LinearLayout(this);receiveRow.setGravity(Gravity.CENTER_VERTICAL);receiveRow.addView(text("Recebimento neste celular",14,GREEN),new LinearLayout.LayoutParams(0,-2,1));receiveRow.addView(receiving,iconSpace());transferPage.addView(receiveRow);updateReceiving();
        title(filesPage,"Arquivos da rede","Baixe ou libere espaço no computador.");
        LinearLayout fileButtons=new LinearLayout(this);fileButtons.setGravity(Gravity.END);fileButtons.addView(iconButton("Atualizar arquivos","refresh",this::loadFiles),iconSpace());fileButtons.addView(iconButton("Voltar à raiz","home",()->{folder="";loadFiles();}),iconSpace());filesPage.addView(fileButtons);
        fileView=column();filesPage.addView(fileView);
        title(configPage,"Sua conexão","Configure uma vez. Compartilhe quando quiser.");
        LinearLayout config=card(configPage);
        connection=text(prefs().getString("token","").isEmpty()?"Vamos conectar seu computador":"Computador salvo • "+prefs().getString("host",""),15,GREEN);config.addView(connection);
        config.addView(text("Endereço do computador",13,MUTED));address=new EditText(this);address.setTextSize(16);address.setSingleLine(true);address.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);address.setHint("http://192.168.1.100:8787");address.setText(prefs().getString("host",""));config.addView(address);
        config.addView(text("Código de acesso",13,MUTED));pin=new EditText(this);pin.setTextSize(16);pin.setSingleLine(true);pin.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);pin.setHint("Os 6 números da página do computador");config.addView(pin);
        LinearLayout connectRow=new LinearLayout(this);connectRow.setGravity(Gravity.CENTER_VERTICAL);connectRow.addView(text("Conectar computador",14,GREEN),new LinearLayout.LayoutParams(0,-2,1));ImageButton connect=iconButton("Conectar computador","network",this::pair);connect.setImageDrawable(new ActionIcon("network",Color.WHITE));connect.setBackground(rounded(GREEN,14));connectRow.addView(connect,iconSpace());config.addView(connectRow);
        configPage.addView(text("O celular pode usar Wi-Fi e o computador, cabo. Ambos precisam estar no mesmo roteador. Encontre o endereço e o código em Conectar celular, no computador.",15,MUTED));
        LinearLayout configActions=new LinearLayout(this);configActions.setGravity(Gravity.END);configActions.addView(iconButton("Renomear dispositivos da rede","edit",this::renameDevices),iconSpace());
        configActions.addView(iconButton("Permissões de notificação","settings",()->startActivity(new Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(android.provider.Settings.EXTRA_APP_PACKAGE,getPackageName()))),iconSpace());configPage.addView(configActions);
        configPage.addView(text("DropAgíl "+appVersion()+" • Feito para ficar por perto.\nOs arquivos trafegam pela rede local via HTTP.",12,MUTED));
        LinearLayout navigation=new LinearLayout(this);navigation.setPadding(dp(12),dp(6),dp(12),dp(8));
        tabs=new ImageButton[]{iconButton("Transferir","upload",()->showTab(0)),iconButton("Arquivos","folder",()->showTab(1)),iconButton("Conexão","network",()->showTab(2))};
        for(ImageButton tab:tabs){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(52),1);p.setMargins(dp(4),0,dp(4),0);navigation.addView(tab,p);}shell.addView(navigation);
        showTab(prefs().getString("token","").isEmpty()?2:0);
    }
    @Override protected void onResume(){super.onResume();ReceiverStartup.start(this);AutoUpdater.check(this);}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants){super.onRequestPermissionsResult(request,permissions,grants);ReceiverStartup.start(this);}
    void renameDevices() {
        if(prefs().getString("token","").isEmpty()){showTab(2);return;}
        io.execute(()->{try{
            JSONObject result=Api.request(prefs().getString("host",""),prefs().getString("token",""),"GET","/api/devices",null);
            JSONArray list=new JSONArray();if(result.optJSONObject("current")!=null)list.put(result.getJSONObject("current"));JSONArray others=result.getJSONArray("devices");for(int i=0;i<others.length();i++)list.put(others.getJSONObject(i));
            runOnUiThread(()->{
                if(list.length()==0){message("Os dispositivos ainda estão se conectando. Tente novamente.");return;}
                String[] names=new String[list.length()];for(int i=0;i<list.length();i++)names[i]=list.optJSONObject(i).optString("name")+" · "+list.optJSONObject(i).optString("id").substring(26);
                new AlertDialog.Builder(this).setTitle("Renomear dispositivo").setItems(names,(dialog,index)->{
                    JSONObject device=list.optJSONObject(index);EditText input=new EditText(this);input.setSingleLine(true);input.setText(device.optString("name"));input.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(50)});
                    new AlertDialog.Builder(this).setTitle("Nome na rede").setView(input).setNegativeButton("Cancelar",null).setPositiveButton("Salvar",(d,w)->{
                        String name=input.getText().toString().trim();
                        io.execute(()->{try{Api.request(prefs().getString("host",""),prefs().getString("token",""),"POST","/api/devices/"+device.optString("id")+"/rename",new JSONObject().put("name",name));runOnUiThread(()->{loadDestinations();message("Nome atualizado em todos os dispositivos.");});}catch(Exception e){message(e.getMessage());}});
                    }).show();
                }).show();
            });
        }catch(Exception e){message(e.getMessage());}});
    }
    void loadDestinations() {
        if(prefs().getString("token","").isEmpty()) {setDestinations(new JSONArray());return;}
        io.execute(()->{try{JSONObject response=Api.request(prefs().getString("host",""),prefs().getString("token",""),"GET","/api/devices",null);runOnUiThread(()->setDestinations(response.optJSONArray("devices")));}catch(Exception e){message(e.getMessage());}});
    }
    void setDestinations(JSONArray devices) {
        String saved=prefs().getString("target","");destinationIds.clear();destinationIds.add("");ArrayList<String> names=new ArrayList<>();names.add("Rede • todos os dispositivos");int selected=0;
        if(devices!=null)for(int i=0;i<devices.length();i++){JSONObject device=devices.optJSONObject(i);if(device==null)continue;destinationIds.add(device.optString("id"));names.add(device.optString("name"));if(saved.equals(device.optString("id")))selected=names.size()-1;}
        if(!saved.isEmpty()&&selected==0){destinationIds.add(saved);names.add("Destino salvo • indisponível agora");selected=names.size()-1;}
        ArrayAdapter<String> adapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,names);adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);destination.setAdapter(adapter);destination.setSelection(selected);
    }
    void pair(){String value=address.getText().toString(),code=pin.getText().toString();connection.setText("Conectando…");io.execute(()->{try{String host=Api.validate(value),token=Api.pair(host,code,Build.MODEL);prefs().edit().putString("host",host).putString("token",token).apply();runOnUiThread(()->{connection.setText("Conectado a "+host);pin.setText("");ReceiverStartup.start(this);showTab(0);loadDestinations();loadFiles();AutoUpdater.check(this);if(!pendingUris.isEmpty())sendPending();});}catch(Exception e){runOnUiThread(()->connection.setText(e.getMessage()));}});}
    void receive(Intent intent){
        if(intent==null)return;
        String action=intent.getAction();
        if(!Intent.ACTION_SEND.equals(action)&&!Intent.ACTION_SEND_MULTIPLE.equals(action))return;
        ArrayList<Uri> uris=new ArrayList<>();
        if(Intent.ACTION_SEND.equals(action)){Uri uri=intent.getParcelableExtra(Intent.EXTRA_STREAM);if(uri!=null)uris.add(uri);}else{ArrayList<Uri> list=intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);if(list!=null)uris.addAll(list);}
        if(uris.isEmpty()&&intent.getClipData()!=null)for(int i=0;i<intent.getClipData().getItemCount();i++){Uri uri=intent.getClipData().getItemAt(i).getUri();if(uri!=null)uris.add(uri);}
        pendingUris.clear();for(Uri uri:uris)if("content".equals(uri.getScheme()))pendingUris.add(uri.toString());
        pendingFolder=false;pendingClip=intent.getClipData();
        if(pendingUris.isEmpty()){message("Compartilhe arquivos pelo app Arquivos, Galeria ou outro aplicativo.");return;}
        sendPending();
    }
    void pickFiles(){Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);startActivityForResult(intent,1);}
    void pickFolder(){startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE),2);}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==11){if(getPackageManager().canRequestPackageInstalls())AutoUpdater.check(this);return;}if(result!=RESULT_OK||data==null)return;pendingUris.clear();ArrayList<Uri> uris=new ArrayList<>();if(data.getClipData()!=null)for(int i=0;i<data.getClipData().getItemCount();i++)uris.add(data.getClipData().getItemAt(i).getUri());else if(data.getData()!=null)uris.add(data.getData());for(Uri uri:uris){try{getContentResolver().takePersistableUriPermission(uri,data.getFlags()&Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(Exception ignored){}pendingUris.add(uri.toString());}pendingFolder=request==2;pendingClip=data.getClipData();sendPending();}
    void sendPending(){
        if(pendingUris.isEmpty())return;
        if(prefs().getString("token","").isEmpty()){showTab(2);message("Informe o endereço e código uma vez para conectar. Os arquivos selecionados estão aguardando.");return;}
        Intent upload=new Intent(this,TransferService.class).setAction("send").putStringArrayListExtra("uris",new ArrayList<>(pendingUris)).putExtra("folder",pendingFolder).putExtra("target",prefs().getString("target","")).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        ClipData clip=ClipData.newRawUri("Arquivos DropAgíl",Uri.parse(pendingUris.get(0)));for(int i=1;i<pendingUris.size();i++)clip.addItem(new ClipData.Item(Uri.parse(pendingUris.get(i))));upload.setClipData(clip);
        try{startForegroundService(upload);pendingUris.clear();setIntent(new Intent(this,MainActivity.class).setAction(Intent.ACTION_MAIN));message("Adicionado à fila do DropAgíl.");}catch(Exception e){message(e.getMessage());}
    }
    void control(String action){Intent command=new Intent(this,TransferService.class).setAction(action);try{if(TransferService.running)startService(command);else startForegroundService(command);}catch(Exception e){message(e.getMessage());}}
    String size(long bytes){if(bytes>=1024L*1024*1024)return String.format(Locale.getDefault(),"%.1f GB",bytes/(1024.0*1024*1024));if(bytes>=1024*1024)return String.format(Locale.getDefault(),"%.1f MB",bytes/(1024.0*1024));return bytes/1024+" KB";}
    String duration(long ms){long s=Math.max(0,ms/1000);return String.format(Locale.getDefault(),"%02d:%02d:%02d",s/3600,(s/60)%60,s%60);}
    void renderQueue(){JSONArray jobs=TransferService.snapshot(this);queueView.removeAllViews();boolean any=false;for(int i=0;i<jobs.length();i++){JSONObject job=jobs.optJSONObject(i);if(job==null||job.optString("state").equals("cancelled"))continue;any=true;String state=job.optString("state");long total=job.optLong("total"),sent=job.optLong("sent");int percent=state.equals("done")?100:total==0?0:(int)Math.min(99,sent*100.0/total);LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(dp(12),dp(8),dp(12),dp(12));card.setBackground(rounded(Color.WHITE,18));LinearLayout.LayoutParams layout=new LinearLayout.LayoutParams(-1,-2);layout.bottomMargin=dp(10);queueView.addView(card,layout);card.addView(text(job.optString("name"),17,GREEN));ProgressBar bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);bar.setMax(100);bar.setProgress(percent);bar.setProgressTintList(android.content.res.ColorStateList.valueOf(GREEN));bar.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(0xffe5ecdd));card.addView(bar);String label=state.equals("done")?"Concluído":state.equals("sending")?"Enviando":state.equals("paused")?"Pausado":state.equals("error")?"Falha":"Na fila";long end=job.optLong("finished",System.currentTimeMillis());double speed=job.optDouble("speed",0);String estimate=speed>0&&state.equals("sending")?" · cerca de "+(long)((total-sent)/speed)+" s restantes":"";card.addView(text(percent+"% · "+size(sent)+" / "+size(total)+" · "+label+"\nTempo: "+duration(end-job.optLong("started",end))+estimate,13,MUTED));if(state.equals("error"))card.addView(text(job.optString("error"),13,0xffa04d35));}if(!any){LinearLayout empty=card(queueView);empty.addView(text("Tudo pronto para enviar",18,GREEN));empty.addView(text("Escolha arquivos acima ou compartilhe direto da galeria.",14,MUTED));}}
    void updateReceiving(){if(receiving==null)return;boolean active=ReceiveService.running;receiving.setContentDescription(active?"Desativar recebimento":"Ativar recebimento");receiving.setTooltipText(receiving.getContentDescription());receiving.setImageDrawable(new ActionIcon(active?"check":"bell",active?Color.WHITE:GREEN));receiving.setBackground(rounded(active?GREEN:0xffedf2e7,14));}
    final Runnable tick=new Runnable(){public void run(){updateReceiving();if(currentTab==0)renderQueue();timer.postDelayed(this,1000);}};
    void loadFiles(){if(prefs().getString("token","").isEmpty())return;String path=folder;io.execute(()->{try{JSONObject response=Api.request(prefs().getString("host",""),prefs().getString("token",""),"GET","/api/files?path="+Uri.encode(path),null);runOnUiThread(()->renderFiles(response.optJSONArray("items"),path));}catch(Exception e){message(e.getMessage());}});}
    void renderFiles(JSONArray files,String path) {
        if(!folder.equals(path))return;
        fileView.removeAllViews();fileView.addView(text(path.isEmpty()?"Todos os arquivos":path,14,MUTED));
        if(files==null||files.length()==0){LinearLayout empty=card(fileView);empty.addView(text("Espaço para o que vem",18,GREEN));empty.addView(text("Os arquivos aparecem aqui após o envio.",14,MUTED));return;}
        for(int i=0;i<files.length();i++) {
            JSONObject file=files.optJSONObject(i);if(file==null)continue;
            LinearLayout row=card(fileView);boolean dir=file.optBoolean("directory");
            row.addView(text(dir?"PASTA":"ARQUIVO • "+size(file.optLong("size")),11,MUTED));
            LinearLayout fileLine=new LinearLayout(this);fileLine.setGravity(Gravity.CENTER_VERTICAL);
            TextView name=text(file.optString("name"),17,GREEN);name.setTypeface(null,android.graphics.Typeface.BOLD);name.setMaxLines(2);name.setEllipsize(android.text.TextUtils.TruncateAt.END);
            fileLine.addView(name,new LinearLayout.LayoutParams(0,-2,1));
            if(dir)fileLine.addView(iconButton("Abrir pasta "+file.optString("name"),"open",()->{folder=file.optString("path");loadFiles();}),iconSpace());
            fileLine.addView(iconButton((dir?"Baixar ZIP de ":"Baixar ")+file.optString("name"),"download",()->download(file)),iconSpace());
            ImageButton remove=iconButton("Apagar "+file.optString("name"),"delete",()->confirmDelete(file));remove.setImageDrawable(new ActionIcon("delete",0xffa34536));fileLine.addView(remove,iconSpace());row.addView(fileLine);
        }
    }
    void confirmDelete(JSONObject file) {
        String detail=file.optBoolean("directory")?"A pasta e todos os arquivos dentro dela serão apagados":"Este arquivo será apagado";
        new AlertDialog.Builder(this).setTitle("Apagar “"+file.optString("name")+"”?")
            .setMessage(detail+" permanentemente do computador e da rede. A cópia original no dispositivo que enviou será mantida.")
            .setNegativeButton("Manter",null).setPositiveButton("Apagar",(dialog,which)->{
                io.execute(()->{try{
                    Api.request(prefs().getString("host",""),prefs().getString("token",""),"DELETE","/api/files",new JSONObject().put("path",file.optString("path")));
                    runOnUiThread(()->{message("Apagado da rede.");loadFiles();});
                }catch(Exception e){message(e.getMessage());}});
            }).show();
    }
    void download(JSONObject file){try{boolean directory=file.optBoolean("directory");String name=file.optString("name")+(directory?".zip":"");String url=prefs().getString("host","")+(directory?"/api/zip?path=":"/api/download?path=")+Uri.encode(file.optString("path"));DownloadManager.Request request=new DownloadManager.Request(Uri.parse(url)).setTitle(name).setDescription("DropAgíl · rede local").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setAllowedOverMetered(true).setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,name).addRequestHeader("Authorization","Bearer "+prefs().getString("token",""));((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(request);message("Download iniciado. Acompanhe nas notificações; o arquivo vai para Downloads.");}catch(Exception e){message(e.getMessage());}}
    @Override protected void onDestroy(){timer.removeCallbacks(tick);io.shutdownNow();super.onDestroy();}
}
