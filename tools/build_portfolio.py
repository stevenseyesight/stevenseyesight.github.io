#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steven's Eyesight: подготовка на портфолиото.

Какво прави:
  1. Чете снимките от твоята папка "ws" (по папки: svatba, godej, balove, photoshoots, events, random)
  2. Смалява ги за сайта (голяма версия + малка за мозайката)
  3. Слага полупрозрачен воден знак с логото в центъра
  4. Маха скритата информация (EXIF, GPS местоположение)
  5. Дава на всяка снимка безлично име (без имена на хора) и пише js/portfolio-data.js

Оригиналите ти НЕ се променят.

Пускане:  python tools/build_portfolio.py
(или:     python tools/build_portfolio.py --ws "C:\\път\\до\\ws")
Добавил си нови снимки? Пусни го пак: старите се пропускат, прави се само за новите.
Искаш всичко наново (напр. промяна на водния знак)?  добави  --force
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    print("Липсва програмата Pillow. Напиши в същия прозорец:  pip install pillow")
    print("и после пусни скрипта отново.")
    sys.exit(1)

Image.MAX_IMAGE_PIXELS = None

SITE = Path(__file__).resolve().parent.parent
OUT_FULL = SITE / "images" / "portfolio" / "full"
OUT_THUMB = SITE / "images" / "portfolio" / "thumbs"
DATA_JS = SITE / "js" / "portfolio-data.js"
LOGO = SITE / "images" / "logo.png"

# папка в ws  ->  категория в сайта (филтър)
CATS = [
    ("svatba", "wedding"),
    ("godej", "engagement"),
    ("balove", "prom"),
    ("photoshoots", "photoshoot"),
    ("events", "events"),
    ("random", "daily"),
]
EXTS = {".jpg", ".jpeg", ".png", ".webp"}

SLIDESHOW_COUNT = 23  # колко снимки да има в слайдшоуто най-горе. 0 = НЕ пипай слайдшоуто (ползвам само моите снимки в images\slides)
FULL_MAX = 1800      # най-дълга страна на голямата снимка (px)
THUMB_W = 720        # ширина на малката снимка (px)
MARK_OPACITY = 0.10  # прозрачност на водния знак (0.10 = едва се вижда, 0.50 = ясно се вижда)
MARK_SIZE = 0.13     # височина на знака като част от снимката (0.13 = 13%)


def natural_key(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(p))]


def make_mark(target_h):
    logo = Image.open(LOGO).convert("RGBA")
    ratio = target_h / logo.height
    logo = logo.resize((max(1, round(logo.width * ratio)), target_h), Image.LANCZOS)
    alpha = logo.getchannel("A")
    white = Image.new("RGBA", logo.size, (255, 255, 255, 0))
    white.putalpha(alpha.point(lambda v: int(v * MARK_OPACITY)))
    shadow = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    shadow.putalpha(alpha.point(lambda v: int(v * MARK_OPACITY * 0.55)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, target_h // 70)))
    return white, shadow


def process(job):
    """Работи в отделен процес. Връща (ключ, ширина, височина, грешка)."""
    src, cat, name, force = job
    full_p = OUT_FULL / name
    thumb_p = OUT_THUMB / name
    try:
        if not force and full_p.exists() and thumb_p.exists():
            with Image.open(thumb_p) as t:
                return (cat, name, t.width, t.height, None)

        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
        im.thumbnail((FULL_MAX, FULL_MAX), Image.LANCZOS)

        # воден знак в центъра
        W, H = im.size
        target_h = max(24, round(min(H * MARK_SIZE, W * MARK_SIZE * 1.25 * 1.33)))
        white, shadow = make_mark(target_h)
        base = im.convert("RGBA")
        x = (W - white.width) // 2
        y = (H - white.height) // 2
        base.alpha_composite(shadow, dest=(max(0, x + 1), max(0, y + 1)))
        base.alpha_composite(white, dest=(max(0, x), max(0, y)))
        im = base.convert("RGB")

        im.save(full_p, "JPEG", quality=82, optimize=True, progressive=True)

        tw = min(THUMB_W, im.width)
        th = round(im.height * tw / im.width)
        thumb = im.resize((tw, th), Image.LANCZOS)
        thumb.save(thumb_p, "JPEG", quality=76, optimize=True, progressive=True)
        return (cat, name, tw, th, None)
    except Exception as e:  # noqa
        return (cat, name, 0, 0, f"{src}: {e}")


STATE_FILE = SITE / "images" / "autofill.json"
AUTOFILL_VER = 3   # вдигаме го, когато променим начина на избор: тогава програмата преподрежда сама


def _sha(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _rank(name):
    return hashlib.sha1(("seed1" + name).encode("utf-8")).hexdigest()


def autofill(items, refill):
    """Пълни сивите места (слайдшоу, услуги, избрани снимки) със снимки от портфолиото.
    НЕ пипа файлове, които си сменил ти на ръка."""
    try:
        state = json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        state = {}

    client = [i for i in items if i["c"] != "daily"]
    by_cat = {}
    for i in client:
        by_cat.setdefault(i["c"], []).append(i)
    for k in by_cat:
        by_cat[k].sort(key=lambda i: _rank(i["f"]))
    used = set()

    def take(pool, pred=None):
        for i in pool:
            if i["f"] in used:
                continue
            if pred is None or pred(i):
                used.add(i["f"])
                return i
        for i in pool:  # ако няма подходяща по форма, взимаме каквато има
            if i["f"] not in used:
                used.add(i["f"])
                return i
        return None

    plan = []  # (целеви файл, източник)
    order = [c for c in ("wedding", "engagement", "prom", "photoshoot", "events") if by_cat.get(c)]

    def pick_ordered(total, quota, pred=None):
        """Избира снимки по ред на поводите: първо сватби, после годежи и т.н."""
        chosen = {c: [] for c in order}
        for c in order:                                  # първо по квота
            for _ in range(quota.get(c, 0)):
                i = take(by_cat[c], pred)
                if i:
                    chosen[c].append(i)
        cnt = sum(len(v) for v in chosen.values())
        guard = 0
        while cnt < total and guard < 200:               # ако не стигат, допълваме по ред
            guard += 1
            for c in order:
                if cnt >= total:
                    break
                i = take(by_cat[c], pred)
                if i:
                    chosen[c].append(i)
                    cnt += 1
        out = []
        for c in order:
            out += chosen[c]
        return out[:total]

    # слайдшоу: хоризонтални, по ред на поводите (пропорции: сватби, годежи, балове, фотосесии, събития)
    weights = {"wedding": 6, "engagement": 3, "prom": 5, "photoshoot": 4, "events": 5}
    wsum = sum(weights[c] for c in order) or 1
    quota = {c: SLIDESHOW_COUNT * weights[c] // wsum for c in order}
    rest = SLIDESHOW_COUNT - sum(quota.values())
    for c in order * 3:
        if rest <= 0:
            break
        quota[c] += 1
        rest -= 1
    slide_items = pick_ordered(SLIDESHOW_COUNT, quota, lambda i: i["w"] / i["h"] >= 1.35) if SLIDESHOW_COUNT > 0 else []
    for n, i in enumerate(slide_items, start=1):
        plan.append((f"images/slides/slide-{n}.jpg", i["t"]))
    # услуги: портретни, от съответния повод
    for key in ("wedding", "engagement", "prom", "photoshoot", "events"):
        i = take(by_cat.get(key, []), lambda i: i["h"] / i["w"] >= 1.15)
        if i:
            plan.append((f"images/services/{key}.jpg", i["f"]))
    # избрани снимки (9): по ред на поводите
    for n, i in enumerate(pick_ordered(9, {"wedding": 2, "engagement": 2, "prom": 2, "photoshoot": 2, "events": 1}), start=1):
        plan.append((f"images/featured/f{n}.jpg", i["t"]))

    slides_changed = state.get("_slides_count") != SLIDESHOW_COUNT   # сменено е числото: преподреждаме всички слайдове
    done = kept = 0
    for dest, src in plan:
        d = SITE / dest
        rec = state.get(dest)
        ours = bool(rec) and d.exists() and _sha(d) == rec["sha"]
        if d.exists() and not ours:
            kept += 1          # сменен от теб: не го пипаме
            continue
        redo = refill or (slides_changed and dest.startswith("images/slides/"))
        if ours and not rec.get("placeholder") and not redo and rec.get("ver") == AUTOFILL_VER:
            continue           # вече е напълнен от програмата: оставяме го стабилен
        shutil.copyfile(SITE / src, d)
        state[dest] = {"sha": _sha(d), "placeholder": False, "ver": AUTOFILL_VER}
        done += 1
    # ако си намалил броя на слайдовете, махаме излишните (само тези, направени от програмата)
    for n in range(len(slide_items) + 1, 100) if SLIDESHOW_COUNT > 0 else []:
        dest = f"images/slides/slide-{n}.jpg"
        d = SITE / dest
        rec = state.get(dest)
        if d.exists() and rec and _sha(d) == rec["sha"]:
            d.unlink()
            del state[dest]
    state["_slides_count"] = SLIDESHOW_COUNT
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    return done, kept


def find_ws(arg):
    cands = []
    if arg:
        cands.append(Path(arg.strip().strip('"')))
    cands += [SITE.parent / "ws", Path.cwd() / "ws", SITE / "ws"]
    for c in cands:
        if c.is_dir():
            return c
    print("Не намирам папката ws. Плъзни я тук в прозореца (или копирай пътя ѝ) и натисни Enter:")
    while True:
        p = Path(input("> ").strip().strip('"'))
        if p.is_dir():
            return p
        print("Това не е папка. Опитай пак.")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--ws", help="път до папката ws")
    ap.add_argument("--force", action="store_true", help="прави всички снимки наново")
    ap.add_argument("--refill", action="store_true", help="избери наново снимките за слайдшоуто, услугите и избраните")
    args = ap.parse_args()

    if not LOGO.exists():
        print(f"Не намирам логото: {LOGO}")
        sys.exit(1)

    ws = find_ws(args.ws)
    print(f"Папка със снимки: {ws}")

    subdirs = {p.name.lower(): p for p in ws.iterdir() if p.is_dir()}
    OUT_FULL.mkdir(parents=True, exist_ok=True)
    OUT_THUMB.mkdir(parents=True, exist_ok=True)

    # снимки, скрити от портфолиото (js/portfolio-hide.js): не се правят наново
    hide = set()
    hf = SITE / "js" / "portfolio-hide.js"
    if hf.exists():
        hide = set(re.findall(r"['\"]([a-z]+-[0-9a-f]{10})['\"]", hf.read_text(encoding="utf-8")))

    jobs, skipped = [], []
    for folder, cat in CATS:
        d = subdirs.get(folder)
        if not d:
            print(f"  (!) Няма папка '{folder}', пропускам категорията.")
            continue
        files = sorted(
            [p for p in d.rglob("*") if p.is_file()],
            key=lambda p: natural_key(p.relative_to(d).as_posix()),
        )
        n = 0
        for f in files:
            if f.suffix.lower() in EXTS:
                rel = f.relative_to(ws).as_posix().lower()
                name = f"{cat}-{hashlib.sha1(rel.encode('utf-8')).hexdigest()[:10]}.jpg"
                if name[:-4] in hide:
                    continue
                jobs.append((str(f), cat, name, args.force))
                n += 1
            elif f.name.lower() not in ("thumbs.db", ".ds_store", "desktop.ini"):
                skipped.append(f)
        print(f"  {folder:12s} -> {cat:11s} {n} снимки")

    if not jobs:
        print("Няма намерени снимки.")
        sys.exit(1)

    print(f"\nОбработвам {len(jobs)} снимки. Първия път отнема няколко минути...")
    t0 = time.time()
    results = {}
    errors = []
    workers = max(1, (os.cpu_count() or 2) - 1)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(process, jobs, chunksize=4), 1):
            cat, name, w, h, err = r
            if err:
                errors.append(err)
            else:
                results[name] = (cat, w, h)
            if i % 25 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}", flush=True)

    # данни за сайта: в реда на категориите
    items = []
    for _, cat, name, _f in jobs:
        if name in results:
            c, w, h = results[name]
            items.append({"c": c, "t": f"images/portfolio/thumbs/{name}",
                          "f": f"images/portfolio/full/{name}", "w": w, "h": h})

    with open(DATA_JS, "w", encoding="utf-8") as fh:
        fh.write("/* Генерирано автоматично от tools/build_portfolio.py. Не го редактирай на ръка. */\n")
        fh.write("window.PORTFOLIO = [\n")
        fh.write(",\n".join(json.dumps(i, ensure_ascii=False, separators=(",", ":")) for i in items))
        fh.write("\n];\n")

    filled, kept = autofill(items, args.refill)

    # махаме примерните сиви снимки
    ph = re.compile(r"^(wedding|engagement|prom|photoshoot|events|daily)-\d\.jpg$")
    for f in (SITE / "images" / "portfolio").glob("*.jpg"):
        if ph.match(f.name):
            f.unlink()

    # махаме снимки, които вече не са в ws (напр. изтрити от теб)
    keep = {i["f"].rsplit("/", 1)[1] for i in items}
    removed = 0
    for folder in (OUT_FULL, OUT_THUMB):
        for f in folder.glob("*.jpg"):
            if f.name not in keep:
                f.unlink()
                removed += 1

    total = sum(f.stat().st_size for d in (OUT_FULL, OUT_THUMB) for f in d.glob("*.jpg"))
    print("\n================ ГОТОВО ================")
    by = {}
    for i in items:
        by[i["c"]] = by.get(i["c"], 0) + 1
    for _, cat in CATS:
        if cat in by:
            print(f"  {cat:11s} {by[cat]}")
    print(f"Общо снимки в портфолиото: {len(items)}")
    print(f"Размер на файловете за сайта: {total / 1024 / 1024:.0f} MB")
    print(f"Време: {time.time() - t0:.0f} сек.")
    print(f"Слайдшоу, услуги и избрани снимки: напълнени {filled}" + (f", оставени твои {kept}" if kept else ""))
    if removed:
        print(f"Премахнати стари файлове: {removed}")
    if skipped:
        print(f"\nПропуснати файлове (неподдържан формат): {len(skipped)}")
        for f in skipped[:8]:
            print("   ", f)
    if errors:
        print(f"\nГрешки при {len(errors)} снимки:")
        for e in errors[:8]:
            print("   ", e)


if __name__ == "__main__":
    main()
