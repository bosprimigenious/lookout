"""Display vocabulary, independent of stored facts and query identities."""
import re
import tomllib
from collections import Counter
from pathlib import Path

_CONFIG = tomllib.loads(Path(__file__).with_suffix('.toml').read_text())
CATALOG = _CONFIG['labels']
STYLES = _CONFIG['styles']
_ICON_USES = Counter(item['icon'] for item in CATALOG.values() if item.get('icon'))


def caption(value):
    return CATALOG.get(value, {}).get('text', value)


def appearance(value):
    return 'label:' + value if 'style' in CATALOG.get(value, {}) else None


def priority(value):
    key = (value or '').removeprefix('label:')
    style = CATALOG.get(key, {}).get('style')
    return STYLES.get(style, {}).get('order', 3)


def palettes():
    return {'label:' + key: {field: STYLES[item['style']][field]
                            for field in ('background', 'foreground')}
            for key, item in CATALOG.items() if 'style' in item}


def icon(value):
    return CATALOG.get(value, {}).get("icon")


def icon_only(value):
    return CATALOG.get(value, {}).get("icon_only", _ICON_USES[icon(value)] == 1)


def tag_palette(background):
    """Darken declared colors until white text has at least 4.5:1 contrast."""
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', background):
        return None
    rgb = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    for _ in range(256):
        linear = [v / 255 / 12.92 if v / 255 <= .04045 else ((v / 255 + .055) / 1.055) ** 2.4 for v in rgb]
        luminance = sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))
        if 1.05 / (luminance + .05) >= 4.5:
            break
        rgb = [max(0, value - 1) for value in rgb]
    return {'background': '#' + ''.join(f'{value:02x}' for value in rgb), 'foreground': '#ffffff'}
