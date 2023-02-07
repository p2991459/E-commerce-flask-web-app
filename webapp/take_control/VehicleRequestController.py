from flask import render_template, request, jsonify, redirect
from flask_login import login_required, current_user
from project.model import Vehicle, VehicleRequest
from project.main import check_user_permission, send_email, ADMIN_EMAIL
from project.common import api_vehicle
from decouple import config
import datetime
from project.auth import is_admin

SITE_URL = config('SITE_URL', '')


def get_posted_data(post_request):
    try:
        req_data = post_request.get_json()
        data = dict()
        data['date'] = req_data.get('date')
        data['vehicle_id'] = req_data.get('vehicle_id')
        data['pickup_time'] = req_data.get('pickup_time')
        data['return_time'] = req_data.get('return_time')
        data['approved'] = req_data.get('approved')
    except Exception as e:
        raise e
    return data


@api_vehicle.route("/vehicle_request", methods=['GET', 'POST'])
@login_required
def vehicle_request():
    mgmt_permissions = check_user_permission('employee_management')
    section_permissions = check_user_permission('employee_section')
    if mgmt_permissions is False and section_permissions is False:
        return redirect("/", code=302)
    request_list = VehicleRequest.get_all_vehicle_requests()
    vehicle_list = Vehicle.get_all_vehicles()

    if request.method == 'POST':
        try:
            data = get_posted_data(request)
            del data['approved']
            data['user_id'] = current_user.id
            req = VehicleRequest(**data)
            req.save()
            if not is_admin(): notify_admin_for_v_req(req)
            msg = "Vehicle added successfully"
            return jsonify({'message': msg, 'insert_id': req.id,  'status': 201})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return render_template('vehicle/vehicleRequest.html', site_url=SITE_URL, all_permissions=all_permissions,
                           request_list=request_list, vehicle_list=vehicle_list, is_admin=int(is_admin()))


@api_vehicle.route("/update_vehicle_request/<int:vehicle_request_id>", methods=["PUT"])
@login_required
def update_vehicle_request(vehicle_request_id):
    mgmt_permissions = check_user_permission('employee_management')
    section_permissions = check_user_permission('employee_section')
    if mgmt_permissions is False and section_permissions is False:
        return redirect("/", code=302)
    if vehicle_request_id:
        try:
            data = get_posted_data(request)
            if not is_admin():
                del data['approved']
            vr = VehicleRequest.update_vehicle_request(request_id=int(vehicle_request_id), data_to_be_updated=data)
            msg = "Vehicle updated successfully"
            if not is_admin(): notify_admin_for_v_req(vr, is_edited=True)
            return jsonify({"message": msg, 'status': 200})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route("/delete_vehicle_request/<int:vehicle_request_id>", methods=["DELETE"])
@login_required
def delete_vehicle_request(vehicle_request_id):
    mgmt_permissions = check_user_permission('employee_management')
    section_permissions = check_user_permission('employee_section')
    if mgmt_permissions is False and section_permissions is False:
        return redirect("/", code=302)
    if vehicle_request_id:
        try:
            VehicleRequest.delete_vehicle_request_by_id(request_id=vehicle_request_id)
            msg = "Vehicle Request deleted successfully"
            return jsonify({"message": msg, 'status': 200})
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route("/get_vehicle_request/<int:vehicle_request_id>", methods=["GET"])
@login_required
def get_vehicle_request(vehicle_request_id):
    mgmt_permissions = check_user_permission('employee_management')
    section_permissions = check_user_permission('employee_section')
    if mgmt_permissions is False and section_permissions is False:
        return redirect("/", code=302)
    if vehicle_request_id:
        try:
            vehicle_request = VehicleRequest.get_vehicle_request_by_id(request_id=vehicle_request_id)
            return jsonify({
                "message": "record found!",
                "status": 200,
                "data": vehicle_request.as_dict()
            })
        except Exception as e:
            return jsonify({"error": f"{str(e)}", 'status': 500})
    return jsonify({"error": "server error!", 'status': 500})


@api_vehicle.route('/veh_request_calendar_list', methods=["GET"])
@login_required
def veh_request_calendar_list():
    mgmt_permissions = check_user_permission('employee_management')
    section_permissions = check_user_permission('employee_section')
    if mgmt_permissions is False and section_permissions is False:
        return redirect("/", code=302)

    if mgmt_permissions != False:  # admin
        veh_req = VehicleRequest.get_all_vehicle_requests()
    else:
        veh_req = VehicleRequest.get_all_vehicle_requests(current_user.id)

    calendar_events = []
    for req, user_name in veh_req:
        try:
            calEvent = {}
            extended_prop = {}
            calEvent['id'] = str(req.id)
            calEvent['title'] = req.vehicle.name 
            calEvent['start'] = datetime.datetime.strptime(req.pickup_time, '%m-%d-%Y %H:%M').strftime('%Y-%m-%d %H:%M')
            calEvent['end'] = datetime.datetime.strptime(req.return_time, '%m-%d-%Y %H:%M').strftime('%Y-%m-%d %H:%M')

            if req.approved == '1':
                calEvent['color'] = "#99cc33"
            elif req.approved == '0':
                calEvent['color'] = "#ff0000"
            else:
                calEvent['color'] = "#ffa700"

            extended_prop = req.__dict__
            extended_prop['name'] = user_name
            del extended_prop['_sa_instance_state']
            del extended_prop['vehicle']

            calEvent['extendedProps'] = extended_prop
            calendar_events.append(calEvent)
        except Exception as e:
            print(e)
            pass
    return jsonify(calendar_events)


def notify_admin_for_v_req(v_req, is_edited=False):
    try:
        req_date, req_time = v_req.pickup_time.split() if v_req.pickup_time else ('', '')
        v_req_page = SITE_URL + '/vehicle_request'
        if is_edited:
            subject = 'Southside Blooms Vehicle Request Updated'
            mail_body = '''
                Hello,
                    <br><br>
                    This message is to notify you that {} has updated the request to use {} on {} at {}. Please login to review this <a href="{}">vehicle request</a>.
                    <br><br>
                    Thank you!
                    <br>
                    The Southside Blooms Team
            '''.format(v_req.user.name, v_req.vehicle.name,
                    req_date, req_time, v_req_page)
        else:
            subject = 'New Southside Blooms Vehicle Request'
            mail_body = '''
                Hello,
                    <br><br>
                    This message is to notify you that {} has requested to use {} on {} at {}. Please login to review this <a href="{}">vehicle request</a>.
                    <br><br>
                    Thank you!
                    <br>
                    The Southside Blooms Team
            '''.format(v_req.user.name, v_req.vehicle.name,
                    req_date, req_time, v_req_page)

        send_email(
            email=ADMIN_EMAIL,
            use_mailchimp=True,
            subject=subject,
            feedback_urls=mail_body,
            message_template_id='ssb-empty-content-no-footer',
        )
    except Exception as e:
        print(str(e))
        print('Something went wrong to send vehicle_request notification.')