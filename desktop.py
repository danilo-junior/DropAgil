"""DropAgíl para Windows: bandeja, envio pelo Explorer e início automático."""
import argparse
import ctypes
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from runtime_paths import BASE, RESOURCES, FROZEN, desktop_command, server_command, child_environment
sys.path.insert(0,str(BASE / 'vendor'))
from desktop_client import DesktopQueue, LocalAPI
from desktop_receiver import DesktopReceiver
from desktop_pages import DesktopPages

PORT = 8788
STATE = BASE / '.dropagil'
TOKEN = STATE / 'desktop-token'
AUTOSTART_DISABLED = STATE / 'startup-disabled'
PYTHONW = str(Path(sys.executable).with_name('pythonw.exe'))
CREATE_NO_WINDOW = 0x08000000


def ipc(action, data=None):
    token = TOKEN.read_text('utf-8')
    request = urllib.request.Request(f'http://127.0.0.1:{PORT}/{action}',json.dumps(data or {}).encode(),{'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=4) as response:
        return json.load(response)


def ensure_server():
    try:
        api = LocalAPI()
        api.request('POST','/api/local-login',{})
        return
    except Exception:
        pass
    log = (BASE / 'server.log').open('ab')
    subprocess.Popen(server_command(),cwd=BASE,env=child_environment(),stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=CREATE_NO_WINDOW)
    log.close()
    for _ in range(40):
        try:
            LocalAPI().request('POST','/api/local-login',{})
            return
        except Exception:
            time.sleep(.25)
    raise RuntimeError('Não foi possível iniciar a central na porta 8787.')


def install(remove=False):
    import winreg
    STATE.mkdir(exist_ok=True)
    command = subprocess.list2cmdline(desktop_command('--background'))
    run = r'Software\Microsoft\Windows\CurrentVersion\Run'
    parents = [r'Software\Classes\*\shell',r'Software\Classes\Directory\shell']
    # Remove only our exact keys, including the old single-choice entry.
    for parent in parents:
        for suffix in ('DropAgil','DropAgilNetwork','DropAgilDevice'):
            keypath=parent+'\\'+suffix
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,keypath+r'\command') as key:
                    value,_=winreg.QueryValueEx(key,'')
                if str(BASE / 'desktop.py') not in value and str(BASE / 'DropAgil.exe') not in value:continue
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER,keypath+r'\command')
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER,keypath)
            except FileNotFoundError:pass
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,run) as key:
        if remove:
            try:
                value,_=winreg.QueryValueEx(key,'DropAgil')
                if str(BASE / 'desktop.py') in value or str(BASE / 'DropAgil.exe') in value:winreg.DeleteValue(key,'DropAgil')
            except FileNotFoundError:pass
        else:winreg.SetValueEx(key,'DropAgil',0,winreg.REG_SZ,command)
    if not remove:
        for parent in parents:
            for suffix,label,flag in [('DropAgilNetwork','DropAgíl — Enviar para a rede','--send-network'),('DropAgilDevice','DropAgíl — Enviar para dispositivo…','--send-device')]:
                keypath=parent+'\\'+suffix
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,keypath) as key:
                    winreg.SetValueEx(key,'',0,winreg.REG_SZ,label)
                    winreg.SetValueEx(key,'Icon',0,winreg.REG_SZ,str(Path(__file__).resolve().parent/'public/dropagil.ico') if not FROZEN else sys.executable)
                    winreg.SetValueEx(key,'MultiSelectModel',0,winreg.REG_SZ,'Player')
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,keypath+r'\command') as key:
                    winreg.SetValueEx(key,'',0,winreg.REG_SZ,subprocess.list2cmdline(desktop_command(flag))+' "%1"')
    ctypes.windll.shell32.SHChangeNotify(0x08000000,0,None,None)
    if remove:
        AUTOSTART_DISABLED.write_text('disabled by user', encoding='utf-8')
    else:
        AUTOSTART_DISABLED.unlink(missing_ok=True)


def ensure_autostart():
    """Register startup on the first normal launch, unless the user removed it."""
    if AUTOSTART_DISABLED.exists():
        return
    import winreg
    expected = subprocess.list2cmdline(desktop_command('--background'))
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            actual, _ = winreg.QueryValueEx(key, 'DropAgil')
    except FileNotFoundError:
        actual = None
    if actual != expected:
        install()



def run_desktop(background=False):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import Image, ImageDraw
    import pystray
    STATE.mkdir(exist_ok=True)
    mutex_api = ctypes.windll.kernel32.CreateMutexW
    mutex_api.restype = wintypes.HANDLE
    mutex = mutex_api(None,False,'Local\\DropAgil.Desktop.8788')
    if ctypes.windll.kernel32.GetLastError() == 183:
        if not background:
            ipc('show')
        return
    try:
        ensure_autostart()
    except OSError as error:
        with (STATE / 'startup-error.log').open('a', encoding='utf-8') as out:
            out.write(str(error) + '\n')
    ensure_server()
    token = secrets.token_urlsafe(32)
    TOKEN.write_text(token,'utf-8')
    jobs = DesktopQueue()
    events = queue.Queue()
    receiver = DesktopReceiver(LocalAPI(),events)

    class IPCHandler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            self.connection.settimeout(5)
            if self.client_address[0] != '127.0.0.1' or self.headers.get('Origin') or not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                self.send_error(403); return
            try:
                size = int(self.headers.get('Content-Length','0'))
                if size < 0 or size > 256*1024: raise ValueError()
                data = json.loads(self.rfile.read(size))
                if self.path in ('/send','/send-network','/send-device'):
                    paths = data.get('paths',[])
                    if not isinstance(paths,list) or not all(isinstance(p,str) for p in paths): raise ValueError()
                    events.put((self.path[1:],paths))
                elif self.path in ('/show','/files','/choose-files','/choose-folder','/exit'):
                    events.put(self.path[1:])
                elif self.path in ('/cancel','/pause','/resume'):
                    jobs.control(self.path[1:])
                elif self.path not in ('/ping','/status'):
                    self.send_error(404); return
                payload = json.dumps({'ok':True,'jobs':jobs.snapshot() if self.path == '/status' else []}).encode()
                self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
            except Exception:
                self.send_error(400)
    bridge = ThreadingHTTPServer(('127.0.0.1',PORT),IPCHandler)
    threading.Thread(target=bridge.serve_forever,daemon=True).start()
    root = tk.Tk()
    if background: root.withdraw()
    root.title('DropAgíl — Desktop')
    root.geometry('980x740')
    root.configure(bg='#f5f7f2')
    root.minsize(800,640)
    root.protocol('WM_DELETE_WINDOW',root.withdraw)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame',background='#f5f7f2')
    style.configure('TLabel',background='#f5f7f2',foreground='#244d40',font=('Segoe UI',10))
    style.configure('TButton',font=('Segoe UI',10),padding=(12,9),background='#edf2e7',foreground='#244d40',borderwidth=0)
    style.map('TButton',background=[('active','#dde8d3')])
    style.configure('Primary.TButton',background='#244d40',foreground='white')
    style.map('Primary.TButton',background=[('active','#386253')])
    style.configure('Danger.TButton',foreground='#a34536')
    style.configure('TProgressbar',background='#7d9b55',troughcolor='#e6ecde',borderwidth=0,thickness=7)
    style.configure('Treeview',font=('Segoe UI',10),rowheight=38,background='white',fieldbackground='white',foreground='#24342e',borderwidth=0)
    style.configure('Treeview.Heading',font=('Segoe UI',9,'bold'),background='#edf2e7',foreground='#687b64',padding=(8,8),borderwidth=0)
    style.map('Treeview',background=[('selected','#ddf5b0')],foreground=[('selected','#173f35')])
    brand=tk.Frame(root,bg='#173f35',padx=24,pady=18);brand.pack(fill='x')
    mark=tk.Canvas(brand,width=48,height=48,bg='#173f35',highlightthickness=0);mark.pack(side='left',padx=(0,14))
    mark.create_oval(5,13,34,42,outline='#ddf5b0',width=5)
    mark.create_line(34,5,34,40,fill='#ddf5b0',width=5,capstyle='round')
    mark.create_oval(38,4,44,10,fill='#ddf5b0',outline='')
    labels=tk.Frame(brand,bg='#173f35');labels.pack(side='left')
    tk.Label(labels,text='DropAgíl',font=('Segoe UI',21,'bold'),fg='white',bg='#173f35').pack(anchor='w')
    tk.Label(labels,text='PERTINHO. RAPIDINHO.',font=('Segoe UI',9,'bold'),fg='#ddf5b0',bg='#173f35').pack(anchor='w')
    ttk.Button(brand,text='Abrir página ↗',command=lambda:webbrowser.open('http://localhost:8787/')).pack(side='right')
    tk.Label(brand,text='●  REDE LOCAL',font=('Segoe UI',9,'bold'),fg='#ddf5b0',bg='#173f35').pack(side='right',padx=(0,20))
    tk.Frame(root,bg='#ddf5b0',height=4).pack(fill='x')
    style.configure('TNotebook',background='#f5f7f2',borderwidth=0)
    style.configure('TNotebook.Tab',font=('Segoe UI',11),padding=(22,12))
    tabs=ttk.Notebook(root);tabs.pack(fill='both',expand=True,padx=16,pady=16)
    frame=ttk.Frame(tabs,padding=(24,18));tabs.add(frame,text='Transferências')
    ttk.Label(frame,text='01  /  SEUS ENVIOS',font=('Segoe UI',9,'bold'),foreground='#7d9b55').pack(anchor='w',pady=(0,8))
    heading = ttk.Label(frame,text='Tudo pronto para enviar',font=('Segoe UI',16,'bold')); heading.pack(anchor='w')
    subtitle = ttk.Label(frame,text='Escolha arquivos ou use o botão direito no Explorador.',wraplength=590); subtitle.pack(anchor='w',pady=(5,12))
    progress = ttk.Progressbar(frame,maximum=100); progress.pack(fill='x')
    timing = ttk.Label(frame,text='0%',foreground='#687b64'); timing.pack(anchor='w',pady=(7,14))
    destination_row=ttk.Frame(frame);destination_row.pack(fill='x',pady=(0,12))
    ttk.Label(destination_row,text='Enviar para:').pack(side='left',padx=(0,10))
    destination=ttk.Combobox(destination_row,state='readonly',values=['Rede • todos os dispositivos']);destination.current(0);destination.pack(side='left',fill='x',expand=True)
    destination_ids=['']
    def refresh_destinations():
        selected=destination_ids[destination.current()] if 0 <= destination.current() < len(destination_ids) else ''
        devices=list(receiver.devices)
        ids=['']+[device['id'] for device in devices]
        labels=['Rede • todos os dispositivos']+[device['name'] for device in devices]
        if selected and selected not in ids:
            ids.append(selected);labels.append('Destino salvo • indisponível agora')
        destination_ids[:]=ids;destination['values']=labels;destination.current(ids.index(selected))
    ttk.Button(destination_row,text='Atualizar',command=refresh_destinations).pack(side='right',padx=(6,0))
    def enqueue(paths):
        jobs.add(paths,target=destination_ids[max(0,destination.current())]);root.deiconify()
    shell_paths=[]
    shell_timer=None
    def queue_device_share(paths):
        nonlocal shell_timer
        shell_paths.extend(paths)
        if shell_timer is not None:root.after_cancel(shell_timer)
        def open_choice():
            nonlocal shell_timer
            chosen=list(dict.fromkeys(shell_paths));shell_paths.clear();shell_timer=None
            share_prompt(chosen)
        shell_timer=root.after(350,open_choice)
    def queue_shell_share(paths,target):
        try:
            if not jobs.add(paths,target=target):
                tray.notify('Os itens selecionados não estão disponíveis para envio.','Falha no envio')
        except Exception as error:
            tray.notify(str(error) or 'Não foi possível iniciar a transferência.','Falha no envio')
    def compact_popup(title,width=440,height=240):
        popup=tk.Toplevel(root)
        popup.withdraw();popup.title(title);popup.configure(bg='#f5f7f2');popup.resizable(False,False)
        popup.iconbitmap(str(STATE / 'dropagil.ico'))
        rect=wintypes.RECT()
        foreground=ctypes.windll.user32.GetForegroundWindow()
        if foreground and ctypes.windll.user32.GetWindowRect(foreground,ctypes.byref(rect)):
            x=(rect.left+rect.right-width)//2;y=(rect.top+rect.bottom-height)//2
        else:
            x=(root.winfo_screenwidth()-width)//2;y=(root.winfo_screenheight()-height)//2
        popup.geometry(f'{width}x{height}{x:+d}{y:+d}')
        popup.attributes('-topmost',True)
        return popup
    def reveal_popup(popup):
        popup.deiconify();popup.lift();popup.grab_set();popup.focus_force()
    def share_prompt(paths):
        refresh_destinations()
        popup=compact_popup('Enviar com DropAgíl',440,225)
        panel=ttk.Frame(popup,padding=22);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='Enviar para…',font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(panel,text=f'{len(paths)} item(ns) selecionado(s)').pack(anchor='w',pady=8)
        choices=list(destination_ids[1:])
        if not choices:
            ttk.Label(panel,text='Nenhum dispositivo disponível. Abra o DropAgíl no celular.').pack(pady=12)
            ttk.Button(panel,text='Tentar novamente',command=lambda:(popup.destroy(),share_prompt(paths))).pack()
            reveal_popup(popup)
            return
        select=ttk.Combobox(panel,state='readonly',values=list(destination['values'])[1:],width=42);select.current(0);select.pack(fill='x',pady=10)
        def send():
            queue_shell_share(paths,choices[max(0,select.current())])
            popup.destroy()
        ttk.Button(panel,text='Enviar',style='Primary.TButton',command=send).pack(side='right')
        ttk.Button(panel,text='Cancelar',command=popup.destroy).pack(side='right',padx=6)
        reveal_popup(popup)
    def offer_receive(files):
        popup=compact_popup('Receber pelo DropAgíl?',460,310)
        panel=ttk.Frame(popup,padding=22);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='Receber arquivos?',font=('Segoe UI',17,'bold')).pack(anchor='w')
        names='\n'.join(item['path'][:70]+('…' if len(item['path'])>70 else '') for item in files[:3])
        if len(files)>3:names+=f'\n… e mais {len(files)-3} arquivo(s)'
        ttk.Label(panel,text=f'{len(files)} arquivo(s) chegando de outro dispositivo.',foreground='#687b64').pack(anchor='w',pady=(8,10))
        ttk.Label(panel,text=names,wraplength=410).pack(anchor='w')
        ttk.Label(panel,text='Serão salvos em Downloads/DropAgil.',foreground='#687b64').pack(anchor='w',pady=(10,12))
        buttons=ttk.Frame(panel);buttons.pack(side='bottom',fill='x')
        def respond(accept):
            popup.destroy();receiver.respond(files,accept)
        ttk.Button(buttons,text='Aceitar',style='Primary.TButton',command=lambda:respond(True)).pack(side='right')
        ttk.Button(buttons,text='Recusar',command=lambda:respond(False)).pack(side='right',padx=8)
        popup.protocol('WM_DELETE_WINDOW',lambda:respond(False))
        reveal_popup(popup)
    table_frame=ttk.Frame(frame);table_frame.pack(fill='both',expand=True)
    table = ttk.Treeview(table_frame,columns=('progress','state','time'),show='tree headings',height=4)
    table.heading('#0',text='Arquivo / pasta'); table.column('#0',width=250,minwidth=150)
    table.heading('progress',text='%'); table.column('progress',width=45,stretch=False,anchor='center')
    table.heading('state',text='Situação'); table.column('state',width=105,stretch=False)
    table.heading('time',text='Tempo'); table.column('time',width=70,stretch=False,anchor='center')
    scrollbar=ttk.Scrollbar(table_frame,orient='vertical',command=table.yview);table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right',fill='y');table.pack(side='left',fill='both',expand=True)
    actions = ttk.Frame(frame); actions.pack(fill='x',pady=(14,0))
    def choose_files():
        paths = filedialog.askopenfilenames(parent=root,title='Enviar arquivos via DropAgíl')
        if paths: enqueue(paths)
    def choose_folder():
        path = filedialog.askdirectory(parent=root,title='Enviar pasta via DropAgíl')
        if path: enqueue([path])
    ttk.Button(actions,text='Enviar arquivos',style='Primary.TButton',command=choose_files).pack(side='left')
    ttk.Button(actions,text='Enviar pasta',command=choose_folder).pack(side='left',padx=4)
    ttk.Button(actions,text='Pausar',command=lambda:jobs.control('pause')).pack(side='left')
    ttk.Button(actions,text='Retomar',command=lambda:jobs.control('resume')).pack(side='left',padx=4)
    footer = ttk.Frame(frame); footer.pack(fill='x',pady=(8,0))
    ttk.Button(footer,text='Cancelar tudo',style='Danger.TButton',command=lambda:jobs.control('cancel')).pack(side='left')
    ttk.Button(footer,text='Arquivos da rede',command=lambda:pages.show(pages.files)).pack(side='left',padx=6)
    ttk.Button(footer,text='Esconder',command=root.withdraw).pack(side='right')
    pages=DesktopPages(root,tabs,LocalAPI(),events,install,BASE/'Recebidos')
    image = Image.new('RGBA',(64,64),'#173f35'); draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3,3,60,60),radius=14,fill='#173f35')
    draw.ellipse((14,22,44,51),outline='#ddf5b0',width=7);draw.line((41,12,41,47),fill='#ddf5b0',width=7)
    image.save(STATE / 'dropagil.ico',sizes=[(16,16),(32,32),(64,64)])
    root.iconbitmap(str(STATE / 'dropagil.ico'))
    def event(name): return lambda *_:events.put(name)
    tray = pystray.Icon('DropAgil',image,'DropAgíl — central de arquivos',pystray.Menu(
        pystray.MenuItem('Transferências',event('show'),default=True),
        pystray.MenuItem('Enviar arquivos…',event('choose-files')),
        pystray.MenuItem('Enviar pasta…',event('choose-folder')),
        pystray.MenuItem('Abrir página do DropAgíl',event('page')),
        pystray.MenuItem('Arquivos da rede',event('files')),
        pystray.MenuItem('Abrir pasta Recebidos',event('received')),
        pystray.MenuItem('Conectar celular',event('connect')),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Cancelar toda a fila',lambda *_:jobs.control('cancel')),
        pystray.MenuItem('Sair da bandeja',event('exit'))))
    tray.run_detached()
    seen_terminal = {j['id'] for j in jobs.snapshot() if j['state'] in ('done','error')}
    def tick():
        try:
            while True:
                name = events.get_nowait()
                if isinstance(name,tuple):
                    kind,payload=name
                    if kind=='ui': payload()
                    elif kind=='send-network': queue_shell_share(payload,'')
                    elif kind in ('send','send-device'):
                        root.withdraw();queue_device_share(payload)
                    elif kind=='incoming':
                        tray.notify(f'{len(payload)} arquivo(s) aguardando sua confirmação.','Receber arquivos?')
                        offer_receive(payload)
                    elif kind=='received': tray.notify(Path(payload).name+' salvo em Downloads/DropAgil.','Arquivo recebido')
                    elif kind=='receive-error': tray.notify(payload,'Falha no recebimento')
                    continue
                if name == 'show': root.deiconify(); root.lift()
                elif name == 'choose-files': choose_files()
                elif name == 'choose-folder': choose_folder()
                elif name == 'page': webbrowser.open('http://localhost:8787/')
                elif name == 'files': root.deiconify();pages.show(pages.files)
                elif name == 'connect': root.deiconify();pages.show(pages.connection)
                elif name == 'received': os.startfile(BASE / 'Recebidos')
                elif name == 'exit':
                    pages.close(); receiver.close(); jobs.control('pause'); jobs.close(); bridge.shutdown(); tray.stop(); root.destroy(); return
        except queue.Empty: pass
        jobs.prune_finished()
        snapshot = jobs.snapshot()
        shown = [j for j in snapshot if j['state'] != 'cancelled']
        active = [j for j in shown if j['state'] not in ('done','cancelled')]
        batches = {j.get('batch',j['id']) for j in active} if active else ({shown[-1].get('batch',shown[-1]['id'])} if shown else set())
        summary = [j for j in shown if j.get('batch',j['id']) in batches]
        total, sent = sum(j['total'] for j in summary),sum(j['sent'] for j in summary)
        pct = min(99 if active else 100,int(sent/total*100)) if total else (100 if shown and not active else 0)
        progress['value'] = pct
        heading['text'] = f"{len(active)} envio(s) em andamento" if active else 'DropAgíl — tudo pronto'
        subtitle['text'] = active[0]['name'] if active else ('Os arquivos concluídos estão disponíveis na rede.' if shown else 'Escolha arquivos ou use o botão direito no Explorador.')
        now = time.time()
        start = min((j['started'] for j in summary if j['started']),default=now)
        end = now if active else max((j['finished'] or now for j in summary),default=now)
        elapsed = max(0,int(end-start)); speed = sum(j['speed'] for j in active if j['state'] == 'sending')
        remaining = f" · cerca de {int(max(0,total-sent)/speed)} s restantes" if speed else ''
        timing['text'] = f"{pct}% · Decorrido: {elapsed//60:02d}:{elapsed%60:02d}{remaining}"
        states = {'sending':'Enviando','queued':'Na fila','paused':'Pausado','done':'Concluído','error':'Falha','cancelled':'Cancelado'}
        current = set(table.get_children()); wanted = {j['id'] for j in shown[-100:]}
        for ident in current-wanted: table.delete(ident)
        for job in shown[-100:]:
            if job['state'] not in ('done','error'): seen_terminal.discard(job['id'])
            amount = min(99,int(job['sent']/job['total']*100)) if job['total'] else 0
            if job['state'] == 'done': amount = 100
            seconds = max(0,int((job.get('finished') or now) - (job.get('started') or now)))
            values = (f'{amount}%',states.get(job['state'],job['state']),f'{seconds//60:02d}:{seconds%60:02d}')
            if job['id'] in current: table.item(job['id'],text=job['name'],values=values)
            else: table.insert('',tk.END,iid=job['id'],text=job['name'],values=values)
            if job['state'] == 'error' and active and job['id'] == active[0]['id']: subtitle['text'] = job['error']
            if job['state'] in ('done','error') and job['id'] not in seen_terminal:
                seen_terminal.add(job['id'])
                if job['state'] == 'done':
                    tray.notify(job['name'] + (' aguarda aceite no destino.' if job.get('target') else ' está disponível na rede.'),'Envio concluído')
                else:
                    tray.notify(job['name'] + ': ' + (job.get('error') or 'Verifique a transferência.'),'Falha no envio')
        root.after(500,tick)
    if background: root.withdraw()
    root.after(100,tick)
    root.mainloop()
    ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(mutex))


def main():
    if '--server' in sys.argv:
        from server import main as serve
        serve([arg for arg in sys.argv[1:] if arg != '--server']);return
    parser = argparse.ArgumentParser()
    parser.add_argument('--background',action='store_true')
    parser.add_argument('--send',nargs='+')
    parser.add_argument('--send-network',nargs='+')
    parser.add_argument('--send-device',nargs='+')
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--uninstall',action='store_true')
    args = parser.parse_args()
    if args.install or args.uninstall:
        install(args.uninstall)
        return
    paths=args.send_network or args.send_device or args.send
    action='send-network' if args.send_network else 'send-device'
    if paths:
        try:
            ipc(action,{'paths':paths}); return
        except Exception:
            subprocess.Popen(desktop_command('--background'),cwd=BASE,env=child_environment(),creationflags=CREATE_NO_WINDOW)
            for _ in range(40):
                try:
                    ipc(action,{'paths':paths}); return
                except Exception: time.sleep(.25)
            raise RuntimeError('A central não iniciou. Abra Iniciar-DropAgil.bat.')
    run_desktop(args.background)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        with (BASE / 'desktop-error.log').open('a',encoding='utf-8') as out:
            traceback.print_exc(file=out)
        if '--background' not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None,'Não foi possível abrir o DropAgíl. Consulte desktop-error.log.','DropAgíl',0x10)
        raise
