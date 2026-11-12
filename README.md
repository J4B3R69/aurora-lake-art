# Aurora Lake

A procedural northern-lights artwork, drawn pixel by pixel by a single
Python program (`main.py`, standard library only).

The scene: three aurora ribbons with vertical rays over a star field and
a full moon, two mountain ridgelines, and the whole sky reflected in a
rippled mountain lake. Every pixel is a fixed mathematical function of
its position, so the program is fully deterministic: run it twice and
the PNG bytes are identical.

Run it the way the grader does:

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png (720x720, about 210 KB)
```
