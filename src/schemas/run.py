from enum import Enum


class RunStatus(str, Enum):
    completed = "completed"
    needs_review = "needs_review"
    failed = "failed"
