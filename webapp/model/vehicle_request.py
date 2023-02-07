from . import db
from datetime import datetime
from sqlalchemy.orm import relationship
from project.models import User


class VehicleRequest(db.Model):
    """
    Store Vehicle Requested Related information.
    """

    __tablename__ = 'vehicle_request'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # name = db.Column(db.String(256), nullable=True)
    date = db.Column(db.String(256), nullable=True)
    vehicle_id = db.Column(
        db.Text, db.ForeignKey('vehicle.id'),
        nullable=False
    )
    vehicle = relationship("Vehicle", back_populates="vehicle_requests")
    user = db.relationship("User", backref=db.backref("user", uselist=False))
    pickup_time = db.Column(db.Text, default=datetime.now().isoformat())
    return_time = db.Column(db.Text, default=datetime.now().isoformat())
    approved = db.Column(db.Text)
    user_id = db.Column(
            db.Text, db.ForeignKey('user.id'),
            nullable=False
        )
    updated_at = db.Column(db.Text, default=datetime.now().isoformat())

    def __init__(self, date, vehicle_id, pickup_time, return_time,
     approved=None, user_id=None, updated_at=datetime.now().isoformat()) -> None:
        # self.name = name
        self.date = date
        self.vehicle_id = vehicle_id
        self.pickup_time = pickup_time
        self.return_time = return_time
        if approved != None:
            self.approved = approved
        if user_id !=None:
            self.user_id = user_id
        self.updated_at = updated_at

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_all_vehicle_requests(user_id=None):
        query = VehicleRequest.query\
            .join(User, User.id==VehicleRequest.user_id)\
            .add_columns(User.name)

        if user_id:
            query = query.filter(VehicleRequest.user_id == user_id)

        return query.all()

    @staticmethod
    def delete_vehicle_request_by_id(request_id):
        req = VehicleRequest.query.get(request_id)
        db.session.delete(req)
        db.session.commit()
        return req

    @staticmethod
    def get_vehicle_request_by_id(request_id):
        req = VehicleRequest.query.get(request_id)
        return req

    @staticmethod
    def update_vehicle_request(request_id, data_to_be_updated):
        vr = VehicleRequest.query.filter(VehicleRequest.id == request_id)
        vr.update(data_to_be_updated)
        db.session.commit()
        return vr.first()
