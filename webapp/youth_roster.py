# youth_roster.py

from flask import (
    Blueprint, render_template, redirect, request, url_for, jsonify
)
from sqlalchemy import func
from . import db
from flask_login import login_required, current_user
from .models import (
    TimeTracking, YouthEmployee, YouthManager, YouthPartner
)
from .main import (check_user_permission, SITE_URL, is_email_sent, send_email, EmailTrace)
from string import Template
from decouple import config
import datetime
import logging

youth = Blueprint('youth', __name__)
log = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)

YOUTH_SURVEY_FORM_LINK = config('YOUTH_SURVEY_FORM_LINK')

@youth.route('/youth_roster', methods=['GET', 'POST'])
@login_required
def get_youth_roster():
    all_permissions = check_user_permission('youth_management')
    if all_permissions is False:
        return redirect("/", code=302)
    
    current_tab = request.values.get("current_tab", "youth_employee")
    youth_partners = YouthPartner.query.all()
    team_managers = YouthManager.query.all()
    youth_employees = YouthEmployee.query.all()
    return render_template("youth_roster.html", name=current_user.name,
                           youth_partners=youth_partners, team_managers=team_managers, youth_employees=youth_employees,
                           current_tab=current_tab, title="Youth Roster",
                           site_url=SITE_URL, all_permissions=all_permissions)


