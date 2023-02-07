from . import db
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import relationship


class Vehicle(db.Model):
    """
    Store Vehicle Related information.
    """

    __tablename__ = 'vehicle'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256), nullable=True)
    oil_change_date = db.Column(db.Text, default=datetime.now().isoformat())
    next_oil_change_date = db.Column(db.Text, default=datetime.now().isoformat())
    car_registration_date = db.Column(db.Text, default=datetime.now().isoformat())
    car_renewal_date = db.Column(db.Text, default=datetime.now().isoformat())
    city_sticker_date = db.Column(db.Text, default=datetime.now().isoformat())
    next_city_sticker_date = db.Column(db.Text, default=datetime.now().isoformat())
    reminder_email = db.Column(db.String(256), nullable=True)
    updated_at = db.Column(db.Text, default=datetime.now().isoformat())
    vehicle_repairs = relationship("VehicleRepair", cascade="all,delete", back_populates="vehicle")
    vehicle_requests = relationship("VehicleRequest", cascade="all,delete", back_populates="vehicle")

    def __init__(self, name, oil_change_date, next_oil_change_date, car_registration_date, car_renewal_date,
                 city_sticker_date, next_city_sticker_date, reminder_email,
                 updated_at=datetime.now().isoformat()) -> None:
        self.name = name
        self.oil_change_date = oil_change_date
        self.next_oil_change_date = next_oil_change_date
        self.car_registration_date = car_registration_date
        self.car_renewal_date = car_renewal_date
        self.city_sticker_date = city_sticker_date
        self.next_city_sticker_date = next_city_sticker_date
        self.reminder_email = reminder_email
        self.updated_at = updated_at

    def save(self):
        db.session.add(self)
        db.session.commit()

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @staticmethod
    def get_next_oil_change_date(oil_change_date):
        try:
            datetime_obj = datetime.strptime(oil_change_date, '%m/%d/%Y')
            date_object = datetime_obj + relativedelta(months=+4)
            return date_object.date().strftime("%m/%d/%Y")
        except Exception as ex:
            print(str(ex))
            return ''

    @staticmethod
    def get_car_renewal_date(car_registration_date):
        try:
            datetime_obj = datetime.strptime(car_registration_date, '%m/%d/%Y')
            date_object = datetime_obj + relativedelta(months=+11)
            return date_object.date().strftime("%m/%d/%Y")
        except Exception as ex:
            print(str(ex))
            return ''

    @staticmethod
    def get_next_city_sticker_date(city_sticker_date):
        try:
            datetime_obj = datetime.strptime(city_sticker_date, '%m/%d/%Y')
            date_object = datetime_obj + relativedelta(years=+1)
            return date_object.date().strftime("%m/%d/%Y")
        except Exception as ex:
            print(str(ex))
            return ''

    @staticmethod
    def get_all_vehicles():
        return Vehicle.query.all()

    @staticmethod
    def delete_vehicle_by_id(vehicle_id):
        vehicle = Vehicle.query.get(vehicle_id)
        for repair in vehicle.vehicle_repairs:
            db.session.delete(repair)
        for request in vehicle.vehicle_requests:
            db.session.delete(request)
        db.session.commit()
        db.session.delete(vehicle)
        db.session.commit()
        return vehicle

    @staticmethod
    def get_vehicle_by_id(vehicle_id):
        vehicle = Vehicle.query.get(vehicle_id)
        return vehicle

    @staticmethod
    def update_vehicle(vehicle_id, data_to_be_updated):
        Vehicle.query.filter(Vehicle.id == vehicle_id).update(data_to_be_updated)
        db.session.commit()

    def __str__(self) -> str:
        return super().__str__(self.name)
