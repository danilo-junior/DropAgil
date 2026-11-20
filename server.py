"""DropAgíl: servidor local de arquivos, Python 3.10+."""
import argparse
from contextlib import contextmanager
import hashlib
import http.cookies
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit
import zipfile

BASE = Path(__file__).resolve().parent
CHUNK = 8 * 1024 * 1024


class Problem(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def addresses():
    result = set()
    try:
        result.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(ip for ip in result if not ip.startswith(('127.', '169.254.')))


class App:
    def __init__(self, root, port, pin=None):
        self.root = Path(root).resolve()
        self.shared = self.root / 'Recebidos'
        self.temp = self.root / '.dropagil'
        self.shared.mkdir(parents=True, exist_ok=True)
        self.temp.mkdir(exist_ok=True)
        self.port, self.pin = port, pin or str(secrets.randbelow(900000) + 100000)
        self.ips = addresses()
        self.address_time = time.monotonic()
        self.sessions, self.attempts, self.locks = {}, {}, {}
        self.guard = threading.RLock()
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, path TEXT, size INTEGER, offset INTEGER, state TEXT, fingerprint TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS pairings (digest TEXT PRIMARY KEY, name TEXT, created REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, name TEXT, seen REAL)')
            db.execute("CREATE TABLE IF NOT EXISTS routing (upload_id TEXT PRIMARY KEY, target TEXT, owner TEXT, status TEXT DEFAULT 'uploading')")

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.temp / 'transfers.sqlite3', timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def lock(self, uid):
        with self.guard:
            return self.locks.setdefault(uid, threading.Lock())

    def path(self, raw, allow_root=False, base=None):
        base = base or self.shared
        if not isinstance(raw, str):
            raise Problem('Caminho inválido.')
        if not raw and allow_root:
            return base
        parts = raw.replace('\\', '/').split('/')
        for part in parts:
            if (not part or part in ('.', '..') or len(part) > 200 or
                re.search(r'[<>:"|?*\x00-\x1f]', part) or part.endswith((' ', '.')) or
                re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', part, re.I)):
                raise Problem('Nome de arquivo ou pasta inválido para Windows.')
        path = base.joinpath(*parts)
        if not path.resolve().is_relative_to(base.resolve()) or any(p.is_symlink() or getattr(os.path, 'isjunction', lambda _: False)(p) for p in [path, *path.parents] if p != self.shared.parent):
            raise Problem('Caminho não permitido.', 403)
        return path


class Handler(BaseHTTPRequestHandler):
    server_version = 'DropAgil/1.0'

    @property
    def app(self):
        return self.server.app

    def log_message(self, fmt, *args):
        # Não registrar nomes de arquivos, códigos ou tokens.
        pass

    def headers_base(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")

    def reply(self, data, status=200, content='application/json; charset=utf-8', cookie=None):
        payload = json.dumps(data, ensure_ascii=False).encode() if content.startswith('application/json') else data
        self.send_response(status)
        self.headers_base()
        self.send_header('Content-Type', content)
        self.send_header('Content-Length', str(len(payload)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    def body(self):
        size = self.length()
        if size > 16384:
            raise Problem('Solicitação muito grande.', 413)
        try:
            value = json.loads(self.rfile.read(size))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise Problem('Dados inválidos.')

    def length(self):
        if self.headers.get('Transfer-Encoding'):
            raise Problem('Use Content-Length.', 411)
        try:
            value = int(self.headers.get('Content-Length', '0'))
            if value < 0:
                raise ValueError()
            return value
        except ValueError:
            raise Problem('Tamanho inválido.')

    def session(self):
        authorization = self.headers.get('Authorization', '')
        if authorization.startswith('Bearer '):
            token = authorization[7:]
            if len(token) > 200:
                raise Problem('Pareamento inválido.', 401)
            with self.app.db() as db:
                paired = db.execute('SELECT name FROM pairings WHERE digest=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not paired:
                raise Problem('Conecte o aplicativo novamente com o código.', 401)
            with self.app.guard:
                session = {'name': paired['name'], 'ip':self.client_address[0], 'seen':time.time(), 'expires':time.time()+86400}
                self.app.sessions['paired:' + hashlib.sha256(token.encode()).hexdigest()] = session
            return session
        cookies = http.cookies.SimpleCookie()
        try:
            cookies.load(self.headers.get('Cookie', ''))
            token = cookies['dropagil'].value
        except (KeyError, http.cookies.CookieError):
            raise Problem('Digite o código exibido no computador.', 401)
        with self.app.guard:
            session = self.app.sessions.get(token)
            if not session or session['expires'] < time.time():
                self.app.sessions.pop(token, None)
                raise Problem('Acesso expirado. Conecte novamente.', 401)
            session['seen'] = time.time()
        return session

    def signin(self, name):
        token = secrets.token_urlsafe(32)
        with self.app.guard:
            self.app.sessions[token] = {'name': str(name or 'Dispositivo')[:50], 'ip': self.client_address[0], 'seen': time.time(), 'expires': time.time() + 86400}
        self.reply({'ok': True}, cookie=f'dropagil={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400')

    def device_identity(self):
        authorization = self.headers.get('Authorization', '')
        if authorization.startswith('Bearer '):
            source = authorization
        elif self.client_address[0] == '127.0.0.1':
            source = 'local-computer'
        else:
            source = self.headers.get('Cookie', '')
        return hashlib.sha256(source.encode()).hexdigest()[:32]

    def private_root(self, uid):
        return self.app.temp / 'direct' / uid

    def discard_delivery(self, uid, db, state):
        root = self.private_root(uid)
        if root.exists():
            if root.is_symlink() or getattr(os.path, 'isjunction', lambda _:False)(root):
                raise Problem('Pasta de entrega inválida.',403)
            shutil.rmtree(root)
        db.execute('UPDATE routing SET status=? WHERE upload_id=?',(state,uid))

    def validate_request(self):
        if time.monotonic() - self.app.address_time > 15:
            self.app.ips = addresses()
            self.app.address_time = time.monotonic()
        host = self.headers.get('Host', '')
        hostname = urlsplit('http://' + host).hostname
        if hostname not in ['localhost', '127.0.0.1', *self.app.ips]:
            raise Problem('Endereço de acesso não permitido.', 403)
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + host:
            raise Problem('Origem não permitida.', 403)
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise Problem('Origem não permitida.', 403)

    def do_GET(self):
        self.dispatch()

    def do_HEAD(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def do_PUT(self):
        self.dispatch()

    def do_DELETE(self):
        self.dispatch()

    def dispatch(self):
        self.connection.settimeout(120)
        try:
            self.validate_request()
            self.route()
        except Problem as exc:
            self.reply({'error': exc.message}, exc.status)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except OSError as exc:
            try:
                self.reply({'error': 'Sem espaço em disco.' if exc.errno == 28 else 'Não foi possível acessar o arquivo. Verifique espaço e permissões.'}, 507 if exc.errno == 28 else 500)
            except OSError:
                pass
        except Exception:
            self.reply({'error': 'Falha interna. Tente novamente.'}, 500)

    def route(self):
        url = urlsplit(self.path)
        route, query, method = url.path, parse_qs(url.query), self.command
        arg = lambda key, default='': query.get(key, [default])[0]
        if route in ('/', '/app.js', '/devices.js', '/transfer-groups.js', '/style.css', '/favicon.svg') and method in ('GET', 'HEAD'):
            file = BASE / 'public' / ('index.html' if route == '/' else route[1:])
            return self.reply(file.read_bytes(), content=mimetypes.guess_type(file.name)[0] or 'text/plain')
        if route == '/api/login' and method == 'POST':
            data = self.body()
            ip, now = self.client_address[0], time.time()
            with self.app.guard:
                recent = [t for t in self.app.attempts.get(ip, []) if now - t < 300]
                if len(recent) >= 8:
                    raise Problem('Muitas tentativas. Aguarde 5 minutos.', 429)
                recent.append(now)
                self.app.attempts[ip] = recent
            if not secrets.compare_digest(str(data.get('pin', '')), self.app.pin):
                raise Problem('Código incorreto. Confira no computador.', 401)
            return self.signin(data.get('name'))
        if route == '/api/local-login' and method == 'POST':
            self.body()
            if self.client_address[0] != '127.0.0.1':
                raise Problem('Disponível apenas no computador servidor.', 403)
            return self.signin('Computador principal')
        session = self.session()
        identity = self.device_identity()
        if route == '/api/devices' and method in ('GET','POST'):
            with self.app.db() as db:
                if method == 'POST':
                    data = self.body()
                    name = str(data.get('name') or session['name'])[:50]
                    db.execute('INSERT INTO devices VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,seen=excluded.seen', (identity,name,time.time()))
                devices = [dict(row) for row in db.execute('SELECT id,name FROM devices WHERE seen>? AND id!=?',(time.time()-40,identity))]
            return self.reply({'id':identity,'devices':devices})
        if route == '/api/inbox' and method == 'GET':
            with self.app.db() as db:
                items = [dict(row) for row in db.execute("SELECT u.id,u.path,u.size,r.status,d.name AS sender FROM uploads u JOIN routing r ON u.id=r.upload_id LEFT JOIN devices d ON d.id=r.owner WHERE r.target=? AND r.status IN ('ready','accepted') AND u.state='done'",(identity,))]
            return self.reply({'items':items})
        delivery = re.fullmatch(r'/api/inbox/([a-f0-9]{32})(/download)?',route)
        if delivery:
            uid, download = delivery.groups()
            with self.app.guard, self.app.db() as db:
                row=db.execute('SELECT u.*,r.target,r.status FROM uploads u JOIN routing r ON u.id=r.upload_id WHERE u.id=?',(uid,)).fetchone()
                if not row or row['target'] != identity:
                    raise Problem('Entrega não encontrada.',404)
                if method == 'POST' and not download:
                    action = self.body().get('action')
                    if action not in ('accept','reject','received'):
                        raise Problem('Ação inválida.')
                    if row['status'] not in ('ready','accepted'):
                        return self.reply({'ok':True,'status':row['status']})
                    if action == 'received' and row['status'] != 'accepted':
                        raise Problem('Aceite a entrega primeiro.',409)
                    if action == 'accept':
                        db.execute("UPDATE routing SET status='accepted' WHERE upload_id=?",(uid,))
                    else:
                        self.discard_delivery(uid,db,'received' if action=='received' else 'rejected')
                    return self.reply({'ok':True})
                if method in ('GET','HEAD') and download and row['status']=='accepted':
                    file=self.app.path(row['path'],base=self.private_root(uid))
                else:
                    raise Problem('Aceite a entrega antes de baixar.',403)
            return self.download(file)
        if route == '/api/pair' and method == 'POST':
            data = self.body()
            token = secrets.token_urlsafe(40)
            with self.app.db() as db:
                db.execute('INSERT INTO pairings VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), str(data.get('name') or 'Android')[:50], time.time()))
            return self.reply({'token':token})
        if route == '/api/revoke-pairings' and method == 'POST':
            self.body()
            if self.client_address[0] != '127.0.0.1':
                raise Problem('Disponível apenas no computador.',403)
            with self.app.db() as db:
                db.execute('DELETE FROM pairings')
            with self.app.guard:
                self.app.sessions = {key:value for key,value in self.app.sessions.items() if not key.startswith('paired:')}
            return self.reply({'ok':True})
        if route == '/api/logout' and method == 'POST':
            self.body()
            cookies = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
            with self.app.guard:
                self.app.sessions.pop(cookies['dropagil'].value, None)
            return self.reply({'ok': True}, cookie='dropagil=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict')
        if route == '/api/status' and method == 'GET':
            local = self.client_address[0] == '127.0.0.1'
            with self.app.guard:
                devices = list({s['ip']: {'name': s['name'], 'local': s['ip'] == self.client_address[0]} for s in self.app.sessions.values() if time.time() - s['seen'] < 30 and s['expires'] > time.time()}.values())
            usage = shutil.disk_usage(self.app.shared)
            return self.reply({'name': socket.gethostname(), 'urls': [f'http://{ip}:{self.app.port}' for ip in self.app.ips], 'pin': self.app.pin if local else None, 'local': local, 'free': usage.free, 'chunkSize': CHUNK, 'devices': devices, 'folder': str(self.app.shared) if local else None})
        if route == '/api/open-folder' and method == 'POST':
            self.body()
            if self.client_address[0] != '127.0.0.1' or os.name != 'nt':
                raise Problem('Abra a pasta pelo computador principal.', 403)
            os.startfile(self.app.shared)
            return self.reply({'ok': True})
        if route == '/api/qr' and method == 'GET':
            target = arg('url')
            if target not in [f'http://{ip}:{self.app.port}' for ip in self.app.ips]:
                raise Problem('Endereço inválido.')
            try:
                import qrcode
                import qrcode.image.svg
            except ImportError:
                raise Problem('QR indisponível. Digite o endereço no celular.', 503)
            out = io.BytesIO()
            qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage, border=2).save(out)
            return self.reply(out.getvalue(), content='image/svg+xml')
        if route == '/api/files' and method == 'DELETE':
            data = self.body()
            with self.app.guard, self.app.db() as db:
                target = self.app.path(data.get('path'))
                if not target.exists():
                    raise Problem('Arquivo ou pasta não encontrado.', 404)
                relative = target.relative_to(self.app.shared).as_posix()
                affected = [row for row in db.execute('SELECT id,path,state FROM uploads')
                            if row['path'].casefold() == relative.casefold() or
                            row['path'].casefold().startswith(relative.casefold() + '/')]
                private_ids = {row[0] for row in db.execute('SELECT upload_id FROM routing')}
                affected = [row for row in affected if row['id'] not in private_ids]
                if any(row['state'] == 'pending' for row in affected):
                    raise Problem('Há um envio para este arquivo ou pasta. Conclua ou cancele o envio antes de apagar.', 409)
                # Reject links and Windows junctions throughout a recursive deletion.
                if target.is_dir() and any(
                    p.is_symlink() or getattr(os.path, 'isjunction', lambda _: False)(p) or not p.resolve().is_relative_to(self.app.shared)
                    for p in target.rglob('*')):
                    raise Problem('A pasta contém um link. Remova o link pelo computador primeiro.', 403)
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                db.executemany('DELETE FROM uploads WHERE id=?', [(row['id'],) for row in affected])
            return self.reply({'ok': True})
        if route == '/api/files' and method == 'GET':
            folder = self.app.path(arg('path'), True)
            if not folder.is_dir():
                raise Problem('Pasta não encontrada.', 404)
            items = []
            for p in folder.iterdir():
                if p.is_symlink() or not p.resolve().is_relative_to(self.app.shared):
                    continue
                info = p.stat()
                items.append({'name': p.name, 'path': p.relative_to(self.app.shared).as_posix(), 'directory': p.is_dir(), 'size': info.st_size if p.is_file() else None, 'modified': info.st_mtime})
            return self.reply({'items': sorted(items, key=lambda x: (not x['directory'], x['name'].lower()))})
        if route == '/api/download' and method in ('GET', 'HEAD'):
            return self.download(self.app.path(arg('path')))
        if route == '/api/android-apk' and method in ('GET','HEAD'):
            return self.download(BASE / 'DropAgil-Android.apk')
        if route == '/api/zip' and method == 'GET':
            return self.archive(self.app.path(arg('path')))
        if route == '/api/uploads' and method == 'POST':
            data = self.body()
            path = self.app.path(data.get('path'))
            target = str(data.get('target') or '')
            size = data.get('size')
            if type(size) is not int or size < 0 or size > 2**53 - 1:
                raise Problem('Tamanho inválido.')
            fingerprint = str(data.get('fingerprint', ''))
            with self.app.guard, self.app.db() as db:
                resume = db.execute('SELECT * FROM uploads WHERE id=?', (str(data.get('id', '')),)).fetchone()
                if resume:
                    routing = db.execute('SELECT * FROM routing WHERE upload_id=?',(resume['id'],)).fetchone()
                    if (routing and (routing['owner'] != identity or routing['target'] != target)) or (not routing and target):
                        raise Problem('O destino deste envio mudou. Inicie um novo envio.',409)
                if resume and resume['size'] == size and resume['fingerprint'] == fingerprint:
                    return self.reply(dict(resume))
                if target and not db.execute('SELECT 1 FROM devices WHERE id=?',(target,)).fetchone():
                    raise Problem('Dispositivo não encontrado. Ative o recebimento nele.',404)
                if size > shutil.disk_usage(self.app.shared).free - 64 * 1024 * 1024:
                    raise Problem('Não há espaço suficiente no computador.', 507)
                uid = secrets.token_hex(16)
                base = self.private_root(uid) if target else self.app.shared
                path = self.app.path(data.get('path'),base=base)
                original, index = path, 1
                while path.exists() or (not target and db.execute('SELECT 1 FROM uploads WHERE path=? AND state=? AND id NOT IN (SELECT upload_id FROM routing)', (path.relative_to(base).as_posix(), 'pending')).fetchone()):
                    path = original.with_name(f'{original.stem} ({index}){original.suffix}')
                    index += 1
                (self.app.temp / (uid + '.part')).touch()
                relative = path.relative_to(base).as_posix()
                db.execute('INSERT INTO uploads VALUES (?,?,?,?,?,?)', (uid, relative, size, 0, 'pending', fingerprint))
                if target:
                    db.execute('INSERT OR IGNORE INTO devices VALUES (?,?,?)',(identity,session['name'],0))
                    db.execute('INSERT INTO routing(upload_id,target,owner) VALUES (?,?,?)',(uid,target,identity))
            return self.reply({'id': uid, 'path': relative, 'size': size, 'offset': 0, 'state': 'pending'})
        match = re.fullmatch(r'/api/uploads/([a-f0-9]{32})(/complete)?', route)
        if match:
            uid, complete = match.groups()
            if method == 'POST':
                self.body()
            with self.app.lock(uid), self.app.db() as db:
                row = db.execute('SELECT * FROM uploads WHERE id=?', (uid,)).fetchone()
                if not row:
                    raise Problem('Transferência não encontrada. Selecione o arquivo novamente.', 404)
                routing = db.execute('SELECT * FROM routing WHERE upload_id=?',(uid,)).fetchone()
                if routing and routing['owner'] != identity:
                    raise Problem('Transferência não encontrada.',404)
                base = self.private_root(uid) if routing else self.app.shared
                part = self.app.temp / (uid + '.part')
                if method == 'GET':
                    return self.reply(dict(row))
                if method == 'DELETE' and not complete:
                    part.unlink(missing_ok=True)
                    db.execute('DELETE FROM uploads WHERE id=?', (uid,))
                    if routing:
                        self.discard_delivery(uid,db,'cancelled')
                        db.execute('DELETE FROM routing WHERE upload_id=?',(uid,))
                    db.commit()
                    return self.reply({'ok': True})
                if row['state'] == 'done':
                    return self.reply(dict(row))
                if method == 'POST' and complete:
                    if row['offset'] != row['size']:
                        raise Problem('O arquivo ainda não terminou de enviar.', 409)
                    destination = self.app.path(row['path'],base=base)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if part.exists():
                        with self.app.guard:
                            original, index = destination, 1
                            while destination.exists():
                                destination = original.with_name(f'{original.stem} ({index}){original.suffix}')
                                index += 1
                            # Persistir destino antes de mover permite recuperar interrupção no commit.
                            db.execute('UPDATE uploads SET path=? WHERE id=?', (destination.relative_to(base).as_posix(), uid))
                            db.commit()
                            part.rename(destination)
                    elif not destination.is_file() or destination.stat().st_size != row['size']:
                        raise Problem('Arquivo temporário indisponível.', 409)
                    db.execute('UPDATE uploads SET state=? WHERE id=?', ('done', uid))
                    if routing:
                        db.execute("UPDATE routing SET status='ready' WHERE upload_id=?",(uid,))
                    db.commit()
                    return self.reply({'state': 'done', 'path': destination.relative_to(base).as_posix(), 'offset': row['size']})
                if method == 'PUT' and not complete:
                    length = self.length()
                    try:
                        offset = int(self.headers.get('Upload-Offset', '-1'))
                    except ValueError:
                        raise Problem('Posição inválida.')
                    if offset != row['offset']:
                        raise Problem('Posição alterada. Retome a transferência.', 409)
                    if length <= 0 or length > CHUNK or offset + length > row['size']:
                        raise Problem('Bloco inválido.', 413)
                    if shutil.disk_usage(self.app.temp).free < length + 16 * 1024 * 1024:
                        raise Problem('Sem espaço em disco.', 507)
                    digest = hashlib.sha256()
                    with part.open('r+b') as out:
                        out.truncate(offset)
                        out.seek(offset)
                        remaining = length
                        while remaining:
                            block = self.rfile.read(min(1024 * 1024, remaining))
                            if not block:
                                raise Problem('Envio interrompido. Retome para continuar.', 409)
                            out.write(block)
                            digest.update(block)
                            remaining -= len(block)
                        out.flush()
                        os.fsync(out.fileno())
                    expected = self.headers.get('X-Chunk-SHA256')
                    if expected and not secrets.compare_digest(expected, digest.hexdigest()):
                        raise Problem('Bloco corrompido. Envie novamente.', 409)
                    db.execute('UPDATE uploads SET offset=? WHERE id=?', (offset + length, uid))
                    db.commit()
                    return self.reply({'offset': offset + length})
        raise Problem('Não encontrado.', 404)

    def attachment(self, name):
        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(name, safe=''))

    def download(self, path):
        if not path.is_file():
            raise Problem('Arquivo não encontrado.', 404)
        with path.open('rb') as stream:
            stat = os.fstat(stream.fileno())
            size, start, end = stat.st_size, 0, stat.st_size - 1
            etag = f'"{stat.st_mtime_ns:x}-{size:x}"'
            partial = self.headers.get('Range')
            if self.headers.get('If-Range', etag) != etag:
                partial = None
            if partial:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', partial)
                if not match or not any(match.groups()) or size == 0:
                    return self.range_error(size)
                first, last = match.groups()
                if first:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                else:
                    start = max(0, size - int(last))
                if start > end or start >= size:
                    return self.range_error(size)
            self.send_response(206 if partial else 200)
            self.headers_base()
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('ETag', etag)
            self.attachment(path.name)
            self.send_header('Content-Length', str(max(0, end - start + 1)))
            if partial:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            if self.command == 'HEAD':
                return
            stream.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                block = stream.read(min(1024 * 1024, remaining))
                if not block:
                    break
                self.wfile.write(block)
                remaining -= len(block)

    def range_error(self, size):
        self.send_response(416)
        self.headers_base()
        self.send_header('Content-Range', f'bytes */{size}')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def archive(self, path):
        if not path.is_dir():
            raise Problem('Pasta não encontrada.', 404)
        self.send_response(200)
        self.headers_base()
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Connection', 'close')
        self.attachment(path.name + '.zip')
        self.end_headers()
        self.close_connection = True
        # ZIP sem compressão, gerado direto na conexão, com suporte a ZIP64.
        with zipfile.ZipFile(self.wfile, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for root, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
                directory = Path(root)
                archive.mkdir(directory.relative_to(path.parent).as_posix() + '/')
                for name in files:
                    source = directory / name
                    if source.is_symlink() or not source.resolve().is_relative_to(self.app.shared):
                        continue
                    info = zipfile.ZipInfo.from_file(source, source.relative_to(path.parent).as_posix())
                    with source.open('rb') as inp, archive.open(info, 'w', force_zip64=True) as out:
                        shutil.copyfileobj(inp, out, 1024 * 1024)


def main():
    parser = argparse.ArgumentParser(description='DropAgíl — arquivos na sua rede')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--data-dir', default=str(BASE))
    args = parser.parse_args()
    app = App(args.data_dir, args.port)
    try:
        server = ThreadingHTTPServer(('0.0.0.0', args.port), Handler)
    except OSError as exc:
        print(f'Não foi possível iniciar na porta {args.port}: {exc}', flush=True)
        return
    server.app = app
    print(f'\nDropAgíl está pronto!\nNo computador: http://localhost:{args.port}\nCódigo de acesso: {app.pin}\nArquivos: {app.shared}', flush=True)
    for ip in app.ips:
        print(f'No celular: http://{ip}:{args.port}', flush=True)
    print('Mantenha esta janela aberta. Ctrl+C para encerrar.\n', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
