#!/usr/bin/env python3
"""Render StockBot options output as colored PNG images using Pillow. No browser needed."""

import re
import subprocess
import sys
import os

from PIL import Image, ImageDraw, ImageFont

# Catppuccin Mocha colors
COLORS = {
    'bg': (30, 30, 46),
    'fg': (205, 214, 244),
    'black': (69, 71, 90),
    'red': (243, 139, 168),
    'green': (166, 227, 161),
    'yellow': (249, 226, 175),
    'blue': (137, 180, 250),
    'magenta': (203, 166, 247),
    'cyan': (148, 226, 213),
    'white': (205, 214, 244),
    'bright_black': (88, 91, 112),
    'bright_red': (243, 139, 168),
    'bright_green': (166, 227, 161),
    'bright_yellow': (249, 226, 175),
    'bright_blue': (137, 180, 250),
    'bright_magenta': (203, 166, 247),
    'bright_cyan': (148, 226, 213),
    'bright_white': (255, 255, 255),
}

ANSI_TO_COLOR = {
    '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
    '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
    '90': 'bright_black', '91': 'bright_red', '92': 'bright_green',
    '93': 'bright_yellow', '94': 'bright_blue', '95': 'bright_magenta',
    '96': 'bright_cyan', '97': 'bright_white',
}

def strip_spinner_lines(text):
    """Remove spinner/progress lines and cursor control sequences."""
    lines = text.split('\n')
    clean = []
    for line in lines:
        # Skip spinner lines, cursor control, and "Fetching" lines
        if re.search(r'\[(\?25[lh]|\d+A|\d+K)', line):
            continue
        if 'Fetching' in line and ('⠋' in line or '⠙' in line or '⠹' in line or '⠸' in line or
                                    '⠼' in line or '⠴' in line or '⠦' in line or '⠧' in line or
                                    '⠇' in line or '⠏' in line):
            continue
        # Remove any remaining cursor control sequences
        line = re.sub(r'\x1b\[\?25[lh]', '', line)
        line = re.sub(r'\x1b\[\d+A', '', line)
        line = re.sub(r'\x1b\[\d+K', '', line)
        if line.strip() or not clean or (clean and clean[-1].strip()):
            clean.append(line)
    return '\n'.join(clean)

def parse_ansi(text):
    """Parse ANSI text into list of (text, color) segments per line."""
    lines = text.split('\n')
    result = []
    for line in lines:
        segments = []
        current_color = 'fg'
        bold = False
        pos = 0
        while pos < len(line):
            # Match ANSI escape sequence
            m = re.match(r'\x1b\[([0-9;]*)m', line[pos:])
            if m:
                codes = m.group(1).split(';')
                for code in codes:
                    if code == '0' or code == '':
                        current_color = 'fg'
                        bold = False
                    elif code == '1':
                        bold = True
                    elif code in ANSI_TO_COLOR:
                        c = ANSI_TO_COLOR[code]
                        current_color = c
                pos += m.end()
            else:
                segments.append((line[pos], current_color))
                pos += 1
        result.append(segments)
    return result

def render_to_image(parsed_lines, padding=24):
    """Render parsed ANSI lines to a PIL Image."""
    # Try to use a monospace font
    font_size = 14
    font = None
    font_paths = [
        '/System/Library/Fonts/SFMono-Regular.otf',
        '/System/Library/Fonts/Menlo.ttc',
        '/System/Library/Fonts/Monaco.ttf',
        '/Library/Fonts/JetBrainsMono-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()

    # Measure character size
    bbox = font.getbbox('M')
    char_w = bbox[2] - bbox[0]
    char_h = int((bbox[3] - bbox[1]) * 1.5)

    # Calculate image size
    max_cols = max((len(segs) for segs in parsed_lines), default=0)
    img_w = max_cols * char_w + padding * 2
    img_h = len(parsed_lines) * char_h + padding * 2

    img = Image.new('RGB', (img_w, img_h), COLORS['bg'])
    draw = ImageDraw.Draw(img)

    for row, segments in enumerate(parsed_lines):
        x = padding
        y = padding + row * char_h
        for char, color in segments:
            draw.text((x, y), char, fill=COLORS.get(color, COLORS['fg']), font=font)
            x += char_w

    return img

def split_by_ticker(raw_text, tickers):
    """Split raw output into news + table sections per ticker."""
    sections = {}
    # Split by ticker delimiter
    parts = re.split(r'={60}\n(\w+)\n={60}', raw_text)
    
    # First part is header (skip)
    i = 1
    while i < len(parts) - 1:
        ticker = parts[i].strip()
        content = parts[i + 1]
        if ticker in tickers:
            # Split into news and table
            news_match = re.search(r'(╭.*?╰[─┘]+╯)', content, re.DOTALL)
            # Find the price line
            price_match = re.search(r'Current Price: \$([0-9.]+)', content)
            price = price_match.group(1) if price_match else '?'
            
            # Find table (starts with ┏ or the Call Options header)
            table_match = re.search(r'((?:Call Options.*\n)?┏.*)', content, re.DOTALL)
            
            news = news_match.group(1) if news_match else ''
            table = table_match.group(1) if table_match else ''
            
            # Count options
            total_match = re.search(r'Total options.*?:\s*(\d+)', content)
            total = total_match.group(1) if total_match else '?'
            
            sections[ticker] = {
                'news': news,
                'table': table,
                'price': price,
                'total': total,
                'raw': content,
            }
        i += 2
    return sections

def main():
    tickers = ['AMZN', 'META', 'NVDA', 'TSLA']
    stockbot_dir = '/Users/huiyuma/Downloads/Projects/StockBot'
    output_dir = '/tmp/options_images'
    os.makedirs(output_dir, exist_ok=True)
    
    # Run StockBot
    print("Running StockBot...")
    env = os.environ.copy()
    env['COLUMNS'] = '150'
    env['FORCE_COLOR'] = '1'
    env['TERM'] = 'xterm-256color'
    
    result = subprocess.run(
        [f'{stockbot_dir}/.venv/bin/python', '-m', 'src.cli.main', 'options'] + tickers +
        ['--min-days', '7', '--max-days', '60', '-s'],
        capture_output=True, text=True, cwd=stockbot_dir, env=env, timeout=120
    )
    
    raw = result.stdout + result.stderr
    if not raw.strip():
        print("ERROR: No output from StockBot")
        sys.exit(1)
    
    # Clean up spinner lines
    cleaned = strip_spinner_lines(raw)
    
    # Split by ticker
    sections = split_by_ticker(cleaned, tickers)
    
    if not sections:
        print("ERROR: Could not parse ticker sections")
        print("Raw output preview:", cleaned[:500])
        sys.exit(1)
    
    # Render combined news image
    news_parts = []
    for ticker in tickers:
        if ticker in sections and sections[ticker]['news']:
            price_line = f"  {ticker}  —  ${sections[ticker]['price']}  |  {sections[ticker]['total']} options"
            news_parts.append(price_line)
            news_parts.append(sections[ticker]['news'])
            news_parts.append('')
    
    if news_parts:
        news_text = '\n'.join(news_parts)
        news_cleaned = strip_spinner_lines(news_text)
        # Strip ANSI for news (it's mostly box-drawing, less color)
        news_parsed = parse_ansi(news_cleaned)
        news_img = render_to_image(news_parsed)
        news_path = os.path.join(output_dir, 'all_news.png')
        news_img.save(news_path)
        print(f"NEWS:{news_path}")
    
    # Render each ticker's table
    for ticker in tickers:
        if ticker not in sections:
            print(f"SKIP:{ticker} (no data)")
            continue
        
        s = sections[ticker]
        table_text = s['table']
        if not table_text.strip():
            print(f"SKIP:{ticker} (no table)")
            continue
        
        table_cleaned = strip_spinner_lines(table_text)
        # Remove the guide at the end (after Total options line)
        guide_idx = table_cleaned.find('💡 IV/HV30')
        if guide_idx > 0:
            table_cleaned = table_cleaned[:guide_idx].rstrip()
        
        table_parsed = parse_ansi(table_cleaned)
        table_img = render_to_image(table_parsed)
        table_path = os.path.join(output_dir, f'{ticker}_table.png')
        table_img.save(table_path)
        print(f"TABLE:{ticker}:{s['price']}:{s['total']}:{table_path}")
    
    print("DONE")

if __name__ == '__main__':
    main()
