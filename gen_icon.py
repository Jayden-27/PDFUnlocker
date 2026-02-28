"""生成 PDFUnlocker 高质量 ICO 图标（BMP 格式，兼容 Windows + PyInstaller）"""

from PIL import Image, ImageDraw, ImageFont
import math
import struct
import os

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ─── 圆角矩形背景（红橙渐变，PDF 风格）───
rad = 180
for y in range(S):
    t = y / S
    r = int(220 + (190 - 220) * t)
    g = int(50 + (30 - 50) * t)
    b = int(47 + (60 - 47) * t)
    draw.line([(0, y), (S - 1, y)], fill=(r, g, b, 255))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=rad, fill=255)
img.putalpha(mask)

# ─── PDF 文件图标（白色，带折角）───
fx, fy, fw, fh, fold = 180, 120, 380, 500, 70
body = [
    (fx, fy + fold), (fx + fw - fold, fy + fold), (fx + fw - fold, fy),
    (fx + fw, fy + fold), (fx + fw, fy + fh), (fx, fy + fh),
]
draw.polygon(body, fill=(255, 255, 255, 230), outline=(255, 255, 255, 250), width=4)
# 折角
draw.polygon(
    [(fx + fw - fold, fy), (fx + fw, fy + fold), (fx + fw - fold, fy + fold)],
    fill=(255, 255, 255, 130), outline=(255, 255, 255, 180), width=3,
)

# ─── "PDF" 文字 ───
try:
    font = ImageFont.truetype("arialbd.ttf", 130)
except OSError:
    try:
        font = ImageFont.truetype("arial.ttf", 130)
    except OSError:
        font = ImageFont.load_default()

text_color = (200, 45, 40, 220)
bbox = draw.textbbox((0, 0), "PDF", font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = fx + (fw - tw) // 2
ty = fy + fold + 30
draw.text((tx, ty), "PDF", fill=text_color, font=font)

# ─── 文档横线 ───
line_color = (200, 80, 70, 100)
for i in range(3):
    ly = fy + fold + 190 + i * 50
    lx_end = fx + fw - 40 - (50 if i == 2 else 0)
    if ly + 10 < fy + fh - 20:
        draw.rounded_rectangle([fx + 40, ly, lx_end, ly + 14], radius=7, fill=line_color)

# ─── 打开的锁（右下角，表示"解锁"）───
lock_cx, lock_cy = 680, 680
lock_w, lock_h = 160, 120
lock_r = 12

# 锁体（金色圆角矩形）
lock_color = (255, 210, 60, 240)
lock_dark = (200, 160, 30, 240)
draw.rounded_rectangle(
    [lock_cx - lock_w // 2, lock_cy, lock_cx + lock_w // 2, lock_cy + lock_h],
    radius=lock_r, fill=lock_color, outline=lock_dark, width=6,
)

# 锁孔（深色圆 + 下方短线）
hole_r = 16
draw.ellipse(
    [lock_cx - hole_r, lock_cy + 30, lock_cx + hole_r, lock_cy + 30 + hole_r * 2],
    fill=lock_dark,
)
draw.rectangle(
    [lock_cx - 6, lock_cy + 30 + hole_r, lock_cx + 6, lock_cy + 30 + hole_r + 25],
    fill=lock_dark,
)

# 锁钩（U 形，打开状态 — 右侧翘起）
hook_w = 100
hook_thick = 22
hook_top = lock_cy - 80
hook_color = (210, 170, 40, 240)

# 左竖线
draw.rounded_rectangle(
    [lock_cx - hook_w // 2, hook_top + 40, lock_cx - hook_w // 2 + hook_thick, lock_cy + 10],
    radius=hook_thick // 2, fill=hook_color,
)
# 右竖线（翘起，更短）
draw.rounded_rectangle(
    [lock_cx + hook_w // 2 - hook_thick, hook_top - 20, lock_cx + hook_w // 2, lock_cy - 30],
    radius=hook_thick // 2, fill=hook_color,
)
# 顶部弧线（连接左右）
draw.arc(
    [lock_cx - hook_w // 2, hook_top, lock_cx + hook_w // 2, hook_top + 80],
    start=180, end=0, fill=hook_color, width=hook_thick,
)


# ─── 手工构建 ICO（BMP 格式，最大兼容性）───
def make_ico_bmp(pil_img, size):
    resized = pil_img.resize((size, size), Image.LANCZOS).convert("RGBA")
    pixels = list(resized.getdata())
    w, h = size, size
    bih = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, w * h * 4, 0, 0, 0, 0)
    xor_rows = []
    for row in range(h - 1, -1, -1):
        row_data = b""
        for col in range(w):
            r, g, b, a = pixels[row * w + col]
            row_data += struct.pack("BBBB", b, g, r, a)
        xor_rows.append(row_data)
    xor_data = b"".join(xor_rows)
    row_bytes = (w + 31) // 32 * 4
    and_data = b"\x00" * (row_bytes * h)
    return bih + xor_data + and_data


sizes = [256, 48, 32, 16]
entries = []
for s in sizes:
    entries.append((s, make_ico_bmp(img, s)))

header = struct.pack("<HHH", 0, 1, len(entries))
dir_entries = b""
offset = 6 + 16 * len(entries)
for s, bmp_data in entries:
    w_byte = 0 if s >= 256 else s
    h_byte = 0 if s >= 256 else s
    dir_entries += struct.pack(
        "<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, len(bmp_data), offset
    )
    offset += len(bmp_data)

ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
with open(ico_path, "wb") as f:
    f.write(header)
    f.write(dir_entries)
    for _, bmp_data in entries:
        f.write(bmp_data)

# 保存预览 PNG
img.resize((256, 256), Image.LANCZOS).save(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_preview.png")
)

print(f"ICO written: {os.path.getsize(ico_path):,} bytes")
print(f"Sizes: {[s for s, _ in entries]}")
