from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
dist = root / 'dist' / 'Shortify'
out = root / 'release'
out.mkdir(exist_ok=True)

if not dist.exists():
    raise SystemExit('Build first: run build.bat')

zip_path = shutil.make_archive(str(out / 'Shortify-windows-v0.1.0'), 'zip', dist)
print(f'Created: {zip_path}')
