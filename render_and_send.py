#!/usr/bin/env python3
"""
Render StockBot ANSI output to PNG using Pillow multiline text.
Strips ANSI color but keeps layout. Fast rendering.
"""
import re, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont

BG = (30, 30, 46)
FG = (205, 214, 244)

def get_font(size=13):
    for fp in ['/System/Library/Fonts/SFMono-Regular.otf', '/System/Library/Fonts/Menlo.ttc',
               '/System/Library/Fonts/Monaco.ttf']:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def clean_ansi(text):
    """Strip ANSI codes and spinner lines."""
    lines = []
    for line in text.split('\n'):
        if re.search(r'⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏', line):
            continue
        if 'Fetching' in line and '[' in line:
            continue
        # Strip all ANSI escape sequences
        line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
        line = re.sub(r'\x1b\[\?25[lh]', '', line)
        lines.append(line)
    # Trim
    while lines and not lines[-1].strip(): lines.pop()
    while lines and not lines[0].strip(): lines.pop(0)
    return '\n'.join(lines)

def text_to_image(text, font, padding=20):
    """Render plain text to image using multiline draw (fast)."""
    lines = text.split('\n')
    if not lines:
        return None
    
    bbox = font.getbbox('M')
    cw = bbox[2] - bbox[0]
    ch = int((bbox[3] - bbox[1]) * 1.55)
    
    max_chars = max(len(l) for l in lines)
    img_w = max_chars * cw + padding * 2
    img_h = len(lines) * ch + padding * 2
    
    img = Image.new('RGB', (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)
    
    for i, line in enumerate(lines):
        draw.text((padding, padding + i * ch), line, fill=FG, font=font)
    
    return img

def run_stockbot_single(ticker, min_days=7, max_days=60):
    """Run stockbot for a single ticker."""
    d = '/Users/huiyuma/Downloads/Projects/StockBot'
    env = os.environ.copy()
    env.update({'COLUMNS': '150', 'FORCE_COLOR': '1', 'TERM': 'xterm-256color'})
    try:
        r = subprocess.run(
            [f'{d}/.venv/bin/python', '-m', 'src.cli.main', 'options', ticker,
             '--min-days', str(min_days), '--max-days', str(max_days), '-s'],
            capture_output=True, text=True, cwd=d, env=env, timeout=90
        )
        return r.stdout + r.stderr
    except:
        return ''

def extract_info(raw):
    """Extract price, hv, news, table from raw output."""
    stripped = clean_ansi(raw)
    
    price_m = re.search(r'Current Price: \$([0-9.]+)', stripped)
    price = price_m.group(1) if price_m else '?'
    
    hv_m = re.search(r'HV30: ([0-9.]+%)', stripped)
    hv = hv_m.group(1) if hv_m else '?'
    
    # News: between ╭ and ╯
    news_m = re.search(r'(╭.*?╯)', stripped, re.DOTALL)
    news = news_m.group(1) if news_m else ''
    
    # Table: from ┏ or "Call Options" to Total
    table_m = re.search(r'((?:Call Options[^\n]*\n)?┏.*?Total options[^\n]*)', stripped, re.DOTALL)
    table = table_m.group(1) if table_m else ''
    
    total_m = re.search(r'Total options.*?:\s*(\d+)', stripped)
    total = total_m.group(1) if total_m else '?'
    
    return {'price': price, 'hv': hv, 'news': news, 'table': table, 'total': total}

def main():
    tickers = ['NVDA', 'TSLA', 'META', 'AMZN']
    out_dir = '/tmp/options_images'
    os.makedirs(out_dir, exist_ok=True)
    font = get_font(13)
    
    print("Fetching options data...", file=sys.stderr)
    data = {}
    for t in tickers:
        raw = run_stockbot_single(t)
        if raw.strip():
            data[t] = extract_info(raw)
            print(f"  ✓ {t}: ${data[t]['price']}, {data[t]['total']} options", file=sys.stderr)
        else:
            print(f"  ✗ {t}: no data", file=sys.stderr)
    
    if not data:
        print("ERROR: No data", file=sys.stderr)
        sys.exit(1)
    
    # Combined news image
    news_text = ''
    for t in tickers:
        if t not in data: continue
        d = data[t]
        news_text += f"\n  {t}  —  ${d['price']}  |  HV30: {d['hv']}  |  {d['total']} options\n\n"
        if d['news']:
            news_text += d['news'] + '\n'
    
    if news_text.strip():
        img = text_to_image(news_text.strip(), font)
        if img:
            p = os.path.join(out_dir, 'all_news.png')
            img.save(p, optimize=True)
            print(f"NEWS:{p}")
    
    # Table images
    for t in tickers:
        if t not in data or not data[t]['table']:
            continue
        img = text_to_image(data[t]['table'], font)
        if img:
            p = os.path.join(out_dir, f'{t}_table.png')
            img.save(p, optimize=True)
            print(f"TABLE:{t}:{data[t]['price']}:{data[t]['total']}:{p}")
    
    print("DONE")

if __name__ == '__main__':
    main()
