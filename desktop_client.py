"""Fila nativa do Windows. Copia em blocos pela API, preservando originais."""
import http.client
import json
from pathlib import Path
import secrets
import threading
import time

BASE = Path(__file__).resolve().parent


class LocalAPI:
    def __init__(self, port=8787):
        self.port, self.cookie = port, ''
        self.guard = threading.Lock()

    def request(self, method, path, data=None, headers=None, retry=True):
        headers = dict(headers or {})
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        headers['Cookie'] = self.cookie
        connection = http.client.HTTPConnection('127.0.0.1',self.port,timeout=120)
        try:
            connection.request(method,path,data,headers)
            response = connection.getresponse()
            payload = json.loads(response.read())
            code = response.status
            cookie = response.getheader('Set-Cookie')
            if cookie:
                self.cookie = cookie.split(';')[0]
        finally:
            connection.close()
        if code == 401 and retry:
            with self.guard:
                self.request('POST','/api/local-login',{},retry=False)
            return self.request(method,path,data,headers,retry=False)
        if code >= 400:
            raise RuntimeError(payload.get('error','Falha na central'))
        return payload


class DesktopQueue:
    def __init__(self, state_path=None, api=None):
        self.api = api or LocalAPI()
        self.path = Path(state_path or BASE / '.dropagil' / 'desktop-jobs.json')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.guard = threading.RLock()
        self.changed = threading.Event()
        self.stopping = False
        self.jobs = []
        try:
            self.jobs = json.loads(self.path.read_text('utf-8'))
            for job in self.jobs:
                if job['state'] in ('sending','queued','scanning'):
                    job['state'] = 'queued'
        except (OSError,ValueError):
            pass
        self.worker = threading.Thread(target=self.run,daemon=True)
        self.worker.start()

    def persist(self):
        with self.guard:
            target = self.path.with_suffix('.tmp')
            target.write_text(json.dumps(self.jobs,ensure_ascii=False),'utf-8')
            target.replace(self.path)

    def add(self, paths):
        with self.guard:
            batch = next((j.get('batch',j['id']) for j in self.jobs if j['state'] not in ('done','cancelled')),secrets.token_hex(8))
            for raw in dict.fromkeys(paths):
                source = Path(raw).resolve()
                if not source.exists() or source.is_symlink():
                    continue
                if source.is_relative_to((BASE / 'Recebidos').resolve()):
                    continue
                self.jobs.append({'id':secrets.token_hex(8),'batch':batch,'source':str(source),'name':source.name,'folder':source.is_dir(),'state':'queued','items':None,'total':0,'sent':0,'started':None,'finished':None,'error':'','speed':0})
            self.persist()
        self.changed.set()

    def snapshot(self):
        with self.guard:
            return [{k:v for k,v in job.items() if k != 'items'} for job in self.jobs]

    def control(self, action):
        with self.guard:
            for job in self.jobs:
                if action == 'cancel' and job['state'] not in ('done','cancelled'):
                    job['state'] = 'cancelled'
                    job['finished'] = time.time()
                elif action == 'pause' and job['state'] in ('sending','queued','scanning'):
                    job['state'] = 'paused'
                elif action == 'resume' and job['state'] in ('paused','error'):
                    job['state'], job['error'] = 'queued',''
            self.persist()
        self.changed.set()

    def run(self):
        while not self.stopping:
            with self.guard:
                job = next((j for j in self.jobs if j['state'] == 'queued'),None)
                if job:
                    job['state'] = 'sending'
                    job['started'] = job['started'] or time.time()
            if not job:
                self.cleanup_cancelled()
                self.changed.wait(.5); self.changed.clear()
                continue
            try:
                self.send(job)
            except Exception as error:
                with self.guard:
                    if job['state'] not in ('cancelled','paused'):
                        job['state'], job['error'] = 'error',str(error)
            self.persist()

    def scan(self,job):
        source = Path(job['source'])
        files = source.rglob('*') if source.is_dir() else [source]
        items = []
        for file in files:
            if job['state'] != 'sending' or self.stopping:
                return False
            if file.is_file() and not file.is_symlink() and file.resolve().is_relative_to(source if source.is_dir() else source.parent):
                stat = file.stat()
                items.append({'source':str(file),'path':file.relative_to(source.parent).as_posix(),'size':stat.st_size,'mtime':stat.st_mtime_ns,'offset':0,'id':None,'done':False})
        with self.guard:
            job['items'],job['total'] = items,sum(i['size'] for i in items)
        self.persist()
        return True

    def send(self,job):
        if job['items'] is None and not self.scan(job):
            return
        if not job['items']:
            raise RuntimeError('A pasta está vazia ou não há arquivos legíveis.')
        for item in job['items']:
            if job['state'] != 'sending' or self.stopping:
                return
            if item['done']:
                continue
            source = Path(item['source'])
            stat = source.stat()
            if stat.st_size != item['size'] or stat.st_mtime_ns != item['mtime']:
                raise RuntimeError('O arquivo de origem mudou. Cancele e envie novamente: ' + source.name)
            upload = self.api.request('POST','/api/uploads',{'path':item['path'],'size':item['size'],'id':item['id'],'fingerprint':f"desktop:{item['source']}:{item['size']}:{item['mtime']}"})
            item['id'],item['offset'] = upload['id'],upload['offset']
            self.persist()
            with source.open('rb') as stream:
                stream.seek(item['offset'])
                while item['offset'] < item['size']:
                    if job['state'] != 'sending' or self.stopping:
                        return
                    block = stream.read(min(8*1024*1024,item['size']-item['offset']))
                    if not block:
                        raise RuntimeError('Arquivo de origem interrompido.')
                    start = time.monotonic()
                    result = self.api.request('PUT','/api/uploads/'+item['id'],block,{'Content-Type':'application/octet-stream','Upload-Offset':str(item['offset'])})
                    item['offset'] = result['offset']
                    with self.guard:
                        job['sent'] = sum(i['offset'] for i in job['items'])
                        job['speed'] = len(block)/max(.001,time.monotonic()-start)
                    self.persist()
            if job['state'] != 'sending' or self.stopping:
                return
            self.api.request('POST','/api/uploads/'+item['id']+'/complete',{})
            item['done'] = True
            self.persist()
        with self.guard:
            if job['state'] == 'sending':
                job['state'],job['finished'],job['sent'] = 'done',time.time(),job['total']

    def cleanup_cancelled(self):
        changed = False
        for job in list(self.jobs):
            if job['state'] != 'cancelled':
                continue
            for item in job.get('items') or []:
                if item.get('id') and not item.get('done'):
                    try:
                        self.api.request('DELETE','/api/uploads/'+item['id'])
                        item['id'] = None
                        changed = True
                    except Exception:
                        continue
        if changed:
            self.persist()

    def close(self):
        self.stopping = True
        self.changed.set()
        self.persist()
