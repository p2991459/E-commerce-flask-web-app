from flask import render_template, request, jsonify, redirect, flash
from flask_login import login_required

from project.model import VehicleRepair
from project.main import check_user_permission
from project.common import api_vehicle
from werkzeug.utils import secure_filename
import os
from decouple import config

SITE_URL = config('SITE_URL', '')


def get_posted_data(post_request):
    try:
        data = dict()
        data["vehicle_id"] = post_request.form.get('vehicle_id', '')
        data["vehicle_no"] = post_request.form.get('vehicle_no', '')
        data["repair_date"] = post_request.form.get('repair_date', '')
        data["driver_name"] = post_request.form.get('driver_name', '')
        data["repair_location"] = post_request.form.get('repair_location', '')
        data["repair_detail"] = post_request.form.get('repair_detail', '')
        data['reminder_email'] = post_request.form.get('reminder_email', '')

        file = post_request.files.get('repair_receipt', None)
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(
                os.getcwd(), "project/static/repair_receipt", filename))
            data["repair_receipt"] = filename
    except Exception as e:
        raise e
    return data


@api_vehicle.route("/vehicle_repair", methods=['GET', 'POST', 'DELETE'])
@login_required
def vehicle_repair():
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    vehicle_repair_list = VehicleRepair.get_all_repair_records()
    if request.method == 'POST':
        try:
            data = get_posted_data(request)
            vehicle_repair_object = VehicleRepair(**data)
            vehicle_repair_object.save()
            msg = "Vehicle repair record added successfully!"
            flash(msg)
            return jsonify({"message": msg, 'status': 201})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return render_template('vehicle/vehicleRepair.html', site_url=SITE_URL, all_permissions=all_permissions, vehicle_repair_records=vehicle_repair_list)


@api_vehicle.route("/repair_update_vehicle/<int:vehicle_id>", methods=["PUT"])
def repair_update_vehicle(vehicle_id):
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    if vehicle_id:
        try:
            data = get_posted_data(request)
            VehicleRepair.update_vehicle_repair(
                vehicle_repair_id=int(vehicle_id), data_to_be_updated=data)
            msg = "Vehicle repair record updated successfully"
            flash(msg)
            return jsonify({"message": msg, 'status': 201})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route("/delete_vehicle_receipt/<int:vehicle_id>", methods=["DELETE"])
def delete_vehicle_receipt(vehicle_id):
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    if vehicle_id:
        try:
            VehicleRepair.delete_vehicle_repair_by_id(vehicle_repair_id=vehicle_id)
            msg = "Vehicle repair record successfully deleted!"
            flash(msg)
            return jsonify({"message": msg, 'status': 200})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route("/get_vehicle_repair/<int:vehicle_id>", methods=["GET"])
def get_vehicle_repair(vehicle_id):
    all_permissions = check_user_permission('operations')
    if all_permissions is False:
        return redirect("/", code=302)
    if vehicle_id:
        try:
            vehicle = VehicleRepair.get_vehicle_repair_record_by_id(vehicle_repair_id=vehicle_id)
            return jsonify({
                "message": "record found!",
                "status": 200,
                "data": vehicle.as_dict()
            })
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})
