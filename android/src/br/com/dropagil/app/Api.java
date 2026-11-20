package br.com.dropagil.app;

import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

final class Api {
    static String validate(String value) throws Exception {
        String normalized = value.trim();
        if (!normalized.startsWith("http://")) normalized = "http://" + normalized;
        URI uri = new URI(normalized);
        String host = uri.getHost();
        if (!"http".equals(uri.getScheme()) || host == null || uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null || (uri.getPath()!=null && !uri.getPath().isEmpty() && !uri.getPath().equals("/"))) throw new Exception("Use o endereço local do computador, com http:// e a porta.");
        InetAddress ip = InetAddress.getByName(host);
        if (!ip.isSiteLocalAddress() && !ip.isLoopbackAddress()) throw new Exception("O DropAgíl aceita somente endereços da rede local.");
        return "http://" + host + ":" + (uri.getPort() == -1 ? 8787 : uri.getPort());
    }
    static JSONObject request(String host,String token,String method,String path,JSONObject json) throws Exception {
        byte[] data = json == null ? null : json.toString().getBytes(StandardCharsets.UTF_8);
        return request(host,token,method,path,data,-1,null);
    }
    static JSONObject request(String host,String token,String method,String path,byte[] data,long offset,String cookie) throws Exception {
        HttpURLConnection connection = (HttpURLConnection)new URL(host + path).openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(15000); connection.setReadTimeout(120000); connection.setRequestMethod(method);
        if (token!=null && !token.isEmpty()) connection.setRequestProperty("Authorization","Bearer " + token);
        if (cookie!=null) connection.setRequestProperty("Cookie",cookie);
        if (offset>=0) connection.setRequestProperty("Upload-Offset",Long.toString(offset));
        try {
            if (data!=null) {
                connection.setDoOutput(true); connection.setFixedLengthStreamingMode(data.length);
                connection.setRequestProperty("Content-Type",offset>=0 ? "application/octet-stream" : "application/json");
                try(OutputStream out=connection.getOutputStream()) {out.write(data);}
            }
            int code=connection.getResponseCode();
            InputStream input=code>=400 ? connection.getErrorStream():connection.getInputStream();
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();
            if(input!=null) try(InputStream in=input){ byte[] buffer=new byte[8192]; int n; while((n=in.read(buffer))!=-1) { if(bytes.size()>8*1024*1024) throw new Exception("Resposta da central muito grande."); bytes.write(buffer,0,n); } }
            JSONObject result = bytes.size()>0 ? new JSONObject(bytes.toString("UTF-8")) : new JSONObject();
            if(code>=400) throw new Exception(result.optString("error","Falha HTTP " + code));
            String setCookie=connection.getHeaderField("Set-Cookie");
            if(setCookie!=null) result.put("cookie",setCookie.split(";")[0]);
            return result;
        } finally {connection.disconnect();}
    }
    static String pair(String host,String pin,String name) throws Exception {
        JSONObject credentials=new JSONObject().put("pin",pin).put("name",name);
        JSONObject login=request(host,"","POST","/api/login",credentials);
        byte[] body=new JSONObject().put("name",name).toString().getBytes(StandardCharsets.UTF_8);
        return request(host,"","POST","/api/pair",body,-1,login.getString("cookie")).getString("token");
    }
}
