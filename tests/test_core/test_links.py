"""
The links inside a description or a note
"""

from dooit.utils.links import find_links, first_link, link_at, link_label


def test_a_plain_url_is_found():
    (link,) = find_links("see https://example.com for more")

    assert link.url == "https://example.com"
    assert link.start == 4
    assert link.end == 4 + len("https://example.com")


def test_www_stands_in_for_a_scheme():
    (link,) = find_links("go to www.example.com now")

    # A browser needs the scheme even where a reader does not
    assert link.url == "https://www.example.com"


def test_every_link_in_order():
    links = find_links("https://a.com then https://b.com")
    assert [link.url for link in links] == ["https://a.com", "https://b.com"]


def test_no_links():
    assert find_links("nothing to open here") == []
    assert first_link("nothing") is None


def test_sentence_punctuation_is_not_part_of_the_link():
    (link,) = find_links("read https://example.com/page.")
    assert link.url == "https://example.com/page"

    (link,) = find_links("(see https://example.com/page)")
    assert link.url == "https://example.com/page"


def test_balanced_brackets_stay_in_the_link():
    (link,) = find_links("https://en.wikipedia.org/wiki/Dooit_(app)")
    assert link.url == "https://en.wikipedia.org/wiki/Dooit_(app)"


def test_a_bare_scheme_is_not_a_link():
    assert find_links("https:// is how they start") == []
    assert find_links("www. is not an address") == []


def test_first_link():
    link = first_link("https://a.com and https://b.com")
    assert link is not None
    assert link.url == "https://a.com"


def test_link_at_reads_the_character_under_the_cursor():
    text = "see https://example.com now"
    link = find_links(text)[0]

    assert link_at(text, link.start) == link
    assert link_at(text, link.end - 1) == link

    # One past the last character is the space after the link
    assert link_at(text, link.end) is None
    assert link_at(text, 0) is None


def test_link_label_shortens_and_escapes():
    assert link_label("https://a.com") == "https://a.com"

    long_url = "https://example.com/" + "x" * 100
    label = link_label(long_url)
    assert len(label) == 50
    assert label.endswith("…")

    # Markup-like brackets escaped, so a URL is not read as rich markup
    assert r"\[bold]" in link_label("https://a.com/[bold]x")
