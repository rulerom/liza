"""Render the static sharing card. Requires Pillow; not part of the site build.

python3 tools/render_social_card.py [--font PATH] [--bold-font PATH]
Commit the resulting PNG. Change its filename and mkdocs.yml when replacing
an already published card so link crawlers can fetch a new image URL.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def default_font(bold=False):
    candidates = [
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    return next((path for path in candidates if Path(path).exists()), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', default=default_font())
    parser.add_argument('--bold-font', default=default_font(True))
    args = parser.parse_args()
    if not args.font or not args.bold_font:
        parser.error('provide --font and --bold-font with Cyrillic support')

    scale = 2
    image = Image.new('RGB', (1200 * scale, 630 * scale), '#101629')
    draw = ImageDraw.Draw(image)

    def rect(box, fill):
        draw.rectangle(tuple(int(x * scale) for x in box), fill=fill)

    def text(x, y, value, size, color, bold=False):
        font = ImageFont.truetype(args.bold_font if bold else args.font, size * scale)
        draw.text((x * scale, y * scale), value, font=font, fill=color, anchor='lt')

    rect((0, 0, 1200, 9), '#58ddc2')
    rect((1025, 9, 1200, 630), '#171f38')
    rect((1050, 70, 1060, 490), '#303e68')
    rect((1090, 120, 1100, 490), '#4a5ba0')
    rect((1130, 170, 1140, 490), '#58ddc2')

    text(78, 64, 'ЯЗЫК СИСТЕМНОГО ПРОГРАММИРОВАНИЯ', 22, '#a7b2d3', True)
    text(70, 139, 'Liza', 160, '#f3f6ff', True)
    rect((80, 329, 166, 335), '#58ddc2')
    text(78, 376, 'Переносимые вычисления.', 40, '#f3f6ff')
    text(78, 434, 'Предсказуемое поведение.', 40, '#f3f6ff')
    text(80, 555, 'liza.rulerom.com', 25, '#58ddc2')

    output = Path(__file__).resolve().parents[1] / 'docs/assets/images/liza-social-v1.png'
    output.parent.mkdir(parents=True, exist_ok=True)
    image.resize((1200, 630), Image.Resampling.LANCZOS).save(output, optimize=True)
    print(output)


if __name__ == '__main__':
    main()
