"""Build small PDFs on the fly for tests (no binary fixtures in the repo)."""

import pymupdf


def make_pdf(
    pages: list[str],
    *,
    header: str | None = None,
    numbered: bool = False,
    password: str | None = None,
) -> bytes:
    document = pymupdf.open()
    for number, body in enumerate(pages, start=1):
        page = document.new_page()  # 612 x 792 pt
        if header:
            page.insert_text((50, 40), header, fontsize=9)
        overflow = page.insert_textbox(pymupdf.Rect(50, 70, 560, 740), body, fontsize=10)
        assert overflow >= 0, "test text too long for one page"
        if numbered:
            page.insert_text((300, 775), str(number), fontsize=9)

    if password:
        return document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password
        )
    return document.tobytes()
