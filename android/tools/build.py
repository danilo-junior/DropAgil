"""Compilação sem Gradle, usando AAPT2, javac, D8 e apksigner oficiais."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ANDROID = ROOT / 'android'
SDK = ROOT / '.work' / 'android-sdk'
BUILD = ROOT / '.work' / 'android-build'
JAVA = Path(os.environ.get('JAVA_HOME', r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot')) / 'bin'
METADATA = ROOT / 'DropAgil-Android.version.json'


def run(*args):
    subprocess.run([str(a) for a in args],check=True,cwd=ROOT)


def versioned_manifest():
    source = ANDROID / 'AndroidManifest.xml'
    manifest = ET.parse(source).getroot()
    android_ns = '{http://schemas.android.com/apk/res/android}'
    base_code = int(manifest.attrib[android_ns + 'versionCode'])
    base_name = manifest.attrib[android_ns + 'versionName']
    digest = hashlib.sha256()
    inputs = [source, *sorted((ANDROID / 'src').rglob('*.java')),
              *sorted(p for p in (ANDROID / 'res').rglob('*') if p.is_file())]
    for file in inputs:
        digest.update(file.relative_to(ANDROID).as_posix().encode('utf-8'))
        digest.update(file.read_bytes())
    source_hash = digest.hexdigest()
    try:
        previous = json.loads(METADATA.read_text('utf-8'))
    except (OSError, ValueError):
        previous = {}
    previous_code = previous.get('versionCode', 0)
    if type(previous_code) is not int:
        previous_code = 0
    same_source = previous.get('sourceSha256') == source_hash
    legacy_baseline = not previous.get('sourceSha256') and previous_code == base_code
    code = max(base_code, previous_code if same_source or legacy_baseline else previous_code + 1)
    name = previous.get('versionName', base_name) if same_source and code == previous_code else (
        base_name if code == base_code else f'{base_name}.{code - base_code}')
    text = source.read_text('utf-8')
    text = text.replace(f'android:versionCode="{base_code}"', f'android:versionCode="{code}"', 1)
    text = text.replace(f'android:versionName="{base_name}"', f'android:versionName="{name}"', 1)
    target = BUILD / 'AndroidManifest.xml'
    target.write_text(text, encoding='utf-8')
    return target, code, name, source_hash


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    build_manifest, version_code, version_name, source_hash = versioned_manifest()
    platform = next((SDK / 'platform').rglob('android.jar'))
    tools = next((SDK / 'build-tools').rglob('aapt2.exe')).parent
    classes,generated,dex = BUILD/'classes',BUILD/'generated',BUILD/'dex'
    for folder in (classes,generated,dex):folder.mkdir(exist_ok=True)
    run(tools/'aapt2.exe','compile','--dir',ANDROID/'res','-o',BUILD/'resources.zip')
    run(tools/'aapt2.exe','link','-o',BUILD/'unsigned.apk','--manifest',build_manifest,'-I',platform,'--java',generated,BUILD/'resources.zip')
    sources = list((ANDROID/'src').rglob('*.java'))+list(generated.rglob('*.java'))
    run(JAVA/'javac.exe','-encoding','UTF-8','--release','8','-classpath',platform,'-d',classes,*sources)
    run(JAVA/'jar.exe','cf',BUILD/'classes.jar','-C',classes,'.')
    run(JAVA/'java.exe','-cp',tools/'lib'/'d8.jar','com.android.tools.r8.D8','--min-api','29','--lib',platform,'--output',dex,BUILD/'classes.jar')
    with zipfile.ZipFile(BUILD/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as archive:
        for file in dex.glob('*.dex'):archive.write(file,file.name)
    run(tools/'zipalign.exe','-f','4',BUILD/'unsigned.apk',BUILD/'aligned.apk')
    key = ROOT / '.dropagil' / 'android-debug.keystore'
    key.parent.mkdir(exist_ok=True)
    if not key.exists():
        run(JAVA/'keytool.exe','-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','androiddebugkey','-dname','CN=DropAgil Local, O=DropAgil, C=BR','-keyalg','RSA','-keysize','2048','-validity','10000')
    output=ROOT/'DropAgil-Android.apk'
    run(JAVA/'java.exe','-jar',tools/'lib'/'apksigner.jar','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',output,BUILD/'aligned.apk')
    run(JAVA/'java.exe','-jar',tools/'lib'/'apksigner.jar','verify','--verbose',output)
    metadata={'versionCode':version_code,'versionName':version_name,'sourceSha256':source_hash,
              'size':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    METADATA.write_text(json.dumps(metadata,ensure_ascii=False),encoding='utf-8')
    print('APK:',output,output.stat().st_size,'bytes')


if __name__ == '__main__':main()
