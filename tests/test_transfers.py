import hashlib
import http.client
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import quote
from urllib.parse import urlsplit
import zipfile

from server import App, Handler, ThreadingHTTPServer, CHUNK
from desktop_client import DesktopQueue, LocalAPI
from desktop_receiver import DesktopReceiver


class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_root = Path(__file__).resolve().parent
        cls.temp = tempfile.TemporaryDirectory(prefix='dropagil-test-', dir=cls.test_root)
        cls.app = App(cls.temp.name, 0, '123456')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.app = cls.app
        cls.port = cls.server.server_address[1]
        cls.app.port = cls.port
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        _, headers, _ = cls.request('POST', '/api/local-login', {}, auth=False)
        cls.cookie = headers['Set-Cookie'].split(';')[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()
        target = Path(cls.temp.name).resolve()
        if target.parent != cls.test_root or not target.name.startswith('dropagil-test-'):
            raise RuntimeError('Diretório temporário fora da área de testes.')
        cls.temp.cleanup()

    @classmethod
    def request(cls, method, path, data=None, headers=None, auth=True):
        request_headers = dict(headers or {})
        if auth:
            request_headers['Cookie'] = cls.cookie
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            request_headers['Content-Type'] = 'application/json'
        connection = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=20)
        connection.request(method, path, data, request_headers)
        response = connection.getresponse()
        body = response.read()
        status, response_headers = response.status, dict(response.getheaders())
        connection.close()
        if response_headers.get('Content-Type', '').startswith('application/json'):
            body = json.loads(body)
        return status, response_headers, body

    def create(self, path, size, **kwargs):
        code, _, data = self.request('POST', '/api/uploads', {'path':path, 'size':size, 'fingerprint':path, **kwargs})
        self.assertEqual(code, 200, data)
        return data

    def put(self, uid, content, offset=0, **headers):
        return self.request('PUT', '/api/uploads/' + uid, content, {'Upload-Offset':str(offset), **headers})

    def complete(self, uid):
        code, _, data = self.request('POST', '/api/uploads/' + uid + '/complete', {})
        self.assertEqual(code, 200, data)
        return data

    def test_auth_origin_host_and_pin(self):
        self.assertEqual(self.request('GET', '/api/files', auth=False)[0], 401)
        self.assertEqual(self.request('POST', '/api/login', {'pin':'wrong'}, auth=False)[0], 401)
        self.assertEqual(self.request('POST', '/api/login', {'pin':'123456','name':'Celular'}, auth=False)[0], 200)
        self.assertEqual(self.request('POST', '/api/local-login', {}, {'Origin':'https://evil.test'}, auth=False)[0], 403)
        self.assertEqual(self.request('GET', '/api/status', headers={'Host':'evil.test'})[0], 403)

    def test_quick_share_guest_download_expiry_and_revoke(self):
        file = self.app.shared / 'visita.txt'
        file.write_bytes(b'arquivo para visita')
        previous_ips = self.app.ips
        self.app.ips = ['127.0.0.1']
        try:
            self.assertEqual(self.request('POST','/api/quick-share',{'path':'visita.txt'},auth=False)[0],401)
            self.assertEqual(self.request('POST','/api/quick-share',{'path':'..'})[0],400)
            code, _, data = self.request('POST','/api/quick-share',{'path':'visita.txt'})
            self.assertEqual(code,200)
            guest_path = urlsplit(data['urls'][0]).path
            self.assertEqual(self.request('GET',guest_path,auth=False)[0],200)
            self.assertEqual(self.request('GET',guest_path,headers={'Sec-Fetch-Site':'cross-site'},auth=False)[0],200)
            self.assertIn(b'visita.txt',self.request('GET',guest_path,auth=False)[2])
            self.assertEqual(self.request('GET',guest_path+'/download',auth=False)[2],b'arquivo para visita')
            code, headers, body = self.request('GET',guest_path+'/download',headers={'Range':'bytes=0-6'},auth=False)
            self.assertEqual((code,body),(206,b'arquivo'))
            self.assertEqual(self.request('GET','/api/qr?url='+quote(data['urls'][0],safe=''))[0],200)
            self.assertEqual(self.request('GET','/quick/'+'x'*43,auth=False)[0],404)
            file.write_bytes('conteúdo alterado'.encode())
            self.assertEqual(self.request('GET',guest_path+'/download',auth=False)[0],404)
            file.write_bytes(b'novo arquivo')
            fresh = self.request('POST','/api/quick-share',{'path':'visita.txt'})[2]
            with self.app.db() as db:
                db.execute('UPDATE quick_shares SET expires=0 WHERE digest=?',
                           (hashlib.sha256(fresh['token'].encode()).hexdigest(),))
            self.assertEqual(self.request('GET',urlsplit(fresh['urls'][0]).path,auth=False)[0],404)
            fresh = self.request('POST','/api/quick-share',{'path':'visita.txt'})[2]
            self.assertEqual(self.request('DELETE','/api/quick-share/'+fresh['token'])[0],200)
            self.assertEqual(self.request('GET',urlsplit(fresh['urls'][0]).path,auth=False)[0],404)
        finally:
            self.app.ips = previous_ips
            file.unlink(missing_ok=True)

    def test_android_update_metadata_matches_served_apk(self):
        folder = Path(self.temp.name)
        apk = folder / 'DropAgil-Android.apk'
        metadata = folder / 'DropAgil-Android.version.json'
        apk.write_bytes(b'example apk')
        metadata.write_text(json.dumps({'versionCode':6,'versionName':'4.2',
            'size':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest()}),encoding='utf-8')
        with patch('server.BASE', folder):
            self.assertEqual(self.request('GET','/api/android-update',auth=False)[0],401)
            code, _, info = self.request('GET','/api/android-update')
            self.assertEqual(code,200)
            self.assertEqual((info['versionCode'],info['url']),(6,'/api/android-apk'))
            self.assertEqual(self.request('GET','/api/android-apk')[2],b'example apk')
            apk.write_bytes(b'changed')
            self.assertEqual(self.request('GET','/api/android-update')[0],503)

    def test_delete_file_folder_and_resume_after_deletion(self):
        upload = self.create('delete-me/nested/file.bin', 4)
        self.assertEqual(self.put(upload['id'], b'test')[0], 200)
        self.complete(upload['id'])
        (self.app.shared / 'keep-me.bin').write_bytes(b'keep')
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'delete-me'})[0], 200)
        self.assertFalse((self.app.shared / 'delete-me').exists())
        self.assertEqual((self.app.shared / 'keep-me.bin').read_bytes(), b'keep')
        self.assertEqual(self.request('GET', '/api/uploads/' + upload['id'])[0], 404)
        fresh = self.create('delete-me/nested/file.bin', 4, id=upload['id'])
        self.assertNotEqual(fresh['id'], upload['id'])
        self.request('DELETE', '/api/uploads/' + fresh['id'])
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'keep-me.bin'})[0], 200)
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'keep-me.bin'})[0], 404)

    def test_delete_requires_auth_and_valid_path(self):
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'x'}, auth=False)[0], 401)
        for value in ['', '.', '..', '../outside', 'C:\\outside', None]:
            self.assertEqual(self.request('DELETE', '/api/files', {'path':value})[0], 400)
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'x'}, headers={'Origin':'https://other.test'})[0], 403)

    def test_delete_blocks_pending_and_linked_directories(self):
        folder = self.app.shared / 'busy'
        folder.mkdir(exist_ok=True)
        (folder / 'keep.txt').write_text('keep')
        pending = self.create('busy/later.bin', 1)
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'BUSY'})[0], 409)
        self.assertTrue((folder / 'keep.txt').exists())
        self.request('DELETE', '/api/uploads/' + pending['id'])
        with patch.object(Path, 'is_symlink', side_effect=lambda: True):
            self.assertEqual(self.request('DELETE', '/api/files', {'path':'busy'})[0], 403)
        self.assertTrue(folder.exists())

    def test_delete_with_mobile_pairing(self):
        code, _, pairing = self.request('POST', '/api/pair', {'name':'Android test'})
        self.assertEqual(code, 200)
        (self.app.shared / 'mobile-cleanup.txt').write_text('test')
        self.assertEqual(self.request('DELETE', '/api/files', {'path':'mobile-cleanup.txt'},
            headers={'Authorization':'Bearer ' + pairing['token']}, auth=False)[0], 200)

    def test_device_rename_persists_across_heartbeat_and_restart(self):
        _, _, pair=self.request('POST','/api/pair',{'name':'Android model'})
        headers={'Authorization':'Bearer '+pair['token']}
        _, _, registered=self.request('POST','/api/devices',{'name':'Android model'},headers,auth=False)
        device_id=registered['id'];route='/api/devices/'+device_id+'/rename'
        self.assertEqual(self.request('POST',route,{'name':'Celular da Thai'})[0],200)
        _, _, refreshed=self.request('POST','/api/devices',{'name':'Android model'},headers,auth=False)
        self.assertEqual(refreshed['current']['name'],'Celular da Thai')
        reloaded=App(self.temp.name,self.port,'123456')
        with reloaded.db() as db:self.assertEqual(db.execute('SELECT name FROM devices WHERE id=?',(device_id,)).fetchone()[0],'Celular da Thai')
        self.assertEqual(self.request('POST',route,{'name':'bad'},auth=False)[0],401)
        for name in ['', ' ', 'x'*51, 'line\nbreak']:
            self.assertEqual(self.request('POST',route,{'name':name})[0],400)
        self.assertEqual(self.request('POST','/api/devices/'+'0'*32+'/rename',{'name':'Missing'})[0],404)

    def test_direct_delivery_is_private_and_requires_recipient_acceptance(self):
        def device(name):
            _, _, pair = self.request('POST','/api/pair',{'name':name})
            headers = {'Authorization':'Bearer '+pair['token']}
            code, _, registered = self.request('POST','/api/devices',{'name':name},headers,auth=False)
            self.assertEqual(code,200)
            return headers, registered['id']
        first, first_id = device('Dispositivo 1')
        second, second_id = device('Dispositivo 2')
        third, third_id = device('Dispositivo 3')
        data = bytes(range(256))*100
        code, _, upload = self.request('POST','/api/uploads',{'path':'private/foto.jpg','size':len(data),'target':third_id},second,auth=False)
        self.assertEqual(code,200)
        uid=upload['id']
        self.assertEqual(self.request('PUT','/api/uploads/'+uid,data,{**second,'Upload-Offset':'0'},auth=False)[0],200)
        self.assertEqual(self.request('POST','/api/uploads/'+uid+'/complete',{},second,auth=False)[0],200)
        self.assertFalse((self.app.shared/'private/foto.jpg').exists())
        self.assertEqual(self.request('GET','/api/uploads/'+uid,headers=first,auth=False)[0],404)
        self.assertEqual(self.request('GET','/api/inbox',headers=first,auth=False)[2]['items'],[])
        inbox=self.request('GET','/api/inbox',headers=third,auth=False)[2]['items']
        self.assertIn(uid,[f['id'] for f in inbox])
        route='/api/inbox/'+uid
        self.assertEqual(self.request('GET',route+'/download',headers=third,auth=False)[0],403)
        self.assertEqual(self.request('POST',route,{'action':'accept'},first,auth=False)[0],404)
        self.assertEqual(self.request('POST',route,{'action':'accept'},third,auth=False)[0],200)
        self.assertEqual(self.request('GET',route+'/download',headers=third,auth=False)[2],data)
        code, _, partial=self.request('GET',route+'/download',headers={**third,'Range':'bytes=100-'},auth=False)
        self.assertEqual(code,206);self.assertEqual(partial,data[100:])
        self.assertEqual(self.request('POST',route,{'action':'received'},third,auth=False)[0],200)
        self.assertFalse((self.app.temp/'direct'/uid).exists())
        self.assertEqual(self.request('GET',route+'/download',headers=third,auth=False)[0],403)
        self.assertEqual(self.request('GET','/api/inbox',headers=third,auth=False)[2]['items'],[])

    def test_direct_rejection_and_changed_recipient(self):
        _, _, pair=self.request('POST','/api/pair',{'name':'Receiver'})
        headers={'Authorization':'Bearer '+pair['token']}
        _, _, registered=self.request('POST','/api/devices',{'name':'Receiver'},headers,auth=False)
        upload=self.create('direct-zero.txt',0,target=registered['id'])
        self.assertEqual(self.request('POST','/api/uploads',{'path':'direct-zero.txt','size':0,'id':upload['id'],'target':'','fingerprint':'direct-zero.txt'})[0],409)
        self.complete(upload['id'])
        self.assertEqual(self.request('POST','/api/inbox/'+upload['id'],{'action':'reject'},headers,auth=False)[0],200)
        self.assertFalse((self.app.temp/'direct'/upload['id']).exists())
        self.assertEqual(self.request('POST','/api/uploads',{'path':'x','size':0,'target':'missing'})[0],404)

    def test_windows_receiver_streams_and_resumes_to_downloads(self):
        api=LocalAPI(self.port)
        local=api.request('POST','/api/devices',{'name':'Windows test'})
        _, _, pair=self.request('POST','/api/pair',{'name':'Sender test'})
        headers={'Authorization':'Bearer '+pair['token']}
        data=b'large-content-'*100000
        code, _, upload=self.request('POST','/api/uploads',{'path':'album/video.mp4','size':len(data),'target':local['id']},headers,auth=False)
        self.assertEqual(code,200)
        uid=upload['id']
        self.assertEqual(self.request('PUT','/api/uploads/'+uid,data,{**headers,'Upload-Offset':'0'},auth=False)[0],200)
        self.assertEqual(self.request('POST','/api/uploads/'+uid+'/complete',{},headers,auth=False)[0],200)
        api.request('POST','/api/inbox/'+uid,{'action':'accept'})
        receiver=DesktopReceiver.__new__(DesktopReceiver)
        receiver.api,receiver.stop=api,threading.Event()
        receiver.destination=Path(self.temp.name)/'downloads'
        part=receiver.destination/uid[:8]/'album/video.mp4.dropagil-part'
        part.parent.mkdir(parents=True);part.write_bytes(data[:10000])
        target=receiver.download({'id':uid,'path':'album/video.mp4','size':len(data)})
        self.assertEqual(target.read_bytes(),data)
        self.assertFalse(part.exists())
        api.request('POST','/api/inbox/'+uid,{'action':'received'})
        self.assertEqual(target.read_bytes(),data)

    def test_traversal_windows_reserved_and_symlinks(self):
        for path in ['../escape','folder/../../escape','/absolute','C:\\escape','folder\\..\\escape','NUL.txt','a/b.','a:b','foo\x00bar']:
            with self.subTest(path=path):
                self.assertEqual(self.request('POST','/api/uploads',{'path':path,'size':0})[0],400)
        with patch.object(Path, 'is_symlink', return_value=True):
            self.assertEqual(self.request('GET','/api/files?path=test')[0],403)

    def test_multichunk_resume_restart_and_exact_download(self):
        data = bytes(range(256)) * (CHUNK // 256 + 345)
        upload = self.create('férias/filme.bin', len(data))
        uid = upload['id']
        self.assertEqual(self.put(uid, data[:CHUNK])[0],200)
        # Simula uma conexão perdida depois de gravar bytes, antes de confirmar o offset.
        part = self.app.temp / (uid + '.part')
        with part.open('ab') as stream:
            stream.write(b'bloco-incompleto')
        # Recria todo o estado da aplicação, como numa nova execução.
        app = App(self.temp.name, self.port, '123456')
        self.server.app = app
        _, headers, _ = self.request('POST','/api/local-login',{},auth=False)
        type(self).cookie = headers['Set-Cookie'].split(';')[0]
        resumed = self.create('férias/filme.bin',len(data),id=uid)
        self.assertEqual(resumed['offset'],CHUNK)
        self.assertEqual(self.put(uid, data[CHUNK:], CHUNK)[0],200)
        self.complete(uid)
        code, _, actual = self.request('GET','/api/download?path=' + quote('férias/filme.bin'))
        self.assertEqual(code,200)
        self.assertEqual(hashlib.sha256(data).digest(),hashlib.sha256(actual).digest())
        self.assertEqual(self.complete(uid)['state'],'done')

    def test_zero_file_duplicate_and_complete_guard(self):
        one = self.create('vazio.txt',0)
        self.complete(one['id'])
        self.assertEqual(self.request('GET','/api/download?path=vazio.txt')[2], b'')
        two = self.create('vazio.txt',1)
        self.assertEqual(two['path'],'vazio (1).txt')
        self.assertEqual(self.request('POST',f"/api/uploads/{two['id']}/complete",{})[0],409)
        self.put(two['id'],b'x')
        self.complete(two['id'])

    def test_range_requests(self):
        upload = self.create('ranges.bin',10)
        self.put(upload['id'],b'0123456789')
        self.complete(upload['id'])
        for value, expected in [('bytes=2-5',b'2345'),('bytes=8-',b'89'),('bytes=-3',b'789'),('bytes=0-999',b'0123456789')]:
            code, headers, data = self.request('GET','/api/download?path=ranges.bin',headers={'Range':value})
            self.assertEqual(code,206)
            self.assertEqual(data,expected)
            self.assertIn('Content-Range',headers)
        for value in ['bytes=11-','bytes=3-1','bytes=-0','bytes=1-2,4-6']:
            code, headers, _ = self.request('GET','/api/download?path=ranges.bin',headers={'Range':value})
            self.assertEqual(code,416)
            self.assertEqual(headers['Content-Range'],'bytes */10')
        self.assertEqual(self.request('HEAD','/api/download?path=ranges.bin')[2],b'')
        self.assertEqual(self.request('GET','/api/download?path=ranges.bin',headers={'Range':'bytes=8-','If-Range':'"stale"'})[0],200)

    def test_chunk_checksums_wrong_offset_and_cancel(self):
        upload = self.create('cancel.bin',3)
        self.assertEqual(self.put(upload['id'],b'abc',1)[0],409)
        self.assertEqual(self.put(upload['id'],b'abc',0,**{'X-Chunk-SHA256':'wrong'})[0],409)
        self.assertEqual(self.request('GET',f"/api/uploads/{upload['id']}")[2]['offset'],0)
        self.assertEqual(self.put(upload['id'],b'abc',0,**{'X-Chunk-SHA256':hashlib.sha256(b'abc').hexdigest()})[0],200)
        self.assertEqual(self.request('DELETE',f"/api/uploads/{upload['id']}")[0],200)
        self.assertFalse((self.app.temp / (upload['id'] + '.part')).exists())

    def test_actual_interrupted_request(self):
        upload = self.create('interrupt.bin',10)
        client = socket.create_connection(('127.0.0.1',self.port))
        message = (f"PUT /api/uploads/{upload['id']} HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nCookie: {self.cookie}\r\nContent-Length: 10\r\nUpload-Offset: 0\r\n\r\nabc").encode()
        client.sendall(message)
        client.shutdown(socket.SHUT_WR)
        while client.recv(4096):
            pass
        client.close()
        self.assertEqual(self.request('GET',f"/api/uploads/{upload['id']}")[2]['offset'],0)
        self.assertEqual(self.put(upload['id'],b'0123456789')[0],200)
        self.complete(upload['id'])
        self.assertEqual(self.request('GET','/api/download?path=interrupt.bin')[2],b'0123456789')

    def test_zip_preserves_tree_and_bytes(self):
        for name, content in [('viagem/fotos/a.txt',b'foto'),('viagem/notas.txt',b'notas')]:
            upload = self.create(name,len(content))
            self.put(upload['id'],content)
            self.complete(upload['id'])
        code, _, data = self.request('GET','/api/zip?path=viagem')
        self.assertEqual(code,200)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.testzip(),None)
            self.assertEqual(archive.read('viagem/fotos/a.txt'),b'foto')
            self.assertEqual(archive.read('viagem/notas.txt'),b'notas')

    def test_offset_above_4gb_without_allocating_large_file(self):
        offset = 5 * 1024**3
        with patch('server.shutil.disk_usage',return_value=type('Usage',(),{'free':offset*2})()):
            upload = self.create('large.bin',offset+1)
        with self.app.db() as db:
            db.execute('UPDATE uploads SET offset=? WHERE id=?',(offset,upload['id']))
        self.assertEqual(self.request('GET',f"/api/uploads/{upload['id']}")[2]['offset'],offset)
        class SparseMock:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def truncate(self,n): self.truncated = n
            def seek(self,n): self.position = n
            def write(self,data): self.data = data
            def flush(self): pass
            def fileno(self): return 0
        sink = SparseMock()
        with patch.object(Path,'open',return_value=sink), patch('server.os.fsync'):
            code, _, result = self.put(upload['id'],b'x',offset)
        self.assertEqual(code,200)
        self.assertEqual(result['offset'],offset+1)
        self.assertEqual(sink.position,offset)
        self.request('DELETE',f"/api/uploads/{upload['id']}")

    def test_pairing_token_persists_and_can_be_revoked(self):
        code, _, paired = self.request('POST','/api/pair',{'name':'Android de teste'})
        self.assertEqual(code,200)
        token = paired['token']
        self.assertEqual(self.request('GET','/api/status',headers={'Authorization':'Bearer '+token},auth=False)[0],200)
        app = App(self.temp.name,self.port,'123456')
        self.server.app = app
        self.assertEqual(self.request('GET','/api/status',headers={'Authorization':'Bearer '+token},auth=False)[0],200)
        _, headers, _ = self.request('POST','/api/local-login',{},auth=False)
        type(self).cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('POST','/api/revoke-pairings',{})[0],200)
        self.assertEqual(self.request('GET','/api/status',headers={'Authorization':'Bearer '+token},auth=False)[0],401)

    def test_desktop_folder_upload_preserves_originals(self):
        source=Path(self.temp.name)/'Pasta desktop'
        (source/'subpasta').mkdir(parents=True)
        (source/'um.txt').write_bytes(b'arquivo um')
        (source/'subpasta'/'dois.bin').write_bytes(bytes(range(256))*1000)
        queue=DesktopQueue(Path(self.temp.name)/'desktop-test.json',LocalAPI(self.port))
        try:
            queue.add([str(source)])
            deadline=time.monotonic()+15
            while time.monotonic()<deadline and queue.snapshot()[0]['state'] not in ('done','error'):
                time.sleep(.02)
            jobs=queue.snapshot()
            self.assertEqual(len(jobs),1)
            self.assertEqual(jobs[0]['state'],'done',jobs)
            self.assertEqual(jobs[0]['sent'],jobs[0]['total'])
            self.assertTrue((source/'um.txt').exists())
            self.assertEqual((self.app.shared/'Pasta desktop'/'subpasta'/'dois.bin').read_bytes(),(source/'subpasta'/'dois.bin').read_bytes())
        finally:
            queue.close();queue.worker.join(5)


if __name__ == '__main__':
    unittest.main()
