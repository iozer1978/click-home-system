"""One-off: convert extracted HTML to Django templates with {% static %}."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def convert_page(name: str, css_name: str) -> str:
    p = ROOT / "_landing_extract" / name
    text = p.read_text(encoding="utf-8")
    out = "{% load static %}\n" + text
    out = out.replace(
        'href="static/css/site.css"',
        'href="{% static \'en_landing/css/site.css\' %}"',
    )
    out = out.replace(
        f'href="static/css/{css_name}"',
        f'href="{{% static \'en_landing/css/{css_name}\' %}}"',
    )
    def src_repl(m: re.Match) -> str:
        return 'src="{% static \'en_landing/img/' + m.group(1) + '\' %}"'

    out = re.sub(r'src="static/img/([^"]+)"', src_repl, out)
    # url() without quotes around value — {% static %} resolves to a path safe for CSS
    out = re.sub(
        r"background:url\('static/img/([^']+)'\)",
        r"background:url({% static 'en_landing/img/\1' %})",
        out,
    )
    out = out.replace(
        'src="static/js/qr.js"',
        'src="{% static \'en_landing/js/qr.js\' %}"',
    )
    return out


def main():
    dest = ROOT / "proposals" / "templates" / "en"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "v1_architectural.html").write_text(
        convert_page("v1_architectural.html", "v1.css"), encoding="utf-8"
    )
    (dest / "v2_industrial.html").write_text(
        convert_page("v2_industrial.html", "v2.css"), encoding="utf-8"
    )
    (dest / "v3_china.html").write_text(
        convert_page("v3_china.html", "v3.css"), encoding="utf-8"
    )
    print("Wrote v1, v2, v3 templates")


if __name__ == "__main__":
    main()
