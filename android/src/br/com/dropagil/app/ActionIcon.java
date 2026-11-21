package br.com.dropagil.app;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.drawable.Drawable;

/** Small, consistent outline icons for the app's compact actions. */
final class ActionIcon extends Drawable {
    private final String kind;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private int color;

    ActionIcon(String kind, int color) {
        this.kind = kind;
        this.color = color;
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(2);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
    }

    private void line(Canvas c,float x1,float y1,float x2,float y2){c.drawLine(x1,y1,x2,y2,paint);}
    private void path(Canvas c,float... points){Path p=new Path();p.moveTo(points[0],points[1]);for(int i=2;i<points.length;i+=2)p.lineTo(points[i],points[i+1]);c.drawPath(p,paint);}
    @Override public void draw(Canvas original) {
        Canvas c=original;int save=c.save();c.translate(getBounds().left,getBounds().top);
        c.scale(getBounds().width()/24f,getBounds().height()/24f);paint.setColor(color);
        switch(kind) {
            case "download": line(c,12,3,12,16);path(c,7,11,12,16,17,11);path(c,4,17,4,21,20,21,20,17);break;
            case "delete": path(c,4,7,20,7);path(c,9,4,15,4,16,7);path(c,6,7,7,21,17,21,18,7);line(c,10,11,10,17);line(c,14,11,14,17);break;
            case "folder": path(c,2,7,9,7,11,9,22,9,22,20,2,20,2,7);break;
            case "open": path(c,3,7,9,7,11,9,21,9,21,20,3,20,3,7);path(c,11,16,15,12,19,16);break;
            case "refresh": c.drawArc(4,4,20,20,35,285,false,paint);path(c,17,4,20,5,20,9);break;
            case "home": path(c,3,11,12,4,21,11);path(c,6,10,6,20,18,20,18,10);break;
            case "pause": c.drawRoundRect(6,4,10,20,1,1,paint);c.drawRoundRect(14,4,18,20,1,1,paint);break;
            case "play": path(c,7,4,19,12,7,20,7,4);break;
            case "cancel": c.drawCircle(12,12,9,paint);line(c,8,8,16,16);line(c,16,8,8,16);break;
            case "upload": path(c,4,17,4,21,20,21,20,17);line(c,12,17,12,4);path(c,7,9,12,4,17,9);break;
            case "web": c.drawCircle(12,12,9,paint);c.drawOval(8,3,16,21,paint);line(c,3,12,21,12);break;
            case "network": c.drawCircle(12,5,2,paint);c.drawCircle(5,18,2,paint);c.drawCircle(19,18,2,paint);line(c,11,7,6,16);line(c,13,7,18,16);line(c,7,18,17,18);break;
            case "phone": c.drawRoundRect(7,2,17,22,2,2,paint);line(c,10,18,14,18);break;
            case "settings": c.drawCircle(12,12,4,paint);c.drawCircle(12,12,9,paint);break;
            case "edit": path(c,4,17,4,20,7,20,19,8,16,5,4,17);line(c,14,7,17,10);break;
            case "bell": path(c,5,17,8,14,8,9,9,6,12,5,15,6,16,9,16,14,19,17,5,17);c.drawArc(10,17,14,21,0,180,false,paint);break;
            case "check": path(c,4,12,10,18,20,6);break;
            default: c.drawCircle(12,12,8,paint);
        }
        c.restoreToCount(save);
    }
    @Override public void setAlpha(int alpha){paint.setAlpha(alpha);invalidateSelf();}
    @Override public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);invalidateSelf();}
    @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    @Override public int getIntrinsicWidth(){return 24;}
    @Override public int getIntrinsicHeight(){return 24;}
}
