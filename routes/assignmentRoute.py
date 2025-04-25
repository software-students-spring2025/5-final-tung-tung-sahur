from flask import Blueprint, render_template

assignment_bp = Blueprint('assignment', __name__)

@assignment_bp.route('/assignments')
def show_assignments():
    return "Here are your assignments"
