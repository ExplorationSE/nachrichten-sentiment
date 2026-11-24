from nachrichten_sentiment.gkg import extract_page_title, parse_gkg_line


def _line(*, collection: str = "1", orgs: str = "NVIDIA", extras: str = "", url: str = "https://example.com/n"):
    cols = [""] * 27
    cols[0] = "20150218230000-GKG-1"
    cols[1] = "20150218230000"
    cols[2] = collection
    cols[3] = "example.com"
    cols[4] = url
    cols[13] = orgs
    cols[14] = "NVIDIA,100"
    cols[26] = extras
    return "\t".join(cols)


def test_extract_page_title_unescapes_entities():
    extras = "<PAGE_TITLE>NVIDIA &#x26; earnings &#8211; rise</PAGE_TITLE>"
    assert extract_page_title(extras) == "NVIDIA & earnings – rise"
    assert extract_page_title("no title here") is None


def test_parse_web_row_and_skip_non_web_and_header():
    record = parse_gkg_line(_line(extras="<PAGE_TITLE>NVIDIA beats</PAGE_TITLE>"), "20150218230000")
    assert record is not None
    assert record.gkg_record_id == "20150218230000-GKG-1"
    assert record.source_collection_id == 1
    assert record.url == "https://example.com/n"
    assert record.organizations == "NVIDIA"
    assert record.page_title == "NVIDIA beats"
    assert parse_gkg_line(_line(collection="2"), "20150218230000") is None
    header = "GKGRECORDID\tDATE\tSourceCollectionIdentifier\t" + "\t".join(["x"] * 24)
    assert parse_gkg_line(header, "20150218230000") is None
    assert parse_gkg_line("too\tshort", "20150218230000") is None
