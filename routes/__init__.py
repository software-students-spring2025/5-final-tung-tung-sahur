from .assignmentRoute import assignment_bp
from .githubRoute import github_bp
from .contentRoute import content_bp

all_blueprints = [
    assignment_bp, github_bp, content_bp
]
