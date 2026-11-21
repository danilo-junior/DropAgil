"""Create current Windows and source archives after compiling the EXE and APK."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent


def archive(name, files):
    with ZipFile(ROOT / name, 'w', ZIP_DEFLATED, compresslevel=6) as output:
        for file in sorted(set(files)):
            if file.is_file():
                output.write(file, 'DropAgil/' + file.relative_to(ROOT).as_posix())


def main():
    common = [ROOT / name for name in (
        'DropAgil-Android.apk', 'DropAgil-Android.version.json', 'README.md', 'Iniciar-DropAgil.bat',
        'Instalar-Windows.bat', 'Remover-Integracao-Windows.bat',
    )]
    if not (ROOT / 'DropAgil.exe').is_file() or not all(file.is_file() for file in common[:2]):
        raise RuntimeError('Compile o EXE e o APK com metadados antes de criar os pacotes.')
    archive('DropAgil-Windows.zip', common + [ROOT / 'DropAgil.exe'])
    source = [ROOT / name for name in ('.gitignore', 'requirements.txt', 'requirements-build.txt')]
    for pattern in ('*.py', 'public/*', 'android/README.md', 'android/AndroidManifest.xml',
                    'android/res/**/*', 'android/src/**/*.java', 'android/tools/*.py', 'tests/*'):
        source.extend(ROOT.glob(pattern))
    archive('DropAgil.zip', common + source)
    print('Pacotes:', ROOT / 'DropAgil-Windows.zip', ROOT / 'DropAgil.zip')


if __name__ == '__main__':
    main()
