CHUNK_SIZE_WORDS = 220
CHUNK_OVERLAP_WORDS = 40


def chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    step = CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + CHUNK_SIZE_WORDS])
        if chunk.strip():
            chunks.append(chunk)
        if start + CHUNK_SIZE_WORDS >= len(words):
            break
    return chunks
