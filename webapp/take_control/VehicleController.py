from project import db
from flask import render_template, request, jsonify, redirect, flash
from flask_login import login_required
from project.model import Vehicle, VehicleRepair
from project.main import check_user_permission
from project.common import api_vehicle
from decouple import config

SITE_URL = config('SITE_URL', '')


def get_posted_data(post_request):
    try:
        data = post_request.get_json()
        data['name'] = data['name']
        data['oil_change_date'] = data['oil_change_date']
        data['next_oil_change_date'] = Vehicle.get_next_oil_change_date(
            oil_change_date=data['oil_change_date'])
        data['car_registration_date'] = data['car_registration_date']
        data['car_renewal_date'] = Vehicle.get_car_renewal_date(
            car_registration_date=data['car_registration_date'])
        data['city_sticker_date'] = data['city_sticker_date']
        data['next_city_sticker_date'] = Vehicle.get_next_city_sticker_date(
            city_sticker_date=data['city_sticker_date'])
        data["reminder_email"] = data['reminder_email']
    except Exception as e:
        raise e
    return data


@api_vehicle.route("/add_vehicle", methods=['GET', 'POST', 'DELETE'])
@login_required
def add_vehicle():
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    vehicle_list = Vehicle.get_all_vehicles()

    if request.method == 'POST':
        try:
            data = get_posted_data(request)
            vehicle = Vehicle(**data)
            vehicle.save()
            msg = "Vehicle added successfully"
            flash(msg)
            return jsonify({"message": msg, 'status': 201})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return render_template('vehicle/vehicle.html', site_url=SITE_URL, all_permissions=all_permissions,
                           vehicle_list=vehicle_list)


@api_vehicle.route("/update_vehicle/<int:vehicle_id>", methods=["PUT"])
def update_vehicle(vehicle_id):
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    if vehicle_id:
        try:
            data = get_posted_data(request)
            Vehicle.update_vehicle(vehicle_id=int(vehicle_id), data_to_be_updated=data)
            msg = "Vehicle updated successfully"
            flash(msg)
            return jsonify({"message": msg, 'status': 201})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route("/delete_vehicle/<int:vehicle_id>", methods=["DELETE"])
def delete_vehicle(vehicle_id):
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    if vehicle_id:
        try:
            Vehicle.delete_vehicle_by_id(vehicle_id=vehicle_id)
            msg = "Vehicle deleted successfully"
            flash(msg)
            return jsonify({"message": msg, 'status': 201})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route("/get_vehicle/<int:vehicle_id>", methods=["GET"])
def get_vehicle(vehicle_id):
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    if vehicle_id:
        try:
            vehicle = Vehicle.get_vehicle_by_id(vehicle_id=vehicle_id)
            return jsonify({
                "message": "record found!",
                "status": 200,
                "data": vehicle.as_dict()
            })
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})
