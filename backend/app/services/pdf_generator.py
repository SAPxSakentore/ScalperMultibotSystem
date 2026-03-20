"""
PDF-генератор ИТД на базе ReportLab.
Поддерживает: АОСР, ОЖР, Акт гидравлических испытаний.
"""
import io
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Шрифты ──────────────────────────────────────────────────────────────────
_FONTS_REGISTERED = False

def _ensure_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("Serif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"))
    pdfmetrics.registerFont(TTFont("SerifBold", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"))
    _FONTS_REGISTERED = True


# ── Стили ────────────────────────────────────────────────────────────────────
def _styles():
    _ensure_fonts()
    def S(name, **kw):
        base = dict(fontName="Serif", fontSize=9, leading=13, spaceAfter=0, spaceBefore=0)
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "center":    S("ctr",  alignment=TA_CENTER),
        "bold":      S("bold", fontName="SerifBold"),
        "bold_ctr":  S("bctr", fontName="SerifBold", alignment=TA_CENTER),
        "left":      S("lft",  alignment=TA_LEFT),
        "justify":   S("jst",  alignment=TA_JUSTIFY, leading=15),
        "small":     S("sm",   fontSize=8, leading=11),
        "small_ctr": S("smc",  fontSize=8, leading=11, alignment=TA_CENTER),
        "sign":      S("sgn",  fontSize=9, leading=13),
    }


def _p(text: str, st, before=0, after=4):
    st2 = ParagraphStyle(st.name + "_x", parent=st, spaceBefore=before, spaceAfter=after)
    return Paragraph(text, st2)


def _sp(h=6):
    return Spacer(1, h)


def _tbl(data, col_widths, style_cmds=None):
    t = Table(data, colWidths=col_widths)
    base = [
        ("FONTNAME",      (0, 0), (-1, -1), "Serif"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]
    if style_cmds:
        base.extend(style_cmds)
    t.setStyle(TableStyle(base))
    return t


def _month_ru(m: int) -> str:
    return ["января","февраля","марта","апреля","мая","июня",
            "июля","августа","сентября","октября","ноября","декабря"][m - 1]


def _month_kz(m: int) -> str:
    return ["қаңтар","ақпан","наурыз","сәуір","мамыр","маусым",
            "шілде","тамыз","қыркүйек","қазан","қараша","желтоқсан"][m - 1]


# ════════════════════════════════════════════════════════════════════════════
#  АОСР
# ════════════════════════════════════════════════════════════════════════════

def generate_aosr_pdf(project: Dict, work: Dict) -> bytes:
    """Вернуть байты PDF для АОСР."""
    _ensure_fonts()
    st = _styles()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=1.5 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    now = datetime.now()
    story = []

    # ── Шапка УТВЕРЖДАЮ / БЕКІТЕМІН ─────────────────────────────────────
    tech_sup = project.get("technical_supervisor") or "____________________"
    hdr = _tbl(
        [
            [_p("УТВЕРЖДАЮ<br/>Технический надзор заказчика", st["small"]),
             _p("БЕКІТЕМІН<br/>Тапсырыс берушінің техникалық бақылаушысы", st["small"])],
            [_p(project.get("customer_name") or "____________________", st["small"]),
             _p(project.get("customer_name") or "____________________", st["small"])],
            [_p(f"____________ {tech_sup}", st["small"]),
             _p(f"____________ {tech_sup}", st["small"])],
            [_p(f"«____» {_month_ru(now.month)} {now.year} г.", st["small"]),
             _p(f"«____» {_month_kz(now.month)} {now.year} ж.", st["small"])],
        ],
        [8 * cm, 8.5 * cm],
    )
    story += [hdr, _sp(10)]

    # ── Заголовок ────────────────────────────────────────────────────────
    act_no = work.get("act_number") or "___"
    story += [
        _p(f"<b>АКТ № {act_no}</b>", st["bold_ctr"], after=2),
        _p("<b>ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ</b>", st["bold_ctr"], after=2),
        _p("<b>ЖАСЫРЫН ЖҰМЫСТАРДЫ КУӘЛАНДЫРУ АКТІСІ</b>", st["bold_ctr"], after=4),
        _p(f"«{now.day}» {_month_ru(now.month)} {now.year} г. / "
           f"{now.year} жылғы «{now.day}» {_month_kz(now.month)}", st["center"], after=10),
        _p("Мы, нижеподписавшиеся / Біз, төменде қол қойушылар:", st["justify"], after=6),
    ]

    # ── Таблица представителей ────────────────────────────────────────────
    foreman     = work.get("foreman") or "____________________"
    author_sup  = work.get("author_supervisor") or "____________________"
    designer    = project.get("designer_name") or "____________________"
    contractor  = project.get("contractor_name") or "____________________"

    reps = [
        ("Представитель заказчика —\nтехнический надзор:\nТапсырыс берушінің өкілі —\nтехникалық бақылаушы:",
         project.get("customer_name") or "____________________",
         tech_sup),
        ("Представитель подрядчика —\nпроизводитель работ:\nМердігердің өкілі —\nжұмыс жетекшісі:",
         contractor, foreman),
        ("Представитель проектировщика —\nавторский надзор:\nЖобалаушының өкілі —\nавторлық бақылаушы:",
         designer, author_sup),
    ]
    rep_tbl = _tbl(
        [[_p(r[0], st["small"]), _p(r[1], st["small"]), _p(r[2], st["small"])] for r in reps],
        [5.5 * cm, 6 * cm, 5 * cm],
        [
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (0, -1),  colors.HexColor("#F2F2F2")),
        ],
    )
    story += [rep_tbl, _sp(8)]

    # ── Секция helper ─────────────────────────────────────────────────────
    def section(num, ru, kz, rows):
        story.append(_p(f"<b>{num}. {ru} / {kz}</b>", st["bold"], before=6, after=4))
        t = _tbl(
            [[_p(r[0], st["small"]), _p(r[1], st["small"])] for r in rows],
            [5 * cm, 11.5 * cm],
            [("LINEBELOW", (1, 0), (1, -1), 0.5, colors.black)],
        )
        story.append(t)

    # ── 1. Предъявлены к освидетельствованию ─────────────────────────────
    work_date = work.get("work_date") or now.strftime("%d.%m.%Y")
    section("1",
        "Предъявлены к освидетельствованию",
        "Куәландыруға ұсынылды",
        [
            ("Наименование работ /\nЖұмыс атауы:",
             f"<b>{work.get('work_name') or '____________________'}</b>"),
            ("Объект / Объект:", project.get("name") or "____________________"),
            ("Участок (ПК) / Учаске (ПК):", work.get("chainage") or "____________________"),
            ("Дата выполнения /\nОрындалған күні:", work_date),
        ],
    )

    # ── 2. Проектная документация ─────────────────────────────────────────
    section("2",
        "Работы выполнены по проектной документации",
        "Жұмыстар жобалық құжаттамаға сәйкес орындалды",
        [
            ("Шифр проекта / Жоба шифры:", project.get("code") or "____________________"),
            ("Раздел / Бөлім:", work.get("design_section") or "____________________"),
            ("Разработчик / Әзірлеуші:", designer),
        ],
    )

    # ── 3. Материалы ──────────────────────────────────────────────────────
    materials = work.get("materials") or []
    mat_text = "<br/>".join(f"• {m}" for m in materials) if materials \
        else "Согласно проекту и сертификатам качества / Жобаға және сапа сертификаттарына сәйкес"
    section("3",
        "Применены материалы",
        "Қолданылған материалдар",
        [("Материалы /\nМатериалдар:", mat_text)],
    )

    # ── 4. Нормативы ──────────────────────────────────────────────────────
    normatives = work.get("normatives") or [
        "ВСН 012-88 «Строительство магистральных и промысловых трубопроводов»",
        "СП РК 2.04-103-2013* «Магістральды газ құбырлары»",
        "СП РК 1.04.02-2019 «Строительство. Исполнительная документация»",
        "ГОСТ 16037-80 «Соединения сварные стальных трубопроводов»",
    ]
    norm_text = "<br/>".join(f"• {n}" for n in normatives)
    section("4",
        "Нормативные документы",
        "Нормативтік құжаттар",
        [("НТД:", norm_text)],
    )

    # ── 5. Заключение ─────────────────────────────────────────────────────
    story += [
        _p("<b>5. Заключение / Қорытынды</b>", st["bold"], before=6, after=6),
        _p(
            "Работы выполнены в соответствии с проектной документацией, требованиями "
            "нормативных технических документов и технических условий и отвечают требованиям приёмки.",
            st["justify"], after=4,
        ),
        _p(
            "Жұмыстар жобалық құжаттамаға, нормативтік-техникалық құжаттар мен техникалық "
            "шарттардың талаптарына сәйкес орындалды және қабылдау талаптарына жауап береді.",
            st["justify"], after=8,
        ),
        _p(
            "<b>Разрешается производство последующих работ / "
            "Кейінгі жұмыстарды жүргізуге рұқсат етіледі:</b>",
            st["bold"], after=4,
        ),
        _p(work.get("next_works") or "____________________", st["justify"], after=12),
        HRFlowable(width="100%", thickness=0.5, color=colors.black),
        _sp(6),
    ]

    # ── Подписи ───────────────────────────────────────────────────────────
    sign_tbl = _tbl(
        [
            [_p("<b>Технический надзор заказчика<br/>Тапсырыс берушінің техникалық бақылаушысы</b>", st["small"]),
             _p("<b>Производитель работ<br/>Жұмыс жетекшісі</b>", st["small"]),
             _p("<b>Авторский надзор<br/>Авторлық бақылаушы</b>", st["small"])],
            [_p(f"____________ {tech_sup}", st["sign"]),
             _p(f"____________ {foreman}", st["sign"]),
             _p(f"____________ {author_sup}", st["sign"])],
            [_p(f"«____» ________ {now.year}", st["small"]),
             _p(f"«____» ________ {now.year}", st["small"]),
             _p(f"«____» ________ {now.year}", st["small"])],
        ],
        [5.5 * cm, 5.5 * cm, 5.5 * cm],
    )
    story += [sign_tbl, _sp(10)]

    # ── М.П. ──────────────────────────────────────────────────────────────
    mp_tbl = _tbl(
        [
            [_p("М.П. / М.Қ.", st["small_ctr"]),
             _p("М.П. / М.Қ.", st["small_ctr"]),
             _p("М.П. / М.Қ.", st["small_ctr"])],
            [_p("(заказчик / тапсырыс беруші)", st["small_ctr"]),
             _p("(подрядчик / мердігер)", st["small_ctr"]),
             _p("(проектировщик / жобалаушы)", st["small_ctr"])],
        ],
        [5.5 * cm, 5.5 * cm, 5.5 * cm],
        [
            ("BOX", (0, 0), (0, -1), 0.5, colors.black),
            ("BOX", (1, 0), (1, -1), 0.5, colors.black),
            ("BOX", (2, 0), (2, -1), 0.5, colors.black),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ],
    )
    story.append(mp_tbl)

    doc.build(story)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
#  ОЖР
# ════════════════════════════════════════════════════════════════════════════

def generate_ojr_pdf(project: Dict, entries: List[Dict]) -> bytes:
    _ensure_fonts()
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=1.5 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    story = []
    now = datetime.now()

    story += [
        _p("<b>ОБЩИЙ ЖУРНАЛ РАБОТ</b>", st["bold_ctr"], after=2),
        _p("<b>ЖАЛПЫ ЖҰМЫС ЖУРНАЛЫ</b>", st["bold_ctr"], after=2),
        _p("(СП РК 1.04.02-2019)", st["center"], after=10),
    ]

    info = [
        ("Наименование объекта / Объект атауы:", project.get("name") or ""),
        ("Шифр проекта / Жоба шифры:", project.get("code") or ""),
        ("Заказчик / Тапсырыс беруші:", project.get("customer_name") or ""),
        ("Генподрядчик / Бас мердігер:", project.get("contractor_name") or ""),
        ("Проектировщик / Жобалаушы:", project.get("designer_name") or ""),
        ("Технический надзор / Техникалық бақылаушы:", project.get("technical_supervisor") or ""),
        ("Начало строительства / Құрылыс басталуы:", project.get("start_date") or ""),
    ]
    info_tbl = _tbl(
        [[_p(f"<b>{r[0]}</b>", st["small"]), _p(r[1], st["small"])] for r in info],
        [7 * cm, 10 * cm],
        [("GRID", (0, 0), (-1, -1), 0.5, colors.black)],
    )
    story += [info_tbl, _sp(12)]

    story.append(_p("<b>РАЗДЕЛ 3. СВЕДЕНИЯ О ПРОИЗВОДСТВЕ РАБОТ / ЖҰМЫС ТУРАЛЫ МӘЛІМЕТТЕР</b>",
                    st["bold"], after=6))

    col_w = [1.2 * cm, 2.8 * cm, 7 * cm, 2.5 * cm, 3 * cm, 2 * cm]
    headers = [
        [_p("<b>№</b>", st["small_ctr"]),
         _p("<b>Дата / Күні</b>", st["small_ctr"]),
         _p("<b>Описание работ / Жұмыс сипаттамасы</b>", st["small_ctr"]),
         _p("<b>ПК</b>", st["small_ctr"]),
         _p("<b>Исполнитель / Орындаушы</b>", st["small_ctr"]),
         _p("<b>Примечание / Ескерту</b>", st["small_ctr"])],
    ]
    rows = []
    for i, e in enumerate(entries or [], 1):
        rows.append([
            _p(str(i), st["small_ctr"]),
            _p(e.get("date") or "", st["small"]),
            _p(e.get("description") or "", st["small"]),
            _p(e.get("chainage") or "", st["small"]),
            _p(e.get("foreman") or "", st["small"]),
            _p(e.get("note") or "", st["small"]),
        ])
    if not rows:
        rows = [[_p("", st["small"])] * 6]

    entries_tbl = _tbl(
        headers + rows,
        col_w,
        [
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1,  0), colors.HexColor("#EEEEEE")),
            ("ALIGN",      (0, 0), (0, -1),  "CENTER"),
        ],
    )
    story.append(entries_tbl)
    doc.build(story)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
#  Акт гидравлических испытаний
# ════════════════════════════════════════════════════════════════════════════

def generate_hydraulic_test_pdf(project: Dict, test: Dict) -> bytes:
    _ensure_fonts()
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=1.5 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    story = []
    now = datetime.now()
    test_date = test.get("test_date") or now.strftime("%d.%m.%Y")

    story += [
        _p("<b>АКТ ГИДРАВЛИЧЕСКИХ ИСПЫТАНИЙ ТРУБОПРОВОДА</b>", st["bold_ctr"], after=2),
        _p("<b>НА ПРОЧНОСТЬ И ГЕРМЕТИЧНОСТЬ</b>", st["bold_ctr"], after=2),
        _p("<b>ҚҰБЫРДЫҢ БЕРІКТІГІ МЕН ГЕРМЕТИКАЛЫҒЫНА ГИДРАВЛИКАЛЫҚ СЫНАҚ АКТІСІ</b>",
           st["bold_ctr"], after=4),
        _p(f"«{now.day}» {_month_ru(now.month)} {now.year} г. / "
           f"{now.year} жылғы «{now.day}» {_month_kz(now.month)}", st["center"], after=10),
    ]

    parties = [
        ("Объект / Объект:", project.get("name") or ""),
        ("Заказчик / Тапсырыс беруші:", project.get("customer_name") or ""),
        ("Подрядчик / Мердігер:", project.get("contractor_name") or ""),
        ("Дата испытания / Сынақ күні:", test_date),
    ]
    story.append(_tbl(
        [[_p(f"<b>{r[0]}</b>", st["small"]), _p(r[1], st["small"])] for r in parties],
        [5 * cm, 11.5 * cm],
        [("GRID", (0, 0), (-1, -1), 0.5, colors.black)],
    ))
    story += [_sp(8), _p("<b>ХАРАКТЕРИСТИКИ ИСПЫТУЕМОГО УЧАСТКА / СЫНАҚ УЧАСКЕСІНІҢ СИПАТТАМАСЫ</b>",
                         st["bold"], after=4)]

    chars = [
        ("Участок (ПК) / Учаске (ПК):", test.get("section_chainage") or ""),
        ("Длина / Ұзындығы:", f"{test.get('length_m') or ''} м"),
        ("Диаметр / Диаметрі:", f"{project.get('diameter_mm') or ''} мм"),
        ("Толщина стенки / Қабырғасының қалыңдығы:", f"{test.get('wall_thickness_mm') or ''} мм"),
        ("Марка стали / Болат маркасы:", test.get("steel_grade") or ""),
        ("Рабочее давление / Жұмыс қысымы:", f"{project.get('working_pressure_mpa') or ''} МПа"),
        ("Испытательное давление (прочность) / Сынақ қысымы (беріктік):",
         f"{test.get('test_pressure_mpa') or ''} МПа"),
        ("Испытательное давление (герметичность) / Сынақ қысымы (герметикалық):",
         f"{test.get('tightness_pressure_mpa') or ''} МПа"),
    ]
    story.append(_tbl(
        [[_p(r[0], st["small"]), _p(r[1], st["small"])] for r in chars],
        [9 * cm, 7.5 * cm],
        [("GRID", (0, 0), (-1, -1), 0.5, colors.black)],
    ))
    story += [_sp(8), _p("<b>РЕЗУЛЬТАТЫ / НӘТИЖЕЛЕР</b>", st["bold"], after=4)]

    results = [
        ("Давление в начале / Басталу қысымы:", f"{test.get('pressure_start') or ''} МПа"),
        ("Давление в конце / Соңғы қысым:", f"{test.get('pressure_end') or ''} МПа"),
        ("Время выдержки / Ұстау уақыты:", f"{test.get('duration_hours') or 24} часов / сағат"),
        ("Результат / Нәтиже:", test.get("result") or "УДОВЛЕТВОРИТЕЛЬНО / ҚАНАҒАТТАНАРЛЫҚ"),
    ]
    story.append(_tbl(
        [[_p(r[0], st["small"]), _p(r[1], st["small"])] for r in results],
        [9 * cm, 7.5 * cm],
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#E8F5E9")),
        ],
    ))
    story += [
        _sp(10),
        _p(
            f"<b>ЗАКЛЮЧЕНИЕ / ҚОРЫТЫНДЫ:</b> Трубопровод участка {test.get('section_chainage') or '___'} "
            f"выдержал гидравлическое испытание на прочность давлением "
            f"{test.get('test_pressure_mpa') or '___'} МПа и на герметичность давлением "
            f"{test.get('tightness_pressure_mpa') or '___'} МПа. "
            f"Трубопровод к дальнейшему строительству допускается.",
            st["justify"], before=6, after=10,
        ),
        _p("Нормативный документ / Нормативтік құжат: СП РК 2.04-103-2013*, п. 10.3",
           st["small"], after=12),
        HRFlowable(width="100%", thickness=0.5, color=colors.black),
        _sp(6),
    ]

    tech_sup = project.get("technical_supervisor") or "____________________"
    sign_tbl = _tbl(
        [
            [_p("<b>Технический надзор / Техникалық бақылаушы</b>", st["small"]),
             _p("<b>Производитель работ / Жұмыс жетекшісі</b>", st["small"]),
             _p("<b>Представитель лаборатории / Зертхана өкілі</b>", st["small"])],
            [_p(f"____________ {tech_sup}", st["sign"]),
             _p("____________ ________________", st["sign"]),
             _p("____________ ________________", st["sign"])],
            [_p(f"«____» ________ {now.year}", st["small"]),
             _p(f"«____» ________ {now.year}", st["small"]),
             _p(f"«____» ________ {now.year}", st["small"])],
        ],
        [5.5 * cm, 5.5 * cm, 5.5 * cm],
    )
    story.append(sign_tbl)

    doc.build(story)
    return buf.getvalue()


# ── Диспетчер по типу документа ─────────────────────────────────────────────

def render_document_as_pdf(doc_type: str, project: Dict, content: Dict) -> bytes:
    """
    Универсальный диспетчер: выбирает нужный рендерер по типу документа.
    doc_type — значение DocumentType (строка).
    """
    if doc_type == "aosr":
        return generate_aosr_pdf(project, content)
    elif doc_type == "ojr":
        entries = content.get("entries") or []
        return generate_ojr_pdf(project, entries)
    elif doc_type == "hydraulic_test":
        return generate_hydraulic_test_pdf(project, content)
    else:
        # Для остальных типов — заглушка с базовой информацией
        return _generic_pdf(project, doc_type, content)


def _generic_pdf(project: Dict, doc_type: str, content: Dict) -> bytes:
    _ensure_fonts()
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2.5 * cm, rightMargin=1.5 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    story = [
        _p(f"<b>{doc_type.upper()}</b>", st["bold_ctr"], after=4),
        _p(project.get("name") or "", st["center"], after=10),
    ]
    for k, v in content.items():
        if v and k not in ("entries",):
            story.append(_p(f"<b>{k}:</b> {v}", st["left"], after=3))
    doc.build(story)
    return buf.getvalue()
