# Aurora Cabin

A procedural night-sky artwork in pure Python (standard library only).

A log cabin with warm glowing windows sits among pine trees under
curtains of northern lights, and the aurora, the moon and the cabin
light all reflect in a still lake. Every pixel is computed by
`main.py`; a fixed-seed PRNG places the stars, so the PNG written to
`/output/entry.png` (720x720) is byte-identical on every run.

Run it:

```sh
python3 main.py            # writes /output/entry.png
OUTPUT_DIR=. python3 main.py
```

Entry for make.fun's coolest-art-01 competition. MIT licensed.
