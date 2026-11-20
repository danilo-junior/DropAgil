"""LAN inbox for the Windows tray; asks before saving to Downloads."""
import http.client
import os
from pathlib import Path
import threading
from urllib.parse import quote


def downloads_folder():
    if os.name == 'nt':
        import ctypes
        import uuid
        guid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('374DE290-123F-4565-9164-39C4925E467B').bytes_le)
        value = ctypes.c_void_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid),0,None,ctypes.byref(value))
        if result == 0:
            try: return Path(ctypes.wstring_at(value))
            finally: ctypes.windll.ole32.CoTaskMemFree(value)
    return Path.home() / 'Downloads'


class DesktopReceiver:
    def __init__(self, api, events, destination=None):
        self.api, self.events = api, events
        self.destination = Path(destination) if destination else downloads_folder() / 'DropAgil'
        self.stop = threading.Event()
        self.guard = threading.Lock()
        self.devices = []
        self.offered = set()
        self.busy = set()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop.is_set():
            try:
                result = self.api.request('POST','/api/devices',{'name':os.environ.get('COMPUTERNAME','Computador Windows')})
                self.devices = result['devices']
                items = self.api.request('GET','/api/inbox')['items']
                with self.guard:
                    fresh = [f for f in items if f['id'] not in self.offered and f['id'] not in self.busy]
                    self.offered.update(f['id'] for f in fresh)
                if fresh: self.events.put(('incoming',fresh))
            except Exception:
                pass
            self.stop.wait(3)

    def respond(self, files, accept):
        def work():
            for item in files:
                uid = item['id']
                with self.guard: self.busy.add(uid)
                try:
                    self.api.request('POST','/api/inbox/'+uid,{'action':'accept' if accept else 'reject'})
                    if accept:
                        destination = self.download(item)
                        self.api.request('POST','/api/inbox/'+uid,{'action':'received'})
                        self.events.put(('received',str(destination)))
                except Exception as error:
                    self.events.put(('receive-error',str(error)))
                    with self.guard: self.offered.discard(uid)
                finally:
                    with self.guard: self.busy.discard(uid)
        threading.Thread(target=work,daemon=True).start()

    def download(self,item):
        uid = item['id']
        # The server validates names; check again before writing local paths.
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts or ':' in str(relative):
            raise ValueError('Caminho de entrega inválido.')
        base = self.destination.resolve()
        target = base / uid[:8] / relative
        if not target.resolve().is_relative_to(base):
            raise ValueError('Caminho fora da pasta de recebimento.')
        target.parent.mkdir(parents=True,exist_ok=True)
        part = target.with_name(target.name+'.dropagil-part')
        offset = part.stat().st_size if part.exists() else 0
        if part.exists() and offset == item['size']:
            part.replace(target)
            return target
        headers = {'Cookie':self.api.cookie}
        if offset: headers['Range'] = f'bytes={offset}-'
        connection = http.client.HTTPConnection('127.0.0.1',self.api.port,timeout=120)
        try:
            connection.request('GET','/api/inbox/'+uid+'/download',headers=headers)
            response = connection.getresponse()
            if response.status not in (200,206):
                raise RuntimeError('Não foi possível baixar o arquivo. Tente novamente.')
            if response.status == 200: offset = 0
            with part.open('ab' if offset else 'wb') as out:
                while block := response.read(1024*1024):
                    if self.stop.is_set(): raise RuntimeError('Recebimento interrompido. Retome ao abrir a bandeja.')
                    out.write(block)
                out.flush(); os.fsync(out.fileno())
            if part.stat().st_size != item['size']:
                raise RuntimeError('Download incompleto. Aceite novamente para retomar.')
            part.replace(target)
            return target
        finally:
            connection.close()

    def close(self):
        self.stop.set()
