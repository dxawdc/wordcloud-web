# -*- coding: utf-8 -*-
"""
词云制作工具 - 网页版
后端：Flask + wordcloud + jieba（图标蒙版复用 stylecloud 自带的 Font Awesome 字体）

三种模式：
  1. text  整段文本 jieba 分词 → 词云
  2. freq  「关键词 权重」逐行 → 词云
蒙版来源：none / 上传 png / Font Awesome 图标，三种模式通用。
"""
import os
import io
import base64
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify, render_template
from wordcloud import WordCloud, STOPWORDS
import jieba

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 上传上限 16MB
app.config["TEMPLATES_AUTO_RELOAD"] = True  # 改前端模板后无需重启服务

# ---------- 字体 ----------
WIN_FONTS = r"C:\Windows\Fonts"
FONTS = {
    "萌趣软糖": os.path.join(BASE_DIR, "字魂萌趣软糖体.ttf"),
    "新青年体": os.path.join(BASE_DIR, "WenYue-XinQingNianTi-W8-J-2.otf"),
    "微软雅黑": os.path.join(WIN_FONTS, "msyh.ttc"),
    "黑体": os.path.join(WIN_FONTS, "simhei.ttf"),
    "宋体": os.path.join(WIN_FONTS, "simsun.ttc"),
    "仿宋": os.path.join(WIN_FONTS, "simfang.ttf"),
    "楷体": os.path.join(WIN_FONTS, "simkai.ttf"),
    "Times New Roman": os.path.join(WIN_FONTS, "times.ttf"),
}
AVAILABLE_FONTS = {k: v for k, v in FONTS.items() if os.path.exists(v)}

# ---------- 配色 ----------
COLORMAPS = [
    "Set2", "tab10", "Dark2", "Pastel1", "Set3",
    "viridis", "plasma", "rainbow", "cool", "autumn",
]


def sample_colormap(name, n=8):
    """在 0~1 整个区间线性采样，返回 n 个十六进制颜色，供前端预览色板。"""
    cmap = matplotlib.colormaps[name]
    out = []
    for i in range(n):
        c = cmap(i / (n - 1))
        out.append("#%02x%02x%02x" % (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255)))
    return out


COLORMAP_SWATCHES = [{"name": nm, "colors": sample_colormap(nm)} for nm in COLORMAPS]

# ---------- Font Awesome 图标蒙版 ----------
_ICON_CACHE = {}


def _icon_font():
    """惰性加载 stylecloud 自带的 Font Awesome 资源，返回 {prefix: IconFont}。"""
    if _ICON_CACHE:
        return _ICON_CACHE
    from icon_font_to_png.icon_font import IconFont
    from stylecloud.stylecloud import STATIC_PATH

    css = os.path.join(STATIC_PATH, "fontawesome.min.css")
    files = {
        "fas": "fa-solid-900.ttf",
        "far": "fa-regular-400.ttf",
        "fab": "fa-brands-400.ttf",
    }
    for prefix, ttf in files.items():
        ttf_path = os.path.join(STATIC_PATH, ttf)
        _ICON_CACHE[prefix] = {
            "icon": IconFont(css_file=css, ttf_file=ttf_path),
            "ttf": ttf_path,
        }
    return _ICON_CACHE


# 前端可选图标（名称 -> Font Awesome 标识）
ICONS = {
    "云朵": "fas fa-cloud",
    "爱心": "fas fa-heart",
    "五角星": "fas fa-star",
    "对话气泡": "fas fa-comment",
    "点赞": "fas fa-thumbs-up",
    "旗帜": "fas fa-flag",
    "树": "fas fa-tree",
    "音符": "fas fa-music",
    "铃铛": "fas fa-bell",
    "圆形": "fas fa-circle",
    "苹果": "fas fa-apple-alt",
    "用户": "fas fa-user",
}


def gen_icon_mask(icon_name, size=800):
    """用 PIL 把 Font Awesome 图标渲染成 wordcloud 蒙版（白底=不绘制，图标区=绘制）。

    不调用 stylecloud 的 export_icon，因为它依赖 Pillow 已移除的 draw.textsize。
    """
    prefix, name = icon_name.split(" ")
    key = name[len("fa-"):] if name.startswith("fa-") else name
    cache = _icon_font()
    if prefix not in cache:
        prefix = "fas"
    entry = cache[prefix]
    char = entry["icon"].css_icons.get(key)
    if char is None:
        raise ValueError(f"未找到图标：{icon_name}")

    font = ImageFont.truetype(entry["ttf"], int(size * 0.9))
    img = Image.new("L", (size, size), 255)  # 白底
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), char, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1]
    draw.text((x, y), char, font=font, fill=0)  # 黑色图标
    return np.array(img)


def gen_icon_preview(icon_name, size=64, color=(200, 205, 215, 255)):
    """渲染图标缩略图（透明底、浅色），供前端预览选择，返回 base64 data URL。"""
    prefix, name = icon_name.split(" ")
    key = name[len("fa-"):] if name.startswith("fa-") else name
    cache = _icon_font()
    if prefix not in cache:
        prefix = "fas"
    entry = cache[prefix]
    char = entry["icon"].css_icons.get(key)
    if char is None:
        return ""
    font = ImageFont.truetype(entry["ttf"], int(size * 0.82))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), char, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1]
    draw.text((x, y), char, font=font, fill=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# 启动时为每个图标生成预览缩略图
ICON_SWATCHES = [{"name": k, "img": gen_icon_preview(v)} for k, v in ICONS.items()]


# ---------- 文本处理 ----------
def split_words(raw):
    """前端用 / 或换行分隔的词列表。"""
    if not raw:
        return []
    out = []
    for chunk in raw.replace("\n", "/").split("/"):
        w = chunk.strip()
        if w:
            out.append(w)
    return out


def cut_text(text, add_words, stop_words):
    for w in add_words:
        jieba.add_word(w)
    seg = jieba.cut(str(text), cut_all=False)
    words = " ".join(seg)
    stopwords = STOPWORDS.copy()
    for w in stop_words:
        stopwords.add(w)
    return words, stopwords


def parse_frequencies(raw):
    """解析「关键词 权重」逐行文本，分隔符支持空格 / 逗号 / 制表符。"""
    freq = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.replace(",", " ").replace("\t", " ").split()
        if len(parts) < 2:
            continue
        word = parts[0]
        try:
            weight = float(parts[1])
        except ValueError:
            continue
        freq[word] = weight
    return freq


# ---------- 文件导入 ----------
def _decode(raw_bytes):
    """字节解码，自动尝试 utf-8 / gbk，避免中文乱码。"""
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _rows_from_csv(raw_bytes):
    import csv
    text = _decode(raw_bytes)
    return [row for row in csv.reader(text.splitlines()) if row]


def _rows_from_xlsx(stream):
    import openpyxl
    wb = openpyxl.load_workbook(stream, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        cells = ["" if c is None else str(c) for c in row]
        if any(c.strip() for c in cells):
            rows.append(cells)
    wb.close()
    return rows


def rows_to_content(rows, mode):
    """表格行按模式转成填入 textarea 的文本。"""
    if mode == "freq":
        # 取前两列：关键词 权重（表头/非数字行由 parse_frequencies 自动忽略）
        lines = []
        for r in rows:
            if len(r) >= 2:
                lines.append(f"{r[0]} {r[1]}")
        return "\n".join(lines)
    # text 模式：所有单元格拼成大段文本
    return " ".join(c for r in rows for c in r if c.strip())


# ---------- 路由 ----------
@app.route("/")
def index():
    return render_template(
        "index.html",
        fonts=list(AVAILABLE_FONTS.keys()),
        swatches=COLORMAP_SWATCHES,
        icon_swatches=ICON_SWATCHES,
    )


@app.route("/api/import", methods=["POST"])
def import_file():
    """解析上传的 txt / csv / xlsx，返回填入 textarea 的文本。"""
    try:
        mode = request.form.get("mode", "text")
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify(error="未选择文件"), 400
        ext = os.path.splitext(f.filename)[1].lower()
        if ext == ".txt":
            content = _decode(f.read())
        elif ext == ".csv":
            content = rows_to_content(_rows_from_csv(f.read()), mode)
        elif ext == ".xlsx":
            content = rows_to_content(_rows_from_xlsx(f.stream), mode)
        else:
            return jsonify(error=f"不支持的格式：{ext}（仅支持 txt / csv / xlsx）"), 400
        if not content.strip():
            return jsonify(error="文件内容为空或无法解析"), 400
        return jsonify(content=content)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(error=f"{type(e).__name__}: {e}"), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        mode = request.form.get("mode", "text")
        font_key = request.form.get("font", next(iter(AVAILABLE_FONTS)))
        font_path = AVAILABLE_FONTS.get(font_key, next(iter(AVAILABLE_FONTS.values())))
        colormap = request.form.get("colormap", "Set2")
        bg_color = request.form.get("bg_color", "white")
        mask_type = request.form.get("mask_type", "none")

        width = int(request.form.get("width", 1200))
        height = int(request.form.get("height", 800))
        scale = float(request.form.get("scale", 2))
        max_words = int(request.form.get("max_words", 200))
        max_font = int(request.form.get("max_font_size", 200))
        min_font = int(request.form.get("min_font_size", 8))

        # 蒙版
        mask = None
        if mask_type == "image" and "mask_file" in request.files:
            f = request.files["mask_file"]
            if f and f.filename:
                mask = np.array(Image.open(f.stream).convert("RGB"))
        elif mask_type == "icon":
            icon_key = request.form.get("icon", next(iter(ICONS)))
            mask = gen_icon_mask(ICONS.get(icon_key, "fas fa-cloud"), size=800)

        wc = WordCloud(
            width=width,
            height=height,
            mask=mask,
            scale=scale,
            max_words=max_words,
            max_font_size=max_font,
            min_font_size=min_font,
            background_color=bg_color,
            colormap=colormap,
            font_path=font_path,
            random_state=50,
            prefer_horizontal=0.9,
        )

        if mode == "freq":
            freq = parse_frequencies(request.form.get("content", ""))
            if not freq:
                return jsonify(error="未解析到有效的「关键词 权重」数据"), 400
            wc.generate_from_frequencies(freq)
            count = len(freq)
        else:
            text = request.form.get("content", "")
            if len(text.strip()) < 2:
                return jsonify(error="待绘制文本太短"), 400
            add_words = split_words(request.form.get("add_words", ""))
            stop_words = split_words(request.form.get("stop_words", ""))
            words, stopwords = cut_text(text, add_words, stop_words)
            wc.stopwords = stopwords
            wc.generate_from_text(words)
            count = len(wc.words_)

        img = wc.to_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode()
        return jsonify(image="data:image/png;base64," + data, count=count)
    except Exception as e:  # 把后端异常透传到前端便于排查
        import traceback
        traceback.print_exc()
        return jsonify(error=f"{type(e).__name__}: {e}"), 500


if __name__ == "__main__":
    print("词云网页版已启动： http://127.0.0.1:5000")
    print("可用字体：", list(AVAILABLE_FONTS.keys()))
    app.run(host="127.0.0.1", port=5000, debug=False)
