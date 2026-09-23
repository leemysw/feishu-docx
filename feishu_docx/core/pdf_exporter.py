"""
[INPUT]: markdown string or path, optional CSS path
[OUTPUT]: PDF file via WeasyPrint
[POS]: core module, markdown-to-PDF bridge
"""

import html
import re
from datetime import date
from pathlib import Path

import mistune
from mistune.plugins.math import math as math_plugin
from mistune.plugins.table import table as table_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer


class _HighlightRenderer(mistune.HTMLRenderer):
    """Renderer that applies Pygments syntax highlighting to code blocks.

    `style` is the Pygments style name, or None for the default.
    """

    def __init__(self, style: str | None = None) -> None:
        super().__init__()
        self._fmt = HtmlFormatter(nowrap=True, style=style) if style else HtmlFormatter(nowrap=True)

    def inline_html(self, html: str) -> str:
        # 仅允许无属性的换行标签，其他原始 HTML 仍由 Mistune 转义。
        if html.lower() in ("<br>", "<br/>", "<br />"):
            return "<br>"
        return super().inline_html(html)

    def block_code(self, code: str, info: str | None = None) -> str:
        lang = info.strip() if info else ""
        if not lang:
            return super().block_code(code, info)
        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            lexer = guess_lexer(code)
        highlighted = highlight(code, lexer, self._fmt)
        return f'<pre class="highlight"><code class="language-{lang}">{highlighted}</code></pre>\n'


def _make_md_renderer(syntax_style: str | None = None):
    return mistune.create_markdown(
        renderer=_HighlightRenderer(style=syntax_style),
        plugins=["strikethrough", "speedup", table_plugin, math_plugin],
    )


def _make_pygments_css(syntax_style: str | None = None) -> str:
    fmt = HtmlFormatter(style=syntax_style) if syntax_style else HtmlFormatter()
    return fmt.get_style_defs(".highlight")


# ponytail: mistune rejects spaces in image src per CommonMark; wrap in <>
_IMG_SRC_RE = re.compile(r"!\[([^]]*)]\(([^)]+)\)")


def _prepare_md(md: str) -> str:
    def _fix(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if " " in src and not src.startswith(("<", "http://", "https://", "data:")):
            return f"![{alt}](<{src}>)"
        return m.group(0)

    return _IMG_SRC_RE.sub(_fix, md)


def _build_cover_html(title: str | None, logo_path: Path | None = None) -> str:
    if not title:
        return ""

    today = date.today().isoformat()
    logo_img = ""
    if logo_path:
        logo_src = logo_path.resolve().as_uri()
        logo_img = f'<img class="cover-logo" src="{logo_src}" alt="logo">\n'

    escaped_title = html.escape(title)
    return (
        f'<div class="cover-page">\n'
        f"{logo_img}"
        f"<h1>{escaped_title}</h1>\n"
        f'<div class="rule"></div>\n'
        f'<div class="meta">{today}</div>\n'
        f"</div>\n"
    )


DEFAULT_CSS = """
@page { size: A4; margin: 2.5cm 2cm; @bottom-center { content: counter(page); font-size: 9pt; color: #999; } }
@page cover { margin: 0; @bottom-center { content: none; } }

body { font-family: "Noto Sans", "Helvetica Neue", Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #222; max-width: 100%; }

.cover-page { page: cover; page-break-after: always; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; text-align: center; background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); color: #fff; padding: 3cm; }
.cover-page h1 { font-size: 2.4em; font-weight: 700; border: none; margin-bottom: 0.5em; line-height: 1.3; color: #fff; }
.cover-page .meta { font-size: 1.05em; opacity: 0.75; margin-top: 2em; }
.cover-page .rule { width: 80px; height: 3px; background: rgba(255,255,255,0.5); margin: 1.5em auto; }

h1 { font-size: 1.8em; border-bottom: 2px solid #2563eb; padding-bottom: 0.3em; }
h2 { font-size: 1.4em; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.2em; }
h3 { font-size: 1.15em; }
code { padding: 0.15em 0.3em; border-radius: 3px; font-size: 0.9em; }
pre { border: 1px solid #e5e7eb; padding: 0.8em; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; }
pre code { padding: 0; white-space: pre-wrap; word-wrap: break-word; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #d1d5db; padding: 0.5em 0.75em; text-align: left; }
th { background: #f3f4f6; font-weight: 600; }
img { max-width: 100%; height: auto; }
blockquote { border-left: 3px solid #2563eb; margin-left: 0; padding-left: 1em; color: #555; }
"""


def md_to_pdf(
    md_content: str,
    output_path: Path,
    css_path: Path | None = None,
    title: str | None = None,
    logo_path: Path | None = None,
    debug: bool = False,
    syntax_style: str | None = None,
) -> Path:
    """Convert markdown string to PDF using WeasyPrint.

    Args:
        md_content: Markdown source string.
        output_path: Destination .pdf path.
        css_path: Optional path to a CSS file for branding; defaults to built-in styles.
        title: Optional document title for the cover page.
        logo_path: Optional path to an image (SVG/PNG) for the cover page header.
        debug: If True, also write the intermediate HTML file alongside the PDF.
        syntax_style: Optional Pygments style name (e.g. "solarized-light"). Defaults to Pygments default.

    Returns:
        The output_path that was written.
    """
    # ponytail: lazy import so the CLI works without weasyprint installed
    from weasyprint import HTML  # type: ignore[import-untyped]

    md_renderer = _make_md_renderer(syntax_style)
    pygments_css = _make_pygments_css(syntax_style)

    html_body = md_renderer(_prepare_md(md_content))
    extra_css = css_path.read_text(encoding="utf-8") if css_path else ""
    css_text = DEFAULT_CSS + "\n" + pygments_css + "\n" + extra_css

    title_html = _build_cover_html(title, logo_path)

    html = (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        f"<style>{css_text}</style>\n"
        "</head><body>\n"
        f"{title_html}"
        f"{html_body}\n"
        "</body></html>"
    )

    if debug:
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")

    # ponytail: as_uri() strips trailing /; add it so relative paths resolve correctly
    base_url = output_path.parent.resolve().as_uri() + "/"
    HTML(string=html, base_url=base_url).write_pdf(output_path)
    return output_path
