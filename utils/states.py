from enum import Enum

class States(str, Enum):
    IDLE = "idle"

    TITLE = "title"
    DESCRIPTION = "description"

    QUESTION = "question"
    OPTIONS = "options"
    ANSWER = "answer"

    TIMER = "timer"
    SHUFFLE = "shuffle"

    READY = "ready"
