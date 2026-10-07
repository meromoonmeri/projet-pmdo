"""Package the tested CPL1 editor project and editable PNG layers."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import build as cpl1


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package() -> dict:
    manifest = cpl1.build()
    out = cpl1.OUT
    stage = cpl1.STAGE
    project_zip = out / "CPL1_projet_pmdo_0812.zip"
    layers_zip = out / "CPL1_calques_png_8px.zip"
    for dst, source, arcroot in ((project_zip, stage, "CPL1_PMDO"),
                                 (layers_zip, out / "maps/passage", "CPL1_calques")):
        if dst.exists():
            dst.unlink()
        with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for path in sorted(p for p in source.rglob("*") if p.is_file()):
                z.write(path, str(Path(arcroot) / path.relative_to(source)))
            if dst == layers_zip:
                for reference in (cpl1.REF, cpl1.GUIDE):
                    z.write(reference, str(Path(arcroot) / "references" / reference.name))
    for path in (project_zip, layers_zip):
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                raise AssertionError(f"ZIP endommagé: {path.name}:{bad}")
    with zipfile.ZipFile(layers_zip) as z:
        names = set(z.namelist())
        required = {"CPL1_calques/references/D13P11A_ROM.png",
                    "CPL1_calques/references/CPL1_layout_reference.png"}
        if not required <= names:
            raise AssertionError(f"Références absentes du ZIP des calques: {required-names}")
    checksums = {
        "CPL1_projet_pmdo_0812.zip": digest(project_zip),
        "CPL1_calques_png_8px.zip": digest(layers_zip),
        "CPL1_layout_reference.png": cpl1.sha256(cpl1.GUIDE),
        cpl1.REF.name: cpl1.sha256(cpl1.REF),
    }
    (out / "SHA256SUMS.json").write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["packs"] = {k: {"sha256": v, "bytes": (out / k).stat().st_size} for k, v in checksums.items()
                         if k.endswith(".zip")}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = package()
    print(json.dumps({"packs": result["packs"], "markers": result["collision"]["markers_px"],
                      "path_16px": result["collision"]["north_south_path_16x16"]}, ensure_ascii=False, indent=2))
