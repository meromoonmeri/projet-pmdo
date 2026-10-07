"""Rebuild the tested PVC1 Ground and create installable/editable ZIP deliverables."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import build as pvc1


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def add_tree(z: zipfile.ZipFile, source: Path, arcroot: str) -> None:
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        z.write(path, str(Path(arcroot) / path.relative_to(source)))


def package() -> dict:
    manifest = pvc1.build()
    out, stage = pvc1.OUT, pvc1.STAGE
    project_zip = out / "PVC1_projet_pmdo_0812.zip"
    layers_zip = out / "PVC1_calques_png_8px.zip"

    for dst in (project_zip, layers_zip):
        dst.unlink(missing_ok=True)

    with zipfile.ZipFile(project_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        add_tree(z, stage, "PVC1_PMDO")

    with zipfile.ZipFile(layers_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        add_tree(z, out / "maps/passage", "PVC1_calques")
        add_tree(z, out / "animation", "PVC1_calques/animation")
        for raw in (pvc1.REF, pvc1.REF_ANIM, pvc1.GUIDE, pvc1.FLOOR):
            z.write(raw, str(Path("PVC1_calques/references") / raw.name))
        for src in (pvc1.HERE / "README.md", pvc1.HERE / "README_PACK.md", pvc1.HERE / "build.py",
                    pvc1.HERE / "test_build.py", pvc1.HERE / "package.py"):
            z.write(src, str(Path("PVC1_calques/source") / src.name))
        z.write(out / "manifest.json", "PVC1_calques/manifest.json")
        z.write(out / "README.md", "PVC1_calques/README.md")

    for path in (project_zip, layers_zip):
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                raise AssertionError(f"ZIP endommagé: {path.name}:{bad}")
    with zipfile.ZipFile(project_zip) as z:
        names = set(z.namelist())
        required = {"PVC1_PMDO/Mod.xml", f"PVC1_PMDO/Data/Ground/{pvc1.ASSET}.rsground",
                    "PVC1_PMDO/Content/Tile/index.idx", "PVC1_PMDO/INSTALLER.py"}
        if not required <= names:
            raise AssertionError(f"Fichiers PMDO absents: {required - names}")
    with zipfile.ZipFile(layers_zip) as z:
        names = set(z.namelist())
        required = {"PVC1_calques/PVC1_calques.ora", "PVC1_calques/references/D17P33A_ROM.png",
                    "PVC1_calques/references/D17P33A_animations.webp",
                    "PVC1_calques/references/decor_magenta.png", "PVC1_calques/manifest.json"}
        if not required <= names:
            raise AssertionError(f"Références/calques absents: {required - names}")

    files = [project_zip, layers_zip, pvc1.REF, pvc1.REF_ANIM, pvc1.GUIDE, pvc1.FLOOR,
             out / "maps/passage/review/PVC1_scene_t000.png",
             out / "maps/passage/review/PVC1_animation_12_phases.webp",
             out / "SESSION_NOTE.md", pvc1.ROOT / "apercu_passage_veines_cristal_v1.html"]
    checksums = {p.name: {"sha256": digest(p), "bytes": p.stat().st_size} for p in files}
    (out / "SHA256SUMS.json").write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["packs"] = {p.name: checksums[p.name] for p in (project_zip, layers_zip)}
    manifest["deliverable_checksums"] = checksums
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = package()
    print(json.dumps({"packs": result["packs"], "path_16px": result["collision"]["north_south_path_16x16"],
                      "layers": len(result["map"]["layers"]), "loop_ticks": result["animation"]["composite_loop_ticks"]},
                     ensure_ascii=False, indent=2))
