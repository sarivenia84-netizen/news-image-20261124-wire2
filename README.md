[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/sarivenia84-netizen/news-image-20261124-wire2/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/sarivenia84-netizen/news-image-20261124-wire2/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

# THE WIRE — 24 November 2026

Entry for [news-image-20261124](https://make.fun/bounty/news-image-20261124)

A competition entry for the make.fun "news-image-20261124" bounty: a deterministic, pure-Python-stdlib renderer that produces a 1024x1024 newspaper front page titled "THE WIRE — 24 NOVEMBER 2026". Every story is parsed at startup from `facts.md` (the editorial fact sheet), so the data lives in one place and is never duplicated in code. Text is drawn with an in-house 5x7 bitmap font encoded as hex row masks, illustrations are built from simple geometric primitives, and the PNG is written by hand (zlib + struct) with no third-party packages or network access. Running the renderer twice on the same input yields byte-identical output.

## Run

```
MAKEFUN_OUTPUT_DIR=/tmp/wire-out python3 -P -s main.py
```

The image is written to `$MAKEFUN_OUTPUT_DIR/entry.png`, or `out/entry.png` when the variable is unset.

## License

MIT. See [LICENSE](LICENSE) — Copyright (c) 2026 sarivenia84-netizen.
