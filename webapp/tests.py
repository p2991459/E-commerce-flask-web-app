import click
import datetime
import logging
from flask import Blueprint
from project.main import (
    list_all_routific_projects, get_project, get_order_id_from_custom_notes, remove_visits_from_project,
    auto_schedule_order
)
#from __init__ import db

log = logging.getLogger(__name__)
tests = Blueprint('tests', __name__)


@tests.cli.command('test-cancel-order-webhook')
@click.option('--order_id', help="The squarespace onetime order id", required=True, default=0)
def test_cancel_order_webhook(order_id):
    orderId = order_id
    log.debug("In canceled")
    log.debug("Order %s has been canceled" % orderId)
    # remove the order from future routific projects if scheduled already
    all_routific_projects = list_all_routific_projects()
    future_routific_projects = []
    for project in all_routific_projects:
        project_date = project.get('date')
        project_name = project.get('name', '--')
        if datetime.datetime.strptime(project_date, '%Y-%m-%d').date() > datetime.date.today():
            log.debug("The project %s on %s is a future project" % (project_name, project_date))
            future_routific_projects.append(project)
    log.debug("We found %s future routific projects" % len(future_routific_projects))
    log.debug("Checking if we find order_id %s in them" % orderId)
    for fp in future_routific_projects:
        rp = get_project(fp['_id'])
        visits = rp.get('visits', [])
        visits_to_remove = []
        for visit in visits:
            notes_order_id = get_order_id_from_custom_notes(visits.get(visit))
            if notes_order_id and int(notes_order_id) == int(orderId):
                log.debug("Order ID %s found in %s" % (orderId, rp['name']))
                visits_to_remove.append(visit)
        if visits_to_remove:
            remove_visits_from_project(fp['_id'], visits_to_remove)
        else:
            print("Order ID %s not found in %s" % (orderId, rp['name']))
    # mark order as canceled
    order_canceled_distinguish = 'CANCELED'
    # soc = get_squarespace_order_from_order_id(orderId)
    # if soc:
    #     log.debug("Renaming %s to %s-%s" % (soc.squarespace_order_id, soc.squarespace_order_id,
    #                                         order_canceled_distinguish))
    #     soc.squarespace_order_id = '%s-%s' % (
    #         soc.squarespace_order_id, order_canceled_distinguish)
    # db.session.commit()


@tests.cli.command('test-auto-schedule-order')
@click.option('--order_id', help="The squarespace onetime order id", required=True, default=0)
def test_auto_schedule(order_id):
    auto_schedule_order(order_id)
