#!/usr/bin/env python3
"""Build children's Russia quiz PowerPoint presentation."""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import nsmap
from pptx.oxml import parse_xml
from pptx.util import Inches, Pt, Emu

OUT = Path(__file__).resolve().parent
IMG = OUT / "images"
IMG.mkdir(parents=True, exist_ok=True)

# Colors: festive Russia-themed (not purple/cream AI defaults)
NAVY = RGBColor(0x0B, 0x2C, 0x5C)
CRIMSON = RGBColor(0xC4, 0x1E, 0x3A)
GOLD = RGBColor(0xD4, 0xA0, 0x17)
CREAM = RGBColor(0xFF, 0xFB, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT_BLUE = RGBColor(0xE8, 0xF1, 0xFA)
DARK = RGBColor(0x1A, 0x1A, 0x2E)
GREEN = RGBColor(0x1B, 0x6B, 0x4A)

# Unsplash source images (thematic, avoid spoiling exact answers)
# Using images.unsplash.com direct links with known photo IDs
IMAGE_URLS = {
    # Block 1
    "b1_q2": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=80",  # honey / bees theme
    "b1_q4": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=1200&q=80",  # embroidery / textile
    "b1_q5": "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=1200&q=80",  # milk pour
    "b1_q6": "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?w=1200&q=80",  # campfire night
    "b1_q7": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=1200&q=80",  # festive celebration
    "b1_q9": "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=1200&q=80",  # music instruments abstract
    # Block 2
    "b2_q1": "https://images.unsplash.com/photo-1548013146-72479768bada?w=1200&q=80",  # historic temple / baptism vibe
    "b2_q2": "https://images.unsplash.com/photo-1556610961-2fecc5927173?w=1200&q=80",  # St Petersburg / city
    "b2_q4": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200&q=80",  # Kremlin / power
    "b2_q6": "https://images.unsplash.com/photo-1589656966895-2f33e7653819?w=1200&q=80",  # battle / history cannon
    "b2_q8": "https://images.unsplash.com/photo-1551958219-acbc608c6377?w=1200&q=80",  # sports / stadium
    "b2_q9": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=1200&q=80",  # Moscow Kremlin historic
    # Block 3
    "b3_q3": "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=1200&q=80",  # military memorial
    "b3_q4": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=1200&q=80",  # flags waving (generic)
    "b3_q6": "https://images.unsplash.com/photo-1506157786151-b8491531f063?w=1200&q=80",  # choir / singing
    "b3_q7": "https://images.unsplash.com/photo-1555990793-da11153b2473?w=1200&q=80",  # Russian tricolor soft
    "b3_q8": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=1200&q=80",  # Russia celebration / Kremlin
    "b3_q9": "https://images.unsplash.com/photo-1569003339405-ea396a5a8a90?w=1200&q=80",  # medieval banner / castle
    # Block 4
    "b4_q1": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=1200&q=80",  # historic war theme - replace
    "b4_q2": "https://images.unsplash.com/photo-1507838153414-b4b713384a76?w=1200&q=80",  # ballet / orchestra
    "b4_q4": "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=1200&q=80",  # painting / art museum
    "b4_q5": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=1200&q=80",  # Moscow
    "b4_q6": "https://images.unsplash.com/photo-1596484552834-6a58f850e0a1?w=1200&q=80",  # baptism / church water
    "b4_q9": "https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=1200&q=80",  # space / earth from orbit
    # Block 5
    "b5_q1": "https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=1200&q=80",  # big river landscape
    "b5_q2": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1200&q=80",  # mountain range
    "b5_q3": "https://images.unsplash.com/photo-1524661135-423995f22d0b?w=1200&q=80",  # map of world/regions
    "b5_q5": "https://images.unsplash.com/photo-1501139083538-0139583c060f?w=1200&q=80",  # clocks / time
    "b5_q6": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1200&q=80",  # high mountain peak
    "b5_q8": "https://images.unsplash.com/photo-1505142468610-359e7d316be0?w=1200&q=80",  # sea coast waves
    # Block covers
    "block1": "https://images.unsplash.com/photo-1605649487212-47bdab064df7?w=1400&q=80",
    "block2": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=1400&q=80",
    "block3": "https://images.unsplash.com/photo-1555990793-da11153b2473?w=1400&q=80",
    "block4": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1400&q=80",
    "block5": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=80",
    "title": "https://images.unsplash.com/photo-1547448415-e9f5b28e570d?w=1400&q=80",
}

BLOCKS = [
    {
        "num": 1,
        "title": "Традиции и обычаи\nнародов России",
        "short": "Традиции и обычаи народов России",
        "color": CRIMSON,
        "img": "block1",
        "questions": [
            {
                "n": 2,
                "q": "Назовите традиционное блюдо татар — восточную сладость из теста и мёда.",
                "a": "Чак-чак",
                "img": "b1_q2",
                "hint_img_note": "мёд / сладости",
            },
            {
                "n": 4,
                "q": "Как называется полотенце из домотканого холста, которое считалось оберегом? Его использовали в свадебных обрядах, при крещении и других событиях.",
                "a": "Рушник",
                "img": "b1_q4",
            },
            {
                "n": 5,
                "q": "Какой напиток готовят чеченцы и ингуши из молока и соли?",
                "a": "Айран",
                "img": "b1_q5",
            },
            {
                "n": 6,
                "q": "В каком празднике существует традиция прыжка через костёр и плетения венков?",
                "a": "Иван Купала\n(Купальская ночь)",
                "img": "b1_q6",
            },
            {
                "n": 7,
                "q": "Как назывался старинный женский головной убор замужней женщины, напоминающий высокую корону вокруг головы?",
                "a": "Кокошник",
                "img": "b1_q7",
            },
            {
                "n": 9,
                "q": "Как называется русский народный трёхструнный инструмент?",
                "a": "Балалайка",
                "img": "b1_q9",
            },
        ],
    },
    {
        "num": 2,
        "title": "История и\nисторическая память России",
        "short": "История и историческая память России",
        "color": NAVY,
        "img": "block2",
        "questions": [
            {
                "n": 1,
                "q": "В каком году произошло крещение Руси?",
                "a": "988 год",
                "img": "b2_q1",
            },
            {
                "n": 2,
                "q": "В каком городе произошло восстание декабристов?",
                "a": "Санкт-Петербург\n(Сенатская площадь)",
                "img": "b2_q2",
            },
            {
                "n": 4,
                "q": "Кто был первым президентом Российской Федерации?",
                "a": "Борис Николаевич Ельцин",
                "img": "b2_q4",
            },
            {
                "n": 6,
                "q": "Какое знаменитое сражение произошло в 1812 году?",
                "a": "Бородинская битва",
                "img": "b2_q6",
            },
            {
                "n": 8,
                "q": "В каком году проходила Олимпиада в Москве?",
                "a": "1980 год",
                "img": "b2_q8",
            },
            {
                "n": 9,
                "q": "Кто был первым в России царём?",
                "a": "Иван Грозный\n(Иван IV)",
                "img": "b2_q9",
            },
        ],
    },
    {
        "num": 3,
        "title": "Символы России",
        "short": "Символы России",
        "color": GOLD,
        "img": "block3",
        "questions": [
            {
                "n": 3,
                "q": "Какой символ воинской славы изображён на многих памятниках и наградах, включая Орден Победы?",
                "a": "Георгиевская лента",
                "img": "b3_q3",
            },
            {
                "n": 4,
                "q": "Кто ввёл порядок расположения цветов на Российском флаге?",
                "a": "Пётр I",
                "img": "b3_q4",
            },
            {
                "n": 6,
                "q": "Как начинается второй куплет гимна России?",
                "a": "«От южных морей до полярного края\nраскинулись наши леса и поля…»",
                "img": "b3_q6",
            },
            {
                "n": 7,
                "q": "Когда мы отмечаем День Государственного флага?",
                "a": "22 августа",
                "img": "b3_q7",
            },
            {
                "n": 8,
                "q": "Когда отмечается День России?",
                "a": "12 июня",
                "img": "b3_q8",
            },
            {
                "n": 9,
                "q": "Какое старинное русское название флага?",
                "a": "Стяг",
                "img": "b3_q9",
            },
        ],
    },
    {
        "num": 4,
        "title": "Выдающиеся\nличности России",
        "short": "Выдающиеся личности России",
        "color": GREEN,
        "img": "block4",
        "questions": [
            {
                "n": 1,
                "q": "Кто из русских полководцев прославился победами в Отечественной войне 1812 года и известен фразой: «С потерей Москвы не потеряна Россия»?",
                "a": "Михаил Илларионович Кутузов",
                "img": "b4_q1",
            },
            {
                "n": 2,
                "q": "Какой русский композитор написал «Лебединое озеро» и «Щелкунчик»?",
                "a": "Пётр Ильич Чайковский",
                "img": "b4_q2",
            },
            {
                "n": 4,
                "q": "Какой русский художник написал картину «Богатыри», воплотившую образы народных защитников?",
                "a": "Виктор Михайлович Васнецов",
                "img": "b4_q4",
            },
            {
                "n": 5,
                "q": "Назовите человека, который основал Москву.",
                "a": "Юрий Долгорукий",
                "img": "b4_q5",
            },
            {
                "n": 6,
                "q": "Какой князь крестил Русь в 988 году?",
                "a": "Князь Владимир\n(Владимир Святославич)",
                "img": "b4_q6",
            },
            {
                "n": 9,
                "q": "Кто стала первой женщиной-космонавтом?",
                "a": "Валентина Терешкова",
                "img": "b4_q9",
            },
        ],
    },
    {
        "num": 5,
        "title": "География\nрегионов России",
        "short": "География регионов России",
        "color": RGBColor(0x0E, 0x6B, 0x8A),
        "img": "block5",
        "questions": [
            {
                "n": 1,
                "q": "Какая река является самой длинной в России?",
                "a": "Лена\n(более 4,4 тыс. км)",
                "img": "b5_q1",
            },
            {
                "n": 2,
                "q": "Какая горная система является границей между Европейской и Азиатской частями России?",
                "a": "Уральские горы",
                "img": "b5_q2",
            },
            {
                "n": 3,
                "q": "Сколько в России автономных округов?",
                "a": "4",
                "img": "b5_q3",
            },
            {
                "n": 5,
                "q": "Сколько часовых поясов в России?",
                "a": "11",
                "img": "b5_q5",
            },
            {
                "n": 6,
                "q": "Самая высокая точка России?",
                "a": "Эльбрус",
                "img": "b5_q6",
            },
            {
                "n": 8,
                "q": "Россия имеет самое большое количество морей, омывающих её берега. Сколько?",
                "a": "13",
                "img": "b5_q8",
            },
        ],
    },
]


def download(key: str, url: str) -> Path | None:
    dest = IMG / f"{key}.jpg"
    if dest.exists() and dest.stat().st_size > 5000:
        return dest
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; QuizBuilder/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"OK  {key} ({len(data)} bytes)")
        return dest
    except Exception as e:
        print(f"FAIL {key}: {e}")
        return None


def set_run_font(run, size_pt, bold=False, color=DARK, name="Arial"):
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = name


def add_full_bg(slide, color: RGBColor):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    # send to back
    spTree = slide.shapes._spTree
    sp = shape._element
    spTree.remove(sp)
    spTree.insert(2, sp)
    return shape


def add_accent_bar(slide, color: RGBColor, top=0):
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(top), Inches(13.333), Inches(0.18)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    return bar


def add_textbox(slide, left, top, width, height, text, size=28, bold=False, color=DARK, align=PP_ALIGN.LEFT, font="Arial"):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_run_font(run, size, bold=bold, color=color, name=font)
    return box


def add_rounded_panel(slide, left, top, width, height, fill: RGBColor):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    # softer corners
    try:
        shape.adjustments[0] = 0.08
    except Exception:
        pass
    return shape


def picture_cover(slide, path: Path, left, top, width, height):
    """Add picture cropped roughly to area (pptx doesn't crop easily; we size it)."""
    if path and path.exists():
        return slide.shapes.add_picture(str(path), left, top, width=width, height=height)
    # fallback colored rect
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    s.fill.solid()
    s.fill.fore_color.rgb = SOFT_BLUE
    s.line.fill.background()
    return s


def make_title(prs, images):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_full_bg(slide, NAVY)
    img = images.get("title")
    if img:
        try:
            pic = slide.shapes.add_picture(str(img), Inches(0), Inches(0), height=Inches(7.5))
            # dim overlay
        except Exception:
            pass
    overlay = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    overlay.fill.solid()
    overlay.fill.fore_color.rgb = NAVY
    # semi-opaque via solid dark is ok for readability
    overlay.fill.fore_color.rgb = RGBColor(0x08, 0x1E, 0x3D)
    # Make overlay somewhat transparent using alpha in solid fill
    try:
        solidFill = overlay.fill._xPr.solidFill
        srgb = solidFill.find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr"
        )
        if srgb is not None:
            alpha = parse_xml(
                '<a:alpha xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="72000"/>'
            )
            srgb.append(alpha)
    except Exception:
        pass

    add_accent_bar(slide, GOLD, 0)
    add_accent_bar(slide, CRIMSON, 7.32)

    add_textbox(
        slide,
        Inches(0.8),
        Inches(2.0),
        Inches(11.5),
        Inches(1.2),
        "ВИКТОРИНА",
        size=54,
        bold=True,
        color=GOLD,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(0.8),
        Inches(3.2),
        Inches(11.5),
        Inches(1.4),
        "Россия: традиции, история,\nсимволы, личности и география",
        size=28,
        bold=False,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(0.8),
        Inches(5.3),
        Inches(11.5),
        Inches(0.6),
        "5 блоков  ·  30 вопросов  ·  Нажмите, чтобы начать",
        size=18,
        color=RGBColor(0xCC, 0xDD, 0xEE),
        align=PP_ALIGN.CENTER,
    )


def make_block_slide(prs, block, images):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_full_bg(slide, block["color"] if block["num"] != 3 else NAVY)
    img = images.get(block["img"])
    if img:
        try:
            slide.shapes.add_picture(str(img), Inches(0), Inches(0), height=Inches(7.5))
        except Exception:
            pass
    overlay = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    overlay.fill.solid()
    base = block["color"] if block["num"] != 3 else NAVY
    overlay.fill.fore_color.rgb = base
    try:
        solidFill = overlay.fill._xPr.solidFill
        srgb = solidFill.find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr"
        )
        if srgb is not None:
            alpha = parse_xml(
                '<a:alpha xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="65000"/>'
            )
            srgb.append(alpha)
    except Exception:
        pass

    add_accent_bar(slide, GOLD, 0)
    add_textbox(
        slide,
        Inches(1),
        Inches(2.0),
        Inches(11.3),
        Inches(0.7),
        f"БЛОК {block['num']}",
        size=22,
        bold=True,
        color=GOLD,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(1),
        Inches(2.7),
        Inches(11.3),
        Inches(2.2),
        block["title"],
        size=40,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(1),
        Inches(5.4),
        Inches(11.3),
        Inches(0.5),
        "6 вопросов  ·  Готовы? Вперёд!",
        size=18,
        color=RGBColor(0xEE, 0xEE, 0xEE),
        align=PP_ALIGN.CENTER,
    )


def make_question_slide(prs, block, qi, q, images):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_full_bg(slide, CREAM)
    add_accent_bar(slide, block["color"], 0)

    # Header strip
    header = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0.18), Inches(13.333), Inches(0.85)
    )
    header.fill.solid()
    header.fill.fore_color.rgb = WHITE
    header.line.fill.background()

    add_textbox(
        slide,
        Inches(0.5),
        Inches(0.28),
        Inches(8),
        Inches(0.55),
        f"Блок {block['num']}: {block['short']}",
        size=16,
        bold=True,
        color=block["color"] if block["num"] != 3 else NAVY,
    )
    add_textbox(
        slide,
        Inches(9.2),
        Inches(0.28),
        Inches(3.6),
        Inches(0.55),
        f"Вопрос {qi} из 6",
        size=16,
        bold=True,
        color=DARK,
        align=PP_ALIGN.RIGHT,
    )

    # Image panel (right)
    img_path = images.get(q["img"])
    add_rounded_panel(slide, Inches(7.3), Inches(1.3), Inches(5.5), Inches(5.5), SOFT_BLUE)
    if img_path and img_path.exists():
        try:
            # Fill panel area
            slide.shapes.add_picture(
                str(img_path), Inches(7.45), Inches(1.45), width=Inches(5.2), height=Inches(5.2)
            )
        except Exception:
            pass

    # Question card (left)
    add_rounded_panel(slide, Inches(0.4), Inches(1.3), Inches(6.6), Inches(5.5), WHITE)
    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.4), Inches(1.3), Inches(0.18), Inches(5.5)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = block["color"] if block["num"] != 3 else CRIMSON
    accent.line.fill.background()

    add_textbox(
        slide,
        Inches(0.9),
        Inches(1.6),
        Inches(5.8),
        Inches(0.5),
        "ВОПРОС",
        size=14,
        bold=True,
        color=GOLD,
    )
    add_textbox(
        slide,
        Inches(0.9),
        Inches(2.2),
        Inches(5.8),
        Inches(3.8),
        q["q"],
        size=24,
        bold=True,
        color=DARK,
    )
    add_textbox(
        slide,
        Inches(0.9),
        Inches(6.2),
        Inches(5.8),
        Inches(0.4),
        "Команда отвечает → клик для ответа",
        size=12,
        color=RGBColor(0x88, 0x88, 0x99),
    )


def make_answer_slide(prs, block, qi, q):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_full_bg(slide, RGBColor(0x0F, 0x3D, 0x2E))
    add_accent_bar(slide, GOLD, 0)
    add_accent_bar(slide, GOLD, 7.32)

    add_textbox(
        slide,
        Inches(0.8),
        Inches(1.5),
        Inches(11.7),
        Inches(0.6),
        f"Блок {block['num']}  ·  Ответ {qi} из 6",
        size=18,
        bold=True,
        color=GOLD,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(0.8),
        Inches(2.3),
        Inches(11.7),
        Inches(0.5),
        "ПРАВИЛЬНЫЙ ОТВЕТ",
        size=16,
        bold=True,
        color=RGBColor(0xA8, 0xE6, 0xC4),
        align=PP_ALIGN.CENTER,
    )

    add_rounded_panel(slide, Inches(1.5), Inches(3.0), Inches(10.3), Inches(2.6), RGBColor(0x14, 0x52, 0x3E))
    add_textbox(
        slide,
        Inches(1.8),
        Inches(3.3),
        Inches(9.7),
        Inches(2.1),
        q["a"],
        size=36,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(0.8),
        Inches(6.0),
        Inches(11.7),
        Inches(0.4),
        "Клик — следующий вопрос",
        size=14,
        color=RGBColor(0xA8, 0xE6, 0xC4),
        align=PP_ALIGN.CENTER,
    )


def make_final(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_full_bg(slide, NAVY)
    add_accent_bar(slide, GOLD, 0)
    add_accent_bar(slide, CRIMSON, 7.32)
    add_textbox(
        slide,
        Inches(0.8),
        Inches(2.4),
        Inches(11.7),
        Inches(1.0),
        "Молодцы!",
        size=54,
        bold=True,
        color=GOLD,
        align=PP_ALIGN.CENTER,
    )
    add_textbox(
        slide,
        Inches(0.8),
        Inches(3.6),
        Inches(11.7),
        Inches(1.2),
        "Все 5 блоков пройдены.\nСпасибо за игру!",
        size=26,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )


def main():
    print("Downloading images...")
    images: dict[str, Path | None] = {}
    for key, url in IMAGE_URLS.items():
        images[key] = download(key, url)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    make_title(prs, images)
    for block in BLOCKS:
        make_block_slide(prs, block, images)
        for i, q in enumerate(block["questions"], start=1):
            make_question_slide(prs, block, i, q, images)
            make_answer_slide(prs, block, i, q)
    make_final(prs)

    out = OUT / "Викторина_Россия.pptx"
    prs.save(str(out))
    print(f"Saved: {out}")
    print(f"Slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
