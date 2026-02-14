#!/usr/bin/env python3
"""
Render StockBot ANSI output to colored PNG using Pillow.
Parses ANSI color codes and renders segment-by-segment (fast).
Usage: render_and_send.py [cc|csp]  (default: cc)
"""
import re, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont

BG = (30, 30, 46)
FG = (205, 214, 244)

# Catppuccin Mocha palette mapped to ANSI codes
ANSI_COLORS = {
    30: (69, 71, 90),    31: (243, 139, 168),  32: (166, 227, 161),  33: (249, 226, 175),
    34: (137, 180, 250),  35: (203, 166, 247),  36: (148, 226, 213),  37: (205, 214, 244),
    90: (88, 91, 112),    91: (243, 139, 168),  92: (166, 227, 161),  93: (249, 226, 175),
    94: (137, 180, 250),  95: (203, 166, 247),  96: (148, 226, 213),  97: (255, 255, 255),
}

def get_font(size=13):
    for fp in ['/System/Library/Fonts/SFMono-Regular.otf', '/System/Library/Fonts/Menlo.ttc',
               '/System/Library/Fonts/Monaco.ttf']:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def parse_ansi_line(line):
    """Parse a line into segments of (text, color)."""
    segments = []
    color = FG
    bold = False
    i = 0
    buf = ''
    while i < len(line):
        m = re.match(r'\x1b\[([0-9;]*)m', line[i:])
        if m:
            if buf:
                segments.append((buf, color))
                buf = ''
            for code in m.group(1).split(';'):
                if not code:
                    continue
                try:
                    c = int(code)
                    if c == 0:
                        color = FG
                        bold = False
                    elif c == 1:
                        bold = True
                    elif c in ANSI_COLORS:
                        color = ANSI_COLORS[c]
                    elif 30 <= c <= 37 and bold:
                        color = ANSI_COLORS.get(c + 60, ANSI_COLORS.get(c, FG))
                except:
                    pass
            i += m.end()
        else:
            buf += line[i]
            i += 1
    if buf:
        segments.append((buf, color))
    return segments

def clean_lines(text):
    """Remove spinner/fetching lines, keep ANSI codes."""
    lines = []
    for line in text.split('\n'):
        if re.search(r'⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏', line):
            continue
        if 'Fetching' in line and '[' in line:
            continue
        line = re.sub(r'\x1b\[\?25[lh]|\x1b\[\d+[AK]', '', line)
        lines.append(line)
    while lines and not re.sub(r'\x1b\[[0-9;]*m', '', lines[-1]).strip():
        lines.pop()
    while lines and not re.sub(r'\x1b\[[0-9;]*m', '', lines[0]).strip():
        lines.pop(0)
    return lines

def text_to_image_colored(lines, font, padding=20):
    """Render ANSI-colored lines to image, segment by segment."""
    if not lines:
        return None
    
    bbox = font.getbbox('M')
    cw = bbox[2] - bbox[0]
    ch = int((bbox[3] - bbox[1]) * 1.55)
    
    # Parse all lines and find max width
    parsed = [parse_ansi_line(line) for line in lines]
    max_chars = 0
    for segs in parsed:
        line_len = sum(len(t) for t, c in segs)
        max_chars = max(max_chars, line_len)
    
    img_w = max_chars * cw + padding * 2
    img_h = len(parsed) * ch + padding * 2
    
    img = Image.new('RGB', (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)
    
    for row, segs in enumerate(parsed):
        x = padding
        y = padding + row * ch
        for text, color in segs:
            if text:
                draw.text((x, y), text, fill=color, font=font)
                x += len(text) * cw
    
    return img

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

def run_stockbot_single(ticker, cmd='cc', min_days=7, max_days=60):
    """Run stockbot for a single ticker."""
    d = '/Users/huiyuma/Downloads/Projects/StockBot'
    env = os.environ.copy()
    env.update({'COLUMNS': '150', 'FORCE_COLOR': '1', 'TERM': 'xterm-256color'})
    try:
        r = subprocess.run(
            [f'{d}/.venv/bin/python', '-m', 'src.cli.main', cmd, ticker,
             '--min-days', str(min_days), '--max-days', str(max_days), '-s'],
            capture_output=True, text=True, cwd=d, env=env, timeout=90
        )
        return r.stdout + r.stderr
    except:
        return ''

def extract_sections(raw):
    """Extract news and table sections (keeping ANSI codes)."""
    stripped = strip_ansi(raw)
    
    price_m = re.search(r'Current Price: \$([0-9.]+)', stripped)
    price = price_m.group(1) if price_m else '?'
    
    hv_m = re.search(r'HV30: ([0-9.]+%)', stripped)
    hv = hv_m.group(1) if hv_m else '?'
    
    total_m = re.search(r'Total options.*?:\s*(\d+)', stripped)
    total = total_m.group(1) if total_m else '?'
    
    # Find news block in raw (between ╭ and ╯)
    news_m = re.search(r'(╭.*?╯)', raw, re.DOTALL)
    news = news_m.group(1) if news_m else ''
    
    # Find table block in raw (from ┏ to Total options line)
    table_m = re.search(r'((?:(?:Call|Put) Options[^\n]*\n)?┏.*?Total options[^\n]*)', raw, re.DOTALL)
    table = table_m.group(1) if table_m else ''
    
    return {'price': price, 'hv': hv, 'news': news, 'table': table, 'total': total}

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'cc'
    label = 'Covered Calls' if cmd == 'cc' else 'Cash-Secured Puts'
    
    tickers = ['NVDA', 'TSLA', 'META', 'AMZN']
    out_dir = f'/tmp/{cmd}_images'
    os.makedirs(out_dir, exist_ok=True)
    font = get_font(13)
    
    print(f"Fetching {label} data...", file=sys.stderr)
    raw_data = {}
    sections = {}
    for t in tickers:
        raw = run_stockbot_single(t, cmd=cmd)
        if raw.strip():
            raw_data[t] = raw
            sections[t] = extract_sections(raw)
            print(f"  ✓ {t}: ${sections[t]['price']}, {sections[t]['total']} options", file=sys.stderr)
        else:
            print(f"  ✗ {t}: no data", file=sys.stderr)
    
    if not sections:
        print("ERROR: No data", file=sys.stderr)
        sys.exit(1)
    
    # Combined news image
    news_lines_raw = []
    for t in tickers:
        if t not in sections: continue
        s = sections[t]
        news_lines_raw.append(f"\x1b[1;97m  {t}  —  ${s['price']}  |  HV30: {s['hv']}  |  {s['total']} options\x1b[0m")
        news_lines_raw.append('')
        if s['news']:
            news_lines_raw.extend(s['news'].split('\n'))
            news_lines_raw.append('')
    
    if news_lines_raw:
        cleaned = clean_lines('\n'.join(news_lines_raw))
        if cleaned:
            img = text_to_image_colored(cleaned, font)
            if img:
                p = os.path.join(out_dir, 'all_news.png')
                img.save(p, optimize=True)
                print(f"NEWS:{p}")
    
    # Table images
    for t in tickers:
        if t not in sections or not sections[t]['table']:
            continue
        cleaned = clean_lines(sections[t]['table'])
        if cleaned:
            img = text_to_image_colored(cleaned, font)
            if img:
                p = os.path.join(out_dir, f'{t}_table.png')
                img.save(p, optimize=True)
                print(f"TABLE:{t}:{sections[t]['price']}:{sections[t]['total']}:{p}")
    
    print("DONE")

if __name__ == '__main__':
    main()
