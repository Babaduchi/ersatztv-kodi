#!/usr/bin/env python3
import hashlib
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin.video.ersatztv"
REPOSITORY = ROOT / "repository.babaduchi.ersatztv"


def version(addon_dir):
    return ET.parse(addon_dir / "addon.xml").getroot().attrib["version"]


def zip_addon(addon_dir, destination):
    with ZipFile(destination, "w", ZIP_DEFLATED) as package:
        for path in sorted(addon_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                package.write(path, path.relative_to(ROOT).as_posix())


def digest(path, algorithm):
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "kodi-repository-site").resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    addons = [REPOSITORY, PLUGIN]
    xml = ET.Element("addons")
    for addon_dir in addons:
        xml.append(ET.parse(addon_dir / "addon.xml").getroot())
        addon_id = addon_dir.name
        target = output / addon_id
        target.mkdir()
        addon_version = version(addon_dir)
        archive = target / "{}-{}.zip".format(addon_id, addon_version)
        zip_addon(addon_dir, archive)
        (target / (archive.name + ".sha256")).write_text(digest(archive, "sha256") + "\n", encoding="ascii")
        shutil.copy2(addon_dir / "addon.xml", target / "addon.xml")
        icon = addon_dir / "icon.png"
        if icon.exists():
            shutil.copy2(icon, target / "icon.png")

    tree = ET.ElementTree(xml)
    ET.indent(tree, space="  ")
    index = output / "addons.xml"
    tree.write(index, encoding="UTF-8", xml_declaration=True)
    (output / "addons.xml.md5").write_text(digest(index, "md5") + "\n", encoding="ascii")
    (output / "index.html").write_text(
        "<!doctype html><title>Babaduchi ErsatzTV Kodi Repository</title>"
        "<h1>Babaduchi ErsatzTV Kodi Repository</h1>"
        "<p>Install the repository ZIP below once, then install ErsatzTV from Kodi's repository browser.</p>"
        '<p><a href="repository.babaduchi.ersatztv/repository.babaduchi.ersatztv-{}.zip">Download repository installer</a></p>'.format(version(REPOSITORY)),
        encoding="utf-8")
    print("Built Kodi repository at", output)


if __name__ == "__main__":
    main()
