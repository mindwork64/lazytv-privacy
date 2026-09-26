#!/usr/bin/env python3
"""Генератор графики для карточки LazyTv Droid в RuStore.

Создаёт:
  icon-512.png       — иконка 512x512 (RGBA, прозрачные углы), для карточки RuStore
  cover-660x440.png  — обложка 660x440 (RGB)
  preview-sheet.png  — контрольный лист для визуальной проверки

Монограмма LT рисуется строго по координатам вектора
app/src/main/res/mipmap/ic_launcher.xml (viewport 108x108, штрих 8,
round cap и round join), поэтому картинки совпадают с иконкой на устройстве.

Запуск:  python3 make_assets.py
Требуется Pillow (python3-pil). Шрифт: DejaVu Sans Bold (есть в системе).
"""

import pathlib

from PIL import Image, ImageDraw, ImageFont

OUT = pathlib.Path(__file__).resolve().parent
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BRAND_TOP = (165, 0, 52)      # #A50034 — фон вектора иконки
BRAND_BOTTOM = (78, 6, 40)    # затемнение к низу обложки
WHITE = (255, 255, 255, 255)

# Координаты монограммы из вектора (viewport 108x108).
# L: M34,36 L34,72 L54,72   T: M60,36 L82,36 и M71,36 L71,72
L_PTS = [((34, 36), (34, 72)), ((34, 72), (54, 72))]
T_PTS = [((60, 36), (82, 36)), ((71, 36), (71, 72))]
JOINTS = [(34, 36), (34, 72), (54, 72), (60, 36), (82, 36), (71, 36), (71, 72)]

STROKE_RATIO = 8.0 / 108.0    # толщина штриха 8 в viewport 108
SS = 4                        # суперсемплинг для гладких round cap


def draw_monogram(layer: ImageDraw.ImageDraw, box_x: float, box_y: float, box_size: float, scale: int) -> None:
    """Рисует монограмму LT в квадрате заданного размера, вписывая в него viewport 108x108."""
    k = (box_size * scale) / 108.0
    w = max(1, int(round(STROKE_RATIO * box_size * scale)))
    ox, oy = box_x * scale, box_y * scale

    def P(pt):
        return (ox + pt[0] * k, oy + pt[1] * k)

    for a, b in L_PTS + T_PTS:
        layer.line([P(a), P(b)], fill=WHITE, width=w)
    r = w / 2.0
    for pt in JOINTS:
        cx, cy = P(pt)
        layer.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)


def make_icon(size: int) -> Image.Image:
    """Иконка: скруглённый квадрат фирменного цвета и белая монограмма по центру.

    margin 0.17 соответствует safe zone adaptive icon: foreground-вектор 108x108
    целиком попадает в центральные ~66% площади, как на устройстве.
    """
    S = size * SS
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=BRAND_TOP + (255,))

    margin = 0.17
    inner = (1 - 2 * margin)
    draw_monogram(d, size * margin, size * margin, inner * size, SS)
    return icon.resize((size, size), Image.LANCZOS)


def fit_font(draw, text: str, max_width: float, start_size: int):
    """Подбирает наибольший кегль, при котором текст влезает в max_width.

    Без этого заголовок при суперсемплинге 3x вылезает за правый край обложки.
    """
    size = start_size
    while size > 8:
        font = ImageFont.truetype(FONT_BOLD, size)
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        if right - left <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(FONT_BOLD, 8)


def make_cover(width: int, height: int) -> Image.Image:
    """Обложка: градиентный фон, диск с монограммой слева, текст и чипы справа."""
    S = 3
    W, H = width * S, height * S

    # Фон — вертикальный градиент от фирменного цвета к затемнённому.
    cover = Image.new("RGBA", (W, H), BRAND_TOP + (255,))
    gd = ImageDraw.Draw(cover)
    for y in range(H):
        t = y / (H - 1)
        gd.line([(0, y), (W, y)],
                fill=tuple(int(BRAND_TOP[i] * (1 - t) + BRAND_BOTTOM[i] * t) for i in range(3)) + (255,))

    # Светлый диск под монограммой. Рисуем ОТДЕЛЬНЫМ слоем и композитим:
    # полупрозрачная заливка в основном слое перезаписала бы фон, а не смешалась с ним.
    disc_d = int(320 * S)
    disc_x, disc_y = int(46 * S), int((height / 2 - 160) * S)

    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([disc_x, disc_y, disc_x + disc_d, disc_y + disc_d], fill=(255, 255, 255, 34))
    hd.ellipse([disc_x + 12 * S, disc_y + 12 * S, disc_x + disc_d - 12 * S, disc_y + disc_d - 12 * S],
               outline=(255, 255, 255, 90), width=3 * S)
    cover.alpha_composite(halo)

    # Монограмма внутри диска, вписанная в центральные 66% как в safe zone.
    mono = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(mono)
    inner = disc_d * 0.66
    draw_monogram(md,
                  (disc_x + (disc_d - inner) / 2.0) / S,
                  (disc_y + (disc_d - inner) / 2.0) / S,
                  inner / S, S)
    cover.alpha_composite(mono)

    # Текстовая зона справа от диска.
    text_x = int(400 * S)
    max_text_w = W - text_x - int(36 * S)

    d = ImageDraw.Draw(cover)
    title = "LazyTv Droid"
    subtitle = "Пульт для LG NetCast 4.0"
    tags = ["Локальная сеть", "Без аккаунтов", "Без рекламы"]

    f_name = fit_font(d, title, max_text_w, int(54 * S))
    f_sub = fit_font(d, subtitle, max_text_w, int(26 * S))
    f_tag = ImageFont.truetype(FONT_BOLD, int(21 * S))

    name_box = d.textbbox((0, 0), title, font=f_name)
    sub_box = d.textbbox((0, 0), subtitle, font=f_sub)
    name_h = name_box[3] - name_box[1]
    sub_h = sub_box[3] - sub_box[1]
    gap = int(18 * S)

    chip_h = int(34 * S)
    chip_pad_x = int(18 * S)
    chip_gap = int(12 * S)
    chip_row_gap = int(12 * S)

    # Раскладываем чипы по строкам заранее, чтобы знать высоту блока и центрировать текст.
    rows = [[]]
    row_w = 0
    for tag in tags:
        b = d.textbbox((0, 0), tag, font=f_tag)
        cw = (b[2] - b[0]) + chip_pad_x * 2
        extra = chip_gap if rows[-1] else 0
        if rows[-1] and row_w + extra + cw > max_text_w:
            rows.append([])
            row_w = 0
            extra = 0
        rows[-1].append(tag)
        row_w += extra + cw
    chips_h = len(rows) * chip_h + (len(rows) - 1) * chip_row_gap

    block_h = name_h + gap + sub_h + int(28 * S) + chips_h
    y = (H - block_h) // 2

    d.text((text_x, y), title, font=f_name, fill=WHITE)
    y += name_h + gap
    d.text((text_x, y), subtitle, font=f_sub, fill=(255, 255, 255, 215))
    y += sub_h + int(28 * S)

    # Чипы: полупрозрачная заливка — отдельным слоем, текст — в основном слое.
    chips = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chips)
    chip_y = y
    for row in rows:
        cx = text_x
        for tag in row:
            b = d.textbbox((0, 0), tag, font=f_tag)
            cw = (b[2] - b[0]) + chip_pad_x * 2
            cd.rounded_rectangle([cx, chip_y, cx + cw, chip_y + chip_h],
                                 radius=chip_h // 2,
                                 fill=(255, 255, 255, 46),
                                 outline=(255, 255, 255, 120),
                                 width=2 * S)
            d.text((cx + chip_pad_x, chip_y + (chip_h - (b[3] - b[1])) // 2 - b[1]),
                   tag, font=f_tag, fill=WHITE)
            cx += cw + chip_gap
        chip_y += chip_h + chip_row_gap
    cover.alpha_composite(chips)

    return cover.convert("RGB").resize((width, height), Image.LANCZOS)


def make_preview(icon: Image.Image, cover: Image.Image) -> Image.Image:
    """Контрольный лист: иконка на шахматке (видно прозрачность углов) и обложка."""
    h = cover.height
    pad = 24
    scaled = icon.resize((h, h), Image.LANCZOS)

    checker = Image.new("RGBA", (h, h), (255, 255, 255, 255))
    tile = 16
    for ty in range(0, h, tile):
        for tx in range(0, h, tile):
            if (tx // tile + ty // tile) % 2 == 0:
                for yy in range(ty, min(ty + tile, h)):
                    for xx in range(tx, min(tx + tile, h)):
                        checker.putpixel((xx, yy), (205, 205, 210, 255))
    checker.alpha_composite(scaled)

    sheet = Image.new("RGB", (pad * 3 + h + cover.width, h + pad * 2), (14, 14, 16))
    sheet.paste(checker.convert("RGB"), (pad, pad))
    sheet.paste(cover, (pad * 2 + h, pad))
    return sheet


def main() -> None:
    icon = make_icon(512)
    icon.save(OUT / "icon-512.png")

    cover = make_cover(660, 440)
    cover.save(OUT / "cover-660x440.png")

    make_preview(icon, cover).save(OUT / "preview-sheet.png")

    print("icon-512.png:", icon.size, icon.mode)
    print("cover-660x440.png:", cover.size, cover.mode)


if __name__ == "__main__":
    main()
