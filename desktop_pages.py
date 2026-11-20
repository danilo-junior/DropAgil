"""Native desktop pages: network files, devices, connection and Windows setup."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import http.client
import os
import secrets
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from urllib.parse import quote


def byte_size(value):
    value = value or 0
    for unit in ('B','KB','MB','GB','TB'):
        if value < 1024 or unit == 'TB': return f'{value:.1f} {unit}'
        value /= 1024


def download_shared(api, item, destination, cancelled, progress):
    api.request('GET','/api/status')  # refresh authentication before the binary request
    route = '/api/zip?path=' if item['directory'] else '/api/download?path='
    connection = http.client.HTTPConnection('127.0.0.1',api.port,timeout=120)
    destination = Path(destination)
    partial = destination.with_name(destination.name+'.'+secrets.token_hex(6)+'.part')
    try:
        connection.request('GET',route+quote(item['path']),headers={'Cookie':api.cookie})
        response = connection.getresponse()
        if response.status != 200: raise RuntimeError('Não foi possível baixar este arquivo.')
        total = int(response.getheader('Content-Length') or 0)
        received = 0
        with partial.open('xb') as output:
            while block := response.read(1024*1024):
                if cancelled.is_set(): raise RuntimeError('Download cancelado.')
                output.write(block);received += len(block);progress(received,total)
            output.flush();os.fsync(output.fileno())
        if total and received != total: raise RuntimeError('Download interrompido. Tente novamente.')
        if cancelled.is_set(): raise RuntimeError('Download cancelado.')
        partial.replace(destination)
        return destination
    finally:
        connection.close()
        partial.unlink(missing_ok=True)


class DesktopPages:
    def __init__(self, root, tabs, api, events, install, shared_folder):
        self.root,self.tabs,self.api,self.events = root,tabs,api,events
        self.pool = ThreadPoolExecutor(max_workers=3,thread_name_prefix='DropAgil-desktop')
        self.closed=False;self.folder='';self.items=[];self.devices=[];self.shared_folder=Path(shared_folder)
        self.cancel_download=threading.Event()
        self.files=ttk.Frame(tabs,padding=24);tabs.add(self.files,text='Arquivos da rede')
        self.device_page=ttk.Frame(tabs,padding=24);tabs.add(self.device_page,text='Dispositivos')
        self.connection=ttk.Frame(tabs,padding=24);tabs.add(self.connection,text='Conexão e ajustes')
        self.build_files();self.build_devices();self.build_connection(install)
        tabs.bind('<<NotebookTabChanged>>',lambda _:self.refresh_selected())

    def run(self, work, done=None):
        def complete(future):
            if self.closed:return
            try:
                value=future.result()
                if done:self.events.put(('ui',lambda:done(value)))
            except Exception as error:
                detail=str(error)
                self.events.put(('ui',lambda:messagebox.showerror('DropAgíl',detail,parent=self.root)))
        self.pool.submit(work).add_done_callback(complete)

    def title(self,parent,heading,detail):
        ttk.Label(parent,text=heading,font=('Segoe UI',22,'bold')).pack(anchor='w')
        ttk.Label(parent,text=detail,foreground='#687b64').pack(anchor='w',pady=(5,18))

    def show(self,page):self.tabs.select(page)

    def refresh_selected(self):
        selected=self.tabs.select()
        if selected==str(self.files):self.load_files()
        elif selected==str(self.device_page):self.load_devices()
        elif selected==str(self.connection):self.load_connection()

    def build_files(self):
        self.title(self.files,'Seus arquivos, por perto.','Navegue, salve e apague arquivos sem abrir o navegador.')
        tools=ttk.Frame(self.files);tools.pack(fill='x',pady=(0,12))
        ttk.Button(tools,text='Voltar',command=self.back).pack(side='left')
        ttk.Button(tools,text='Início',command=lambda:self.navigate('')).pack(side='left',padx=6)
        self.breadcrumb=ttk.Label(tools,text='Todos os arquivos');self.breadcrumb.pack(side='left',padx=8)
        ttk.Button(tools,text='Atualizar',command=self.load_files).pack(side='right')
        self.search=tk.StringVar();self.search.trace_add('write',lambda *_:self.render_files())
        search=ttk.Frame(self.files);search.pack(fill='x',pady=(0,12));ttk.Label(search,text='Buscar nesta pasta:').pack(side='left',padx=(0,10));ttk.Entry(search,textvariable=self.search).pack(fill='x',expand=True)
        table_frame=ttk.Frame(self.files);table_frame.pack(fill='both',expand=True)
        self.file_table=ttk.Treeview(table_frame,columns=('kind','size'),selectmode='browse')
        self.file_table.heading('#0',text='Nome');self.file_table.column('#0',width=430)
        self.file_table.heading('kind',text='Tipo');self.file_table.column('kind',width=90,stretch=False)
        self.file_table.heading('size',text='Tamanho');self.file_table.column('size',width=100,stretch=False)
        scroll=ttk.Scrollbar(table_frame,command=self.file_table.yview);self.file_table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.file_table.pack(side='left',fill='both',expand=True)
        self.file_table.bind('<Double-1>',lambda _:self.open_selected())
        actions=ttk.Frame(self.files);actions.pack(fill='x',pady=(16,8))
        ttk.Button(actions,text='Abrir pasta',command=self.open_selected).pack(side='left')
        self.save_button=ttk.Button(actions,text='Salvar no computador',style='Primary.TButton',command=self.save_selected);self.save_button.pack(side='left',padx=6)
        ttk.Button(actions,text='Apagar da rede',style='Danger.TButton',command=self.delete_selected).pack(side='left')
        ttk.Button(actions,text='Cancelar download',command=self.cancel_download.set).pack(side='right')
        self.file_status=ttk.Label(self.files,text='');self.file_status.pack(anchor='w')
        self.download_progress=ttk.Progressbar(self.files,maximum=100);self.download_progress.pack(fill='x',pady=(6,0))

    def navigate(self,path):self.folder=path;self.search.set('');self.load_files()
    def back(self):self.navigate(self.folder.rsplit('/',1)[0] if '/' in self.folder else '')
    def load_files(self):
        path=self.folder
        def show(data):
            if path!=self.folder:return
            self.items=data['items'];self.breadcrumb['text']=path or 'Todos os arquivos';self.render_files()
        self.run(lambda:self.api.request('GET','/api/files?path='+quote(path)),show)
    def render_files(self):
        self.file_table.delete(*self.file_table.get_children())
        term=self.search.get().casefold()
        for i,item in enumerate(self.items):
            if term in item['name'].casefold():self.file_table.insert('',tk.END,iid=str(i),text=item['name'],values=('Pasta' if item['directory'] else 'Arquivo','—' if item['directory'] else byte_size(item['size'])))
        self.file_status['text']=f'{len(self.file_table.get_children())} item(ns) nesta pasta'
    def selection(self):
        selected=self.file_table.selection()
        if not selected:messagebox.showinfo('DropAgíl','Selecione um arquivo ou pasta.',parent=self.root);return None
        return self.items[int(selected[0])]
    def open_selected(self):
        item=self.selection()
        if item and item['directory']:self.navigate(item['path'])
        elif item:self.save_selected(item)
    def save_selected(self,item=None):
        item=item or self.selection()
        if not item:return
        target=filedialog.asksaveasfilename(parent=self.root,title='Salvar arquivo',initialfile=item['name']+('.zip' if item['directory'] else ''))
        if not target:return
        self.cancel_download.clear();self.save_button['state']='disabled'
        self.file_status['text']='Baixando…';self.download_progress['value']=0
        def progress(received,total):
            self.events.put(('ui',lambda:self.set_download_progress(received,total)))
        def work():
            try:return download_shared(self.api,item,target,self.cancel_download,progress)
            finally:self.events.put(('ui',lambda:self.save_button.configure(state='normal')))
        self.run(work,lambda path:self.file_status.configure(text=f'Salvo em {path}'))
    def set_download_progress(self,received,total):
        self.file_status['text']=f'{byte_size(received)} recebidos'+(f' de {byte_size(total)}' if total else '')
        self.download_progress['value']=received/total*100 if total else 0
    def delete_selected(self):
        item=self.selection()
        if not item:return
        detail='A pasta e todo o seu conteúdo' if item['directory'] else 'O arquivo'
        if not messagebox.askyesno('Apagar da rede?',f'{item["name"]}\n\n{detail} será apagado permanentemente da rede. A cópia no dispositivo de origem é mantida.',parent=self.root):return
        self.run(lambda:self.api.request('DELETE','/api/files',{'path':item['path']}),lambda _:self.load_files())

    def build_devices(self):
        self.title(self.device_page,'Escolha pelo nome.','Renomeie os dispositivos para reconhecer o destino de cada envio.')
        self.device_table=ttk.Treeview(self.device_page,columns=('identity',),selectmode='browse')
        self.device_table.heading('#0',text='Dispositivo');self.device_table.heading('identity',text='Identificação')
        self.device_table.column('#0',width=420);self.device_table.column('identity',width=180)
        self.device_table.pack(fill='both',expand=True)
        actions=ttk.Frame(self.device_page);actions.pack(fill='x',pady=18)
        ttk.Button(actions,text='Renomear dispositivo',style='Primary.TButton',command=self.rename_device).pack(side='left')
        ttk.Button(actions,text='Atualizar lista',command=self.load_devices).pack(side='left',padx=8)
        ttk.Label(self.device_page,text='Os nomes ficam salvos na central e aparecem em todos os aparelhos.').pack(anchor='w')
    def load_devices(self):
        def show(data):
            self.devices=([data['current']] if data.get('current') else [])+data['devices']
            self.device_table.delete(*self.device_table.get_children())
            for d in self.devices:self.device_table.insert('',tk.END,iid=d['id'],text=d['name'],values=('Este computador' if d['id']==data['id'] else d['id'][-6:],))
        self.run(lambda:self.api.request('GET','/api/devices'),show)
    def rename_device(self):
        selected=self.device_table.selection()
        if not selected:return
        ident=selected[0];old=self.device_table.item(ident,'text')
        name=simpledialog.askstring('Renomear dispositivo','Nome na rede (até 50 caracteres):',initialvalue=old,parent=self.root)
        if name is not None:self.run(lambda:self.api.request('POST','/api/devices/'+ident+'/rename',{'name':name}),lambda _:self.load_devices())

    def build_connection(self,install):
        self.title(self.connection,'Tudo conectado.','Use o endereço e o código abaixo para conectar os celulares.')
        row=ttk.Frame(self.connection);row.pack(fill='x')
        self.qr=ttk.Label(row);self.qr.pack(side='right',padx=24)
        info=ttk.Frame(row);info.pack(side='left',fill='both',expand=True)
        self.address=tk.StringVar();ttk.Label(info,text='Endereço na rede').pack(anchor='w')
        ttk.Entry(info,textvariable=self.address,state='readonly',font=('Segoe UI',13)).pack(fill='x',pady=(8,12))
        ttk.Button(info,text='Copiar endereço',command=self.copy_address).pack(anchor='w')
        ttk.Label(info,text='Código de acesso',foreground='#687b64').pack(anchor='w',pady=(22,4))
        self.pin=ttk.Label(info,text='······',font=('Segoe UI',32,'bold'));self.pin.pack(anchor='w')
        self.storage=ttk.Label(info,text='');self.storage.pack(anchor='w',pady=8)
        ttk.Separator(self.connection).pack(fill='x',pady=20)
        ttk.Label(self.connection,text='Integração com Windows',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(self.connection,text='Início automático e dois atalhos no botão direito: Rede e Dispositivo.').pack(anchor='w',pady=8)
        ttk.Button(self.connection,text='Ativar / atualizar integração',command=lambda:self.run(install,lambda _:messagebox.showinfo('DropAgíl','Integração atualizada. No Windows 11, veja também Mostrar mais opções.',parent=self.root))).pack(anchor='w')
        ttk.Label(self.connection,text='Envios concluídos desaparecem da fila após 30 segundos. Os arquivos são mantidos.\nFechar a janela mantém o DropAgíl na bandeja. Versão 4.0.',foreground='#687b64').pack(anchor='w',pady=20)
    def copy_address(self):self.root.clipboard_clear();self.root.clipboard_append(self.address.get())
    def load_connection(self):
        def show(data):
            self.address.set(data['urls'][0] if data['urls'] else 'Sem endereço de rede disponível')
            self.pin['text']=data.get('pin') or '······';self.storage['text']=byte_size(data['free'])+' livres no computador'
            if data['urls']:
                import qrcode
                from PIL import ImageTk
                self.qr_image=ImageTk.PhotoImage(qrcode.make(data['urls'][0]).resize((190,190)))
                self.qr.configure(image=self.qr_image)
        self.run(lambda:self.api.request('GET','/api/status'),show)
    def close(self):
        self.closed=True;self.cancel_download.set();self.pool.shutdown(wait=False,cancel_futures=True)
