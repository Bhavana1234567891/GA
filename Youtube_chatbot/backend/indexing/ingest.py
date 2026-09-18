"""
Document Ingestion: fetch YouTube transcript and chunk into 30-second
timestamped segments with full metadata.
"""

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_core.documents import Document


def _seconds_to_mmss(seconds: float) -> str:
    """Convert seconds to MM:SS display format."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> list[dict]:
    """
    Fetch captions for a YouTube video using the v1.2+ API (instance-based).
    Returns a list of dicts: [{text, start, duration}, ...].
    """
    languages = languages or ["en"]
    api = YouTubeTranscriptApi()

    try:
        transcript = api.fetch(video_id, languages=languages)
        # Convert FetchedTranscriptSnippet objects to plain dicts
        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in transcript
        ]
    except Exception:
        pass

    # Fallback: try any auto-generated transcript
    try:
        transcript_list = api.list(video_id)
        generated = transcript_list.find_generated_transcript(["en"])
        transcript = generated.fetch()
        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in transcript
        ]
    except TranscriptsDisabled:
        raise ValueError(f"Transcripts are disabled for video {video_id}")
    except Exception as e:
        raise ValueError(f"Could not fetch transcript for video {video_id}: {e}")


def chunk_by_time(
    transcript_list: list[dict],
    video_id: str,
    title: str = "",
    language: str = "en",
    window_sec: float = 30.0,
) -> list[Document]:
    """
    Group captions into ~30-second windows. Each chunk becomes a Document
    with metadata: video_id, t_start, t_end, t_start_display, t_end_display,
    title, language.
    """
    if not transcript_list:
        return []

    chunks: list[Document] = []
    current_captions: list[dict] = []
    window_start = transcript_list[0]["start"]

    for cap in transcript_list:
        if cap["start"] - window_start >= window_sec and current_captions:
            last = current_captions[-1]
            t_end = last["start"] + last["duration"]
            text = " ".join(c["text"] for c in current_captions)

            chunks.append(Document(
                page_content=text,
                metadata={
                    "video_id": video_id,
                    "t_start": round(window_start, 2),
                    "t_end": round(t_end, 2),
                    "t_start_display": _seconds_to_mmss(window_start),
                    "t_end_display": _seconds_to_mmss(t_end),
                    "title": title,
                    "language": language,
                },
            ))
            current_captions = []
            window_start = cap["start"]

        current_captions.append(cap)

    # Flush remaining captions
    if current_captions:
        last = current_captions[-1]
        t_end = last["start"] + last["duration"]
        text = " ".join(c["text"] for c in current_captions)

        chunks.append(Document(
            page_content=text,
            metadata={
                "video_id": video_id,
                "t_start": round(window_start, 2),
                "t_end": round(t_end, 2),
                "t_start_display": _seconds_to_mmss(window_start),
                "t_end_display": _seconds_to_mmss(t_end),
                "title": title,
                "language": language,
            },
        ))

    return chunks


def ingest_video(
    video_id: str,
    title: str = "",
    languages: list[str] | None = None,
    window_sec: float = 30.0,
) -> list[Document]:
    """
    Full ingestion pipeline: fetch transcript -> 30-second chunks with metadata.
    """
    transcript_list = fetch_transcript(video_id, languages)
    language = languages[0] if languages else "en"
    chunks = chunk_by_time(transcript_list, video_id, title, language, window_sec)
    return chunks
