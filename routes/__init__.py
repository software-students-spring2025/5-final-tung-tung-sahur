from .assignmentRoute import assignment_bp
from .githubRoute import github_bp
from .chatRoute import chat_bp
from .emailRoute import email_bp
from .contentRoute import content_bp

all_blueprints = [assignment_bp, github_bp, email_bp, chat_bp, content_bp]
