"""Compilação sem Gradle, usando AAPT2, javac, D8 e apksigner oficiais."""
from pathlib import Path
import os
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ANDROID = ROOT / 'android'
SDK = ROOT / '.work' / 'android-sdk'
BUILD = ROOT / '.work' / 'android-build'
JAVA = Path(os.environ.get('JAVA_HOME', r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot')) / 'bin'


def run(*args):
    subprocess.run([str(a) for a in args],check=True,cwd=ROOT)


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    platform = next((SDK / 'platform').rglob('android.jar'))
    tools = next((SDK / 'build-tools').rglob('aapt2.exe')).parent
    classes,generated,dex = BUILD/'classes',BUILD/'generated',BUILD/'dex'
    for folder in (classes,generated,dex):folder.mkdir(exist_ok=True)
    run(tools/'aapt2.exe','compile','--dir',ANDROID/'res','-o',BUILD/'resources.zip')
    run(tools/'aapt2.exe','link','-o',BUILD/'unsigned.apk','--manifest',ANDROID/'AndroidManifest.xml','-I',platform,'--java',generated,BUILD/'resources.zip')
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
    print('APK:',output,output.stat().st_size,'bytes')


if __name__ == '__main__':main()
