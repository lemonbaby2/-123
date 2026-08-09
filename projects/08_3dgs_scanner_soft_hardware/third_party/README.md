# Third-Party Reference Integration

This repository does not copy third-party source code by default.

Reasons:

- Several key HKU-MARS repositories are GPL-2.0, which may affect downstream product licensing if source is copied or linked directly.
- Some 3DGS reference implementations have custom research licenses.
- Keeping upstream projects as references or submodules makes updates and license review clearer.

## Optional Submodule Commands

Run these only after reviewing each upstream license:

```powershell
git submodule add https://github.com/hku-mars/FAST-LIVO2.git third_party/FAST-LIVO2
git submodule add https://github.com/hku-mars/GS-SDF.git third_party/GS-SDF
git submodule add https://github.com/HKUST-Aerial-Robotics/GS-LIVO.git third_party/GS-LIVO
git submodule add https://github.com/nerfstudio-project/gsplat.git third_party/gsplat
git submodule add https://github.com/isl-org/Open3D.git third_party/Open3D
```

For now, use `docs/references/` as the integrated knowledge index.
