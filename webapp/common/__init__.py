from flask import Blueprint
api_vehicle = Blueprint('api_vehicle', __name__, url_prefix='/vehicle', template_folder="templates", static_folder='static')
