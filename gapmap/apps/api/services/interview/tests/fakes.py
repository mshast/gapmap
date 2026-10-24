"""Shared test doubles for the interview module."""

from gapmap.apps.api.services.interview.schema import FeedbackDraft


def feedback_draft(*, score=3, quote=None, follow_up=None, accuracy=True) -> FeedbackDraft:
    item = {"score": score, "comment": "One sentence.", "answer_quote": quote}
    return FeedbackDraft.model_validate({
        "scores": {
            "relevance": item, "specificity": item, "structure": item, "impact": item,
            "accuracy": item if accuracy else None,
        },
        "improvements": ["Lead with the result.", "Name the tools you used."],
        "suggested_rewrite": "I built the service. [result you measured]",
        "follow_up": follow_up,
    })


def completion(content) -> dict:
    return {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}


class FakeClient:
    """Scripted InterviewClient that records how it was called."""

    mode = "llm"

    def __init__(self, question_sets, feedback=None):
        self.question_sets = list(question_sets)
        self.feedback = feedback or feedback_draft()
        self.generate_calls = 0
        self.allow_follow_up: list[bool] = []

    async def generate_questions(self, requirements):
        self.generate_calls += 1
        result = self.question_sets.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def evaluate(self, question, answer_text, *, allow_follow_up):
        self.allow_follow_up.append(allow_follow_up)
        return self.feedback
