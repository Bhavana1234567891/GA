"""
RAGAS evaluation: faithfulness + answer_relevancy.
No ground truth needed for these two metrics.

Usage:
    python -m backend.evaluation.eval --video_id LPZh9BOjkQs
"""

import argparse
import json

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset

from backend.chain.rag_chain import chat
from backend.vectorstore.store import is_video_indexed


# Sample evaluation questions (customize per video)
DEFAULT_EVAL_QUESTIONS = [
    "What is the main topic of this video?",
    "Who is the speaker or guest in this video?",
    "Can you summarize the key points discussed?",
    "What is the most interesting claim made in the video?",
    "Does the video discuss artificial intelligence?",
    "What conclusions does the speaker reach?",
    "Are there any controversial opinions expressed?",
    "What examples or analogies does the speaker use?",
    "What is discussed at the beginning of the video?",
    "What is mentioned towards the end of the video?",
    "Is there any discussion about the future?",
    "What advice or recommendations are given?",
    "Does the speaker mention any specific companies or organizations?",
    "What personal experiences does the speaker share?",
    "Are there any numbers or statistics mentioned?",
]


def run_eval(video_id: str, questions: list[str] | None = None) -> dict:
    """
    Run RAGAS evaluation on the given video.
    Returns the evaluation result dict with scores.
    """
    if not is_video_indexed(video_id):
        raise ValueError(f"Video {video_id} is not indexed yet. Index it first.")

    questions = questions or DEFAULT_EVAL_QUESTIONS

    answers = []
    contexts = []

    for q in questions:
        result = chat(q, video_id, session_id=f"eval_{video_id}")
        answers.append(result["answer"])
        source_texts = [s.page_content for s in result.get("sources", [])]
        contexts.append(source_texts)

    eval_dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
    })

    result = evaluate(
        dataset=eval_dataset,
        metrics=[faithfulness, answer_relevancy],
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation")
    parser.add_argument("--video_id", required=True, help="YouTube video ID")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    print(f"Running RAGAS evaluation for video: {args.video_id}")
    print(f"Metrics: faithfulness, answer_relevancy")
    print(f"Questions: {len(DEFAULT_EVAL_QUESTIONS)}")
    print("-" * 50)

    result = run_eval(args.video_id)

    print("\n=== RAGAS Evaluation Results ===")
    print(f"Faithfulness:      {result['faithfulness']:.4f}")
    print(f"Answer Relevancy:  {result['answer_relevancy']:.4f}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "video_id": args.video_id,
                "faithfulness": float(result["faithfulness"]),
                "answer_relevancy": float(result["answer_relevancy"]),
            }, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
