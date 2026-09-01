"""Local, citation-aware retrieval over the approved career-guidance PDFs."""

import json
import re
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PDF_DIR = PROJECT_ROOT / "knowledge" / "raw_pdfs"
PROCESSED_DIR = PROJECT_ROOT / "knowledge" / "processed"
CORPUS_FILE = PROCESSED_DIR / "corpus.json"
EMBEDDINGS_FILE = PROCESSED_DIR / "embeddings.npy"
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

RAG_SCORE_THRESHOLD = 0.75

MIN_RAG_QUERY_WORDS = 3

QUESTION_WORDS = {
    "what", "why", "how", "when", "where", "which", "who",
    "can", "could", "would", "should", "is", "are", "do",
    "does", "did", "will", "may", "tell", "explain", "describe",
    "show", "give"
}

_chunks = None
_embedding_model = None
_embeddings = None

# JoSAA's FAQ has numbered questions followed by "Answer:".  Treating each
# pair as one record preserves the full official answer during retrieval.
FAQ_PATTERN = re.compile(
    r"(?is)(?P<question>\b\d{1,3}\.\s+.*?)(?:\s+Answer\s*:\s*)(?P<answer>.*?)(?=(?:\s+\d{1,3}\.\s+.*?\s+Answer\s*:)|\Z)"
)


def _normalise(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _split_into_chunks(text, words_per_chunk=170, overlap=35):
    words = text.split()
    if not words:
        return []
    step = words_per_chunk - overlap
    return [" ".join(words[start : start + words_per_chunk]) for start in range(0, len(words), step)]


def _faq_chunks(text, source, page_number):
    """Extract complete numbered FAQ question-and-answer pairs from one page."""
    records = []
    for match in FAQ_PATTERN.finditer(_normalise(text)):
        question = _normalise(match.group("question"))
        answer = _normalise(match.group("answer"))
        if question and answer:
            records.append(
                {
                    "text": f"{question} Answer: {answer}",
                    "question": question,
                    "answer": answer,
                    "kind": "faq",
                    "source": source,
                    "page": page_number,
                }
            )
    return records


def _pdf_reader(pdf_path):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError as error:
            raise RuntimeError("Install pypdf with: pip install pypdf") from error
    return PdfReader(str(pdf_path))

def create_embeddings(chunks):
    """Generate and save embeddings for all knowledge-base chunks."""
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    texts = [chunk["text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    np.save(EMBEDDINGS_FILE, embeddings)

    print(f"Saved {len(embeddings)} embeddings.")
    print(f"Embedding shape: {embeddings.shape}")
    print(f"Saved to: {EMBEDDINGS_FILE}")

    return embeddings

def build_corpus():
    """Extract page-aware chunks from every approved PDF and save them locally."""
    pdf_files = sorted(RAW_PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"No PDFs found in {RAW_PDF_DIR}")

    chunks = []
    for pdf_path in pdf_files:
        reader = _pdf_reader(pdf_path)
        is_faq = "faq" in pdf_path.stem.lower()
        for page_number, page in enumerate(reader.pages, start=1):
            text = _normalise(page.extract_text())
            faq_records = _faq_chunks(text, pdf_path.name, page_number) if is_faq else []
            if faq_records:
                chunks.extend(faq_records)
                continue
            for chunk in _split_into_chunks(text):
                chunks.append({"text": chunk, "source": pdf_path.name, "page": page_number})

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    CORPUS_FILE.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    create_embeddings(chunks)

    return chunks


def _load_index():
    global _chunks, _embedding_model, _embeddings

    if _chunks is not None:
        return

    if not CORPUS_FILE.exists():
        raise FileNotFoundError(
            f"Knowledge corpus not found: {CORPUS_FILE}"
        )

    if not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(
            f"Embeddings file not found: {EMBEDDINGS_FILE}"
        )

    _chunks = json.loads(
        CORPUS_FILE.read_text(encoding="utf-8")
    )

    _embeddings = np.load(EMBEDDINGS_FILE)

    if len(_chunks) != len(_embeddings):
        raise ValueError(
            f"Corpus/embedding mismatch: "
            f"{len(_chunks)} chunks vs {len(_embeddings)} embeddings"
        )

    _embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

def _should_try_rag(question):
    """Allow RAG for genuine information requests, not topic-only inputs."""
    text = _normalise(question)

    if not text:
        return False

    words = re.findall(r"[A-Za-z0-9]+", text.lower())

    # Short/topic-only queries go to the intent model.
    if len(words) < MIN_RAG_QUERY_WORDS:
        return False

    # Explicit questions.
    if "?" in text:
        return True

    # Information-seeking words.
    if any(word in QUESTION_WORDS for word in words):
        return True

    # Common requests without a question mark.
    request_phrases = (
        "tell me about",
        "tell me something about",
        "information about",
        "details about",
        "show me",
        "give me",
        "list of",
        "explain",
        "describe",
    )

    lowered = text.lower()

    return any(
        phrase in lowered
        for phrase in request_phrases
    )


def search(question, limit=2):
    """Return only high-confidence, source-cited semantic matches."""

    if not _should_try_rag(question):
        return []

    _load_index()

    if not _chunks or _embeddings is None or _embedding_model is None:
        return []

    query_embedding = _embedding_model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    scores = np.dot(_embeddings, query_embedding)

    ranked = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True
    )

    return [
        {**_chunks[index], "score": float(score)}
        for index, score in ranked[:limit]
        if score >= RAG_SCORE_THRESHOLD
    ]

def answer(question):
    """Format extractive source passages, or return None for TensorFlow fallback."""
    try:
        matches = search(question)
    except (OSError, RuntimeError, ValueError):
        return None
    if not matches:
        return None

    excerpts, citations = [], []
    for match in matches:
        if match.get("kind") == "faq":
            excerpt = f"Question: {match['question']}\n\nAnswer: {match['answer']}"
        else:
            excerpt = match["text"][:700].rsplit(" ", 1)[0] + "…"
        excerpts.append(f"• {excerpt}")
        citations.append(f"{match['source']}, page {match['page']}")
    return "According to the approved guidance documents:\n\n" + "\n\n".join(excerpts) + "\n\nSources: " + "; ".join(citations)
