from .assignmentRoute import assignment_bp
from .githubRoute import github_bp
from .chatRoute import chat_bp
all_blueprints = [
    assignment_bp, github_bp, chat_bp
]
