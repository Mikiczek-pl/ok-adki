import io
import os
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# =========================
# STAŁE
# =========================
DPI = 300
H_MM = 150.0
PANEL_MM = 130.0
SPINE_MM = 10.0

LOGO_FILES = {
    "Białe": "bluray_white.png",
    "Czarne": "bluray_black.png",
    "Niebieskie": "bluray_blue.png",
}

FONT_CHOICES = {
    "Sans (DejaVu)": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    "Serif (DejaVu)": ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"),
    "Mono (DejaVu)": ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"),
}

# =========================
# UI STYLE (większe, kolorowe zakładki + duży przycisk)
# =========================
APP_ACCENT = "#2563eb"  # NIEBIESKI
st.set_page_config(page_title="Generator okładek Blu-ray", layout="wide")

st.markdown(
    f"""
    <style>
    /* Tytuł */
    h1 {{
        font-size: 44px !important;
        font-weight: 900 !important;
        letter-spacing: -0.5px;
        margin-bottom: 6px !important;
    }}

    /* Opis pod tytułem */
    .stCaption {{
        font-size: 15px !important;
        opacity: 0.85;
    }}

    /* Zakładki (Tabs) - większe i bardziej "przyciskowe" */
    div[data-baseweb="tab-list"] {{
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }}

    button[data-baseweb="tab"] {{
        font-size: 16px !important;
        font-weight: 800 !important;
        padding: 12px 16px !important;
        border-radius: 14px !important;
        background: rgba(0,0,0,0.04) !important;
        border: 1px solid rgba(0,0,0,0.08) !important;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        background: {APP_ACCENT} !important;
        color: white !important;
        border: 1px solid {APP_ACCENT} !important;
        box-shadow: 0 10px 24px rgba(0,0,0,0.12) !important;
    }}

    /* Duży przycisk pobierania */
    .stDownloadButton > button {{
        width: 100% !important;
        height: 52px !important;
        border-radius: 14px !important;
        font-size: 18px !important;
        font-weight: 900 !important;
        background: {APP_ACCENT} !important;
        color: white !important;
        border: 1px solid {APP_ACCENT} !important;
        box-shadow: 0 14px 28px rgba(0,0,0,0.16) !important;
    }}
    .stDownloadButton > button:hover {{
        filter: brightness(0.95);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# UTILS
# =========================
def mm_to_px(mm: float, dpi: int = DPI) -> int:
    return int(round((mm / 25.4) * dpi))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def hex_to_rgba(hex_color: str, a=255):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b, a)

def try_font_pair(font_name: str, bold: bool, size: int):
    regular_path, bold_path = FONT_CHOICES.get(font_name, ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"))
    path = bold_path if bold else regular_path
    try:
        return ImageFont.truetype(path, size=size)
    except:
        return ImageFont.load_default()

def crop_by_percent(img: Image.Image, left_p: float, right_p: float, top_p: float, bottom_p: float) -> Image.Image:
    w, h = img.size
    left = int(round(w * (left_p / 100.0)))
    right = int(round(w * (1.0 - right_p / 100.0)))
    top = int(round(h * (top_p / 100.0)))
    bottom = int(round(h * (1.0 - bottom_p / 100.0)))

    left = clamp(left, 0, w - 1)
    right = clamp(right, left + 1, w)
    top = clamp(top, 0, h - 1)
    bottom = clamp(bottom, top + 1, h)
    return img.crop((left, top, right, bottom))

# ROZCIĄGANIE do 130x150 (bez kadrowania)
def fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    return img.convert("RGBA").resize((target_w, target_h), Image.Resampling.LANCZOS)

def load_logo(variant: str) -> Image.Image:
    path = LOGO_FILES.get(variant)
    if not path:
        raise FileNotFoundError("Nieznany wariant logo.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Brak pliku logo: {path} (wrzuć do folderu obok app.py).")
    return Image.open(path).convert("RGBA")

def resize_logo_to_width(logo: Image.Image, max_w_px: int) -> Image.Image:
    if logo.width <= max_w_px:
        return logo
    ratio = max_w_px / logo.width
    return logo.resize((int(logo.width * ratio), int(logo.height * ratio)), Image.Resampling.LANCZOS)

def paste_logo_at(canvas: Image.Image, logo: Image.Image,
                  area_x: int, area_y: int, area_w: int, area_h: int,
                  corner_lr: str, corner_tb: str, margin_px: int):
    x = area_x + margin_px if corner_lr == "Lewo" else area_x + area_w - logo.width - margin_px
    y = area_y + margin_px if corner_tb == "Góra" else area_y + area_h - logo.height - margin_px
    canvas.alpha_composite(logo, (x, y))

def wrap_text_by_pixels(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width_px: int):
    lines_out = []
    for raw_line in (text or "").splitlines():
        if raw_line.strip() == "":
            lines_out.append("")
            continue

        words = raw_line.split()
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            tw = bbox[2] - bbox[0]
            if tw <= max_width_px:
                current = test
            else:
                if current:
                    lines_out.append(current)
                current = w
        if current:
            lines_out.append(current)
    return lines_out

def draw_multiline_centered(panel: Image.Image, text: str, fill_rgba, font_choice: str, bold: bool,
                            base_size_px: int, margin_px: int, v_align: str):
    text = (text or "").strip("\n")
    if not text:
        return

    draw = ImageDraw.Draw(panel)
    max_w = panel.width - 2 * margin_px
    max_h = panel.height - 2 * margin_px

    size = int(base_size_px)
    while size >= 10:
        font = try_font_pair(font_choice, bold, size)
        lines = wrap_text_by_pixels(draw, text, font, max_w)

        max_line_w = 0
        heights = []
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln if ln else " ", font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            max_line_w = max(max_line_w, w)
            heights.append(h)

        gap = max(4, int(size * 0.20))
        block_h = sum(heights) + gap * (len(lines) - 1)

        if max_line_w <= max_w and block_h <= max_h:
            break
        size -= 2

    font = try_font_pair(font_choice, bold, size)
    lines = wrap_text_by_pixels(draw, text, font, max_w)

    gap = max(4, int(size * 0.20))
    metrics = []
    block_h = 0
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln if ln else " ", font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        metrics.append((ln, w, h))
        block_h += h
    block_h += gap * (len(lines) - 1)

    if v_align == "top":
        y = margin_px
    elif v_align == "bottom":
        y = panel.height - margin_px - block_h
    else:
        y = (panel.height - block_h) // 2

    for ln, w, h in metrics:
        x = (panel.width - w) // 2
        draw.text((x, y), ln, font=font, fill=fill_rgba)
        y += h + gap

def draw_spine_text_centered(canvas: Image.Image, spine_x: int, spine_w: int, canvas_h: int,
                             text: str, text_rgba, font_size_px: int, font_choice: str, bold: bool,
                             rotation: int = -90):
    text = (text or "").strip()
    if not text:
        return

    base = Image.new("RGBA", (canvas_h, spine_w), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)

    fs = int(font_size_px)
    while fs >= 10:
        font = try_font_pair(font_choice, bold, fs)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        if tw <= int(canvas_h * 0.94):
            break
        fs -= 2

    font = try_font_pair(font_choice, bold, fs)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = (canvas_h - tw) // 2
    y = (spine_w - th) // 2
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=text_rgba)

    rot = base.rotate(rotation, expand=True)

    target = Image.new("RGBA", (spine_w, canvas_h), (0, 0, 0, 0))
    ox = (target.width - rot.width) // 2
    oy = (target.height - rot.height) // 2
    target.alpha_composite(rot, (ox, oy))

    canvas.alpha_composite(target, (spine_x, 0))

def corner_to_lr_tb(corner: str):
    corner = corner.lower()
    tb = "Góra" if "gór" in corner else "Dół"
    lr = "Lewo" if "lewy" in corner else "Prawo"
    return lr, tb

# =========================
# APP
# =========================
st.title("Generator okładek Blu-ray")
st.caption("Prosto: wgraj pliki → ustaw grzbiet → opcjonalnie ustaw tył i logo → pobierz JPG.")

# ---- defaults ----
defaults = {
    "swap": False,

    # GRZBIET
    "spine_color_hex": "#000000",
    "spine_text": "TYTUŁ",
    "spine_text_color_hex": "#ffffff",
    "spine_font_px": 90,
    "spine_font_choice": "Sans (DejaVu)",
    "spine_bold": True,

    # TYŁ domyślnie: czarny + biały napis
    "back_mode": "Kolor + tekst",
    "back_color_hex": "#000000",
    "back_text": "",
    "back_text_color_hex": "#ffffff",
    "back_text_size_px": 46,
    "back_text_pos": "Środek",
    "back_text_bold": False,
    "back_text_font": "Sans (DejaVu)",

    # LOGO domyślnie: szerokość 15mm, margines 5mm
    "logo_variant": "Białe",
    "logo_on_front": True,
    "logo_on_back": True,
    "logo_corner_front": "Prawy dół",
    "logo_corner_back": "Lewy dół",
    "logo_max_w_mm": 15.0,
    "logo_margin_mm": 5.0,

    # CROP (opcjonalne)
    "f_left": 0.0, "f_right": 0.0, "f_top": 0.0, "f_bottom": 0.0,
    "b_left": 0.0, "b_right": 0.0, "b_top": 0.0, "b_bottom": 0.0,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

left, right = st.columns([1, 1.6], gap="large")

with left:
    tabs = st.tabs(["Pliki", "Grzbiet", "Tył", "Logo", "Zaawansowane"])

    with tabs[0]:
        st.subheader("Pliki")
        st.file_uploader("Przód", type=["png", "jpg", "jpeg", "webp"], key="u_front")
        st.file_uploader("Tył (opcjonalnie)", type=["png", "jpg", "jpeg", "webp"], key="u_back")
        st.checkbox("Zamień przód z tyłem", key="swap")
        st.caption("Jeśli wgrasz plik TYŁ, aplikacja użyje go automatycznie zamiast tła z tekstem.")

    # Auto: jeśli wgrano TYŁ -> Obraz, inaczej Kolor+tekst
    if st.session_state.get("u_back") is not None:
        st.session_state["back_mode"] = "Obraz"
    else:
        st.session_state["back_mode"] = "Kolor + tekst"

    with tabs[1]:
        st.subheader("Grzbiet")
        st.text_input("Napis na grzbiecie", key="spine_text")
        st.color_picker("Kolor grzbietu", key="spine_color_hex")

        c1, c2 = st.columns(2)
        with c1:
            st.color_picker("Kolor napisu", key="spine_text_color_hex")
            st.checkbox("Gruby napis", key="spine_bold")
        with c2:
            st.selectbox("Czcionka", list(FONT_CHOICES.keys()), key="spine_font_choice")
            st.slider("Wielkość napisu", 10, 220, key="spine_font_px")

    with tabs[2]:
        st.subheader("Tył")

        if st.session_state["back_mode"] == "Obraz":
            st.success("Tył: używany jest wgrany plik TYŁ.")
        else:
            st.info("Tył: domyślnie czarny z białym tekstem (wielowierszowym).")

        if st.session_state["back_mode"] == "Kolor + tekst":
            st.color_picker("Kolor tła", key="back_color_hex")
            st.text_area("Tekst na tyle (wiele wierszy)", key="back_text", height=140)

            c1, c2 = st.columns(2)
            with c1:
                st.color_picker("Kolor tekstu", key="back_text_color_hex")
                st.checkbox("Gruby tekst", key="back_text_bold")
            with c2:
                st.selectbox("Czcionka", list(FONT_CHOICES.keys()), key="back_text_font")
                st.slider("Wielkość tekstu", 10, 140, key="back_text_size_px")

            st.selectbox("Pozycja tekstu", ["Góra", "Środek", "Dół"], key="back_text_pos")

    with tabs[3]:
        st.subheader("Logo Blu-ray")
        st.selectbox("Wariant logo", ["Białe", "Czarne", "Niebieskie"], key="logo_variant")

        c1, c2 = st.columns(2)
        with c1:
            st.checkbox("Logo na przód", key="logo_on_front")
            st.selectbox("Pozycja (przód)", ["Lewy górny", "Prawy górny", "Lewy dół", "Prawy dół"], key="logo_corner_front")
        with c2:
            st.checkbox("Logo na tył", key="logo_on_back")
            st.selectbox("Pozycja (tył)", ["Lewy górny", "Prawy górny", "Lewy dół", "Prawy dół"], key="logo_corner_back")

        st.slider("Rozmiar logo (mm)", 10.0, 60.0, key="logo_max_w_mm")
        st.slider("Margines logo (mm)", 2.0, 20.0, key="logo_margin_mm")

    with tabs[4]:
        st.subheader("Zaawansowane")
        st.caption("Użyj tylko, jeśli kadr jest niepoprawny. Zwykle zostaw 0%.")

        st.markdown("**Przód – przycinanie (%)**")
        st.slider("Lewy", 0.0, 40.0, key="f_left")
        st.slider("Prawy", 0.0, 40.0, key="f_right")
        st.slider("Góra", 0.0, 40.0, key="f_top")
        st.slider("Dół", 0.0, 40.0, key="f_bottom")

        st.markdown("**Tył – przycinanie (%)**")
        st.slider("Lewy ", 0.0, 40.0, key="b_left")
        st.slider("Prawy ", 0.0, 40.0, key="b_right")
        st.slider("Góra ", 0.0, 40.0, key="b_top")
        st.slider("Dół ", 0.0, 40.0, key="b_bottom")

with right:
    st.subheader("Podgląd okładki")

    if st.session_state.get("u_front") is None:
        st.info("Wgraj plik PRZÓD (po lewej), żeby zobaczyć podgląd.")
        st.stop()

    front_in = Image.open(st.session_state["u_front"]).convert("RGBA")

    panel_w = mm_to_px(PANEL_MM, DPI)
    canvas_h = mm_to_px(H_MM, DPI)

    # BACK
    if st.session_state["back_mode"] == "Kolor + tekst":
        back_panel = Image.new("RGBA", (panel_w, canvas_h), hex_to_rgba(st.session_state["back_color_hex"], 255))
        v_align_map = {"Góra": "top", "Środek": "center", "Dół": "bottom"}
        draw_multiline_centered(
            back_panel,
            st.session_state["back_text"],
            hex_to_rgba(st.session_state["back_text_color_hex"], 255),
            st.session_state["back_text_font"],
            bool(st.session_state["back_text_bold"]),
            int(st.session_state["back_text_size_px"]),
            margin_px=int(panel_w * 0.08),
            v_align=v_align_map[st.session_state["back_text_pos"]],
        )
        back_in = back_panel
    else:
        back_in = Image.open(st.session_state["u_back"]).convert("RGBA")

    # SWAP
    if st.session_state["swap"]:
        front_in, back_in = back_in, front_in

    # crop + fit
    front_cropped = crop_by_percent(front_in, st.session_state["f_left"], st.session_state["f_right"],
                                    st.session_state["f_top"], st.session_state["f_bottom"])
    back_cropped = crop_by_percent(back_in, st.session_state["b_left"], st.session_state["b_right"],
                                   st.session_state["b_top"], st.session_state["b_bottom"])

    front_fit = fit_cover(front_cropped, panel_w, canvas_h)
    back_fit  = fit_cover(back_cropped, panel_w, canvas_h)

    spine_w = mm_to_px(SPINE_MM, DPI)
    canvas_w = panel_w + spine_w + panel_w

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    back_x = 0
    spine_x = panel_w
    front_x = panel_w + spine_w

    canvas.alpha_composite(back_fit, (back_x, 0))

    spine_rgba = hex_to_rgba(st.session_state["spine_color_hex"], 255)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([spine_x, 0, spine_x + spine_w, canvas_h], fill=spine_rgba)

    canvas.alpha_composite(front_fit, (front_x, 0))

    draw_spine_text_centered(
        canvas,
        spine_x=spine_x,
        spine_w=spine_w,
        canvas_h=canvas_h,
        text=st.session_state["spine_text"],
        text_rgba=hex_to_rgba(st.session_state["spine_text_color_hex"], 255),
        font_size_px=int(st.session_state["spine_font_px"]),
        font_choice=st.session_state["spine_font_choice"],
        bold=bool(st.session_state["spine_bold"]),
        rotation=-90
    )

    # logo
    try:
        logo = load_logo(st.session_state["logo_variant"])
        logo_max_w_px = mm_to_px(float(st.session_state["logo_max_w_mm"]), DPI)
        margin_px = mm_to_px(float(st.session_state["logo_margin_mm"]), DPI)
        logo = resize_logo_to_width(logo, logo_max_w_px)

        if st.session_state["logo_on_front"]:
            lr, tb = corner_to_lr_tb(st.session_state["logo_corner_front"])
            paste_logo_at(canvas, logo, front_x, 0, panel_w, canvas_h, lr, tb, margin_px)

        if st.session_state["logo_on_back"]:
            lr, tb = corner_to_lr_tb(st.session_state["logo_corner_back"])
            paste_logo_at(canvas, logo, back_x, 0, panel_w, canvas_h, lr, tb, margin_px)

    except FileNotFoundError as e:
        st.error(str(e))

    st.image(canvas, use_container_width=True)

    out_rgb = canvas.convert("RGB")
    buf = io.BytesIO()
    out_rgb.save(buf, format="JPEG", quality=95, subsampling=0, dpi=(DPI, DPI))

    st.download_button(
        "⬇️ Pobierz JPG",
        data=buf.getvalue(),
        file_name="okladka_bluray_270x150.jpg",
        mime="image/jpeg",
        use_container_width=True
    )
