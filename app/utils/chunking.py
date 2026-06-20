"""Text chunking utilities"""


def split_text_into_chunks(text: str, max_words: int = 120) -> list[str]:
    """
    Split text into manageable chunks.

    Strategy:
    1. First split by blank lines (paragraphs)
    2. If a paragraph is too long, split into smaller word-based chunks

    Args:
        text: The text to split
        max_words: Maximum words per chunk

    Returns:
        List of text chunks
    """
    chunks = []

    # Split by blank lines first (paragraphs)
    paragraphs = text.split('\n\n')

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Count words in this paragraph
        words = para.split()

        if len(words) <= max_words:
            # Paragraph is small enough, keep as-is
            chunks.append(para)
        else:
            # Paragraph too long, split into smaller chunks
            current_chunk = []
            current_word_count = 0

            for word in words:
                current_chunk.append(word)
                current_word_count += 1

                if current_word_count >= max_words:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_word_count = 0

            # Add remaining words if any
            if current_chunk:
                chunks.append(' '.join(current_chunk))

    return chunks
