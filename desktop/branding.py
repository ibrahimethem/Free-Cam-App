"""Existing product artwork shared by iOS and desktop; no redesign."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ICON = ROOT / "ios/FreeCam/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"


def runtime_icon():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets/AppIcon-1024.png"
    return SOURCE_ICON


def build_icons(output):
    from PIL import Image
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE_ICON) as source:
        if source.size != (1024, 1024):
            raise ValueError("Product artwork must be 1024 × 1024")
        picture = source.convert("RGBA")
        picture.save(output / "NoSubStudio.ico", sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
        picture.save(output / "NoSubStudio.icns", sizes=[(n, n) for n in (16, 32, 64, 128, 256, 512, 1024)])
    version = (ROOT / "desktop/VERSION").read_text().strip()
    numbers = tuple(int(part) for part in version.split(".")) + (0,)
    if len(numbers) != 4 or any(not 0 <= n <= 65535 for n in numbers):
        raise ValueError("VERSION must contain three unsigned 16-bit integers")
    # PyInstaller version-resource format, evaluated only at build time.
    (output / "windows-version.txt").write_text(f'''VSVersionInfo(
      ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, mask=0x3f,
        flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
      kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'İbrahim Ethem Karalı'),
        StringStruct('FileDescription', 'NoSub Studio'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('ProductName', 'NoSub Studio'),
        StringStruct('ProductVersion', '{version}'),
        StringStruct('OriginalFilename', 'FreeCam.exe')])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])])''', encoding="utf-8")
    return output
