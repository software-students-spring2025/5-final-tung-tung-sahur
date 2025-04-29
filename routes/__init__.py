from .assignmentRoute import assignment_bp
from .githubRoute import github_bp
from .emailRoute import email_bp

all_blueprints = [
    assignment_bp, github_bp, email_bp
]
