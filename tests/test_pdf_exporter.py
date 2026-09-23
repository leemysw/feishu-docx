from types import SimpleNamespace

import pytest

from feishu_docx.core.parsers.document import DocumentParser
from feishu_docx.core.pdf_exporter import _make_md_renderer
from feishu_docx.utils.render_table import convert_to_markdown, render_table_markdown


def test_table_line_breaks_preserve_html_escaping():
    content = 'FIRST LINE\nSECOND LINE <img src="x"> & text'
    for markdown in (
        render_table_markdown([[("Value", 1, 1)], [(content, 1, 1)]], 2, 1),
        convert_to_markdown([["Value"], [content]]),
    ):
        html = _make_md_renderer()(markdown)
        assert 'FIRST LINE<br>SECOND LINE &lt;img src=&quot;x&quot;&gt; &amp; text' in html


def test_only_plain_break_tags_are_allowed_outside_code():
    render = _make_md_renderer()
    assert render("a<br>b<BR/>c<br />d") == "<p>a<br>b<br>c<br>d</p>\n"
    assert '&lt;br onclick=&quot;bad()&quot;&gt;' in render('a<br onclick="bad()">b')
    assert "&lt;script&gt;bad()&lt;/script&gt;" in render("<script>bad()</script>")
    assert "<code>&lt;br&gt;</code>" in render("`<br>`")
    assert "<pre><code>&lt;br&gt;\n</code></pre>" in render("```\n<br>\n```")


@pytest.mark.parametrize(
    ("styles", "expected"),
    [
        ({"bold": True}, "<strong>gpu-operator</strong>"),
        ({"inline_code": True}, "<code>gpu-operator</code>"),
        ({"bold": True, "inline_code": True}, "<strong><code>gpu-operator</code></strong>"),
        (
            {"bold": True, "italic": True, "strikethrough": True, "inline_code": True},
            "<del><em><strong><code>gpu-operator</code></strong></em></del>",
        ),
    ],
)
def test_text_styles_wrap_inline_code(styles, expected):
    style = dict(bold=False, italic=False, strikethrough=False, inline_code=False, underline=False, link=None)
    style.update(styles)
    payload = SimpleNamespace(elements=[SimpleNamespace(text_run=SimpleNamespace(
        content="gpu-operator", text_element_style=SimpleNamespace(**style),
    ))])
    parser = DocumentParser.__new__(DocumentParser)
    markdown = parser._render_text_payload(payload)
    assert _make_md_renderer()(markdown) == f"<p>{expected}</p>\n"
