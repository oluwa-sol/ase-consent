from ase import web


def test_pages_render_with_theme_toggle_and_cream_default():
    html = web._page("Test", "<p>body</p>", "en", "")
    assert 'id="theme"' in html                      # toggle button present
    assert "prefers-color-scheme" not in html        # cream is the default, not the device setting
    assert ':root[data-theme="dark"]' in html        # dark only when chosen
    assert "localStorage" in html
    assert "http" not in html.split("<footer>")[0].replace("https://github.com", "")  # no external resources


def test_pidgin_labels_exist_for_every_english_label():
    assert set(web.L["en"]) == set(web.L["pcm"])
