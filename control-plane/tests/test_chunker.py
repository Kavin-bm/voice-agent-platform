from app.services.ingestion.chunker import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS, chunk_text
from app.services.ingestion.parsers import parse


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\t") == []


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("hours are nine to seven") == ["hours are nine to seven"]


def test_chunks_overlap_by_the_configured_word_count() -> None:
    words = [f"w{i}" for i in range(CHUNK_SIZE_WORDS + CHUNK_OVERLAP_WORDS)]
    chunks = chunk_text(" ".join(words))
    assert len(chunks) == 2
    first = chunks[0].split()
    second = chunks[1].split()
    assert first[-CHUNK_OVERLAP_WORDS:] == second[:CHUNK_OVERLAP_WORDS]


def test_plain_text_parser_and_unknown_type() -> None:
    assert parse("txt", b"price list") == "price list"
    try:
        parse("mp3", b"nope")
    except ValueError as exc:
        assert "mp3" in str(exc)
    else:
        raise AssertionError("expected ValueError")
