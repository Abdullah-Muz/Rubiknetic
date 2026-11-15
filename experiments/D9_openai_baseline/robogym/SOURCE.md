# Source of the vendored OpenAI files

The files in this folder are copied unchanged from OpenAI's **robogym** repository. Credit for the cube model belongs
to OpenAI (robogym authors; the model is the simulated Rubik's cube of OpenAI et al., "Solving Rubik's Cube with a
Robot Hand", 2019). Rubiknetic did not author them.

- Repository: https://github.com/openai/robogym
- Pinned commit: `9ff1111fd557b1a01911d7d8c9d59a453071c96e`
- Downloaded: 2026-11-14

| File | Upstream path | sha256 |
|---|---|---|
| `rubik_perpendicular.xml` | `robogym/assets/xmls/rubik/rubik_perpendicular.xml` | `aa87bb3ebdf12926c2544057325b2d521404cee6adedf0c69e1222cff81626c1` |
| `roundcube.msh` | `robogym/assets/stls/roundcube.msh` | `ef5c3584b1883a0f00dd263c7643a18eedac4e224fefe13eeb3a4c96e188eb65` |
| `LICENSE` | `LICENSE` (repository root) | `271d45b4b4594ff76b6209c12e7f8d183e8d51ea9ea67e63b97238d62f37335b` |

The texture PNGs referenced by the XML (`cube/material*.png`) are not vendored; `../openai_cube.py` strips the
`<texture>`/`<material>` elements at load time (rendering only, no physics effect). The vendored files themselves are
not edited.

## License notice (MIT)

```
MIT License

Copyright (c) 2020 OpenAI
```

The full MIT license text is in `LICENSE` in this folder and must be kept with these files.
