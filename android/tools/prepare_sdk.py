"""Baixa as ferramentas oficiais mínimas do Android SDK com checksum validado."""
import hashlib
from pathlib import Path
import shutil
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2] / '.work' / 'android-sdk'
BASE = 'https://dl.google.com/android/repository/'


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    xml = urllib.request.urlopen(BASE + 'repository2-1.xml', timeout=60).read()
    tree = ET.fromstring(xml)
    for node in tree.iter():
        node.tag = node.tag.split('}')[-1]
    for package, name in [('platforms;android-35', 'platform'), ('build-tools;35.0.0', 'build-tools')]:
        marker = ROOT / name / '.ready'
        if marker.exists():
            continue
        remote = next(n for n in tree.iter('remotePackage') if n.attrib.get('path') == package)
        archive = next(a for a in remote.findall('./archives/archive') if a.findtext('host-os') in (None, 'windows'))
        complete = archive.find('complete')
        url = complete.findtext('url')
        destination = ROOT / (name + '.zip')
        print('Baixando', package, url, flush=True)
        with urllib.request.urlopen(BASE + url, timeout=120) as response, destination.open('wb') as out:
            shutil.copyfileobj(response, out, 1024 * 1024)
        checksum = complete.find('checksum')
        digest = hashlib.new(checksum.attrib.get('type', 'sha1'))
        with destination.open('rb') as inp:
            while chunk := inp.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != checksum.text.strip():
            raise RuntimeError('Checksum incorreto: ' + name)
        target = (ROOT / name).resolve()
        with zipfile.ZipFile(destination) as data:
            for item in data.infolist():
                if not (target / item.filename).resolve().is_relative_to(target):
                    raise RuntimeError('Caminho inválido no SDK')
            data.extractall(target)
        marker.write_text('ok')
        destination.unlink()
        print('Pronto:', name, flush=True)


if __name__ == '__main__':
    main()
