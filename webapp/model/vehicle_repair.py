from . import db
from datetime import datetime
from sqlalchemy.orm import relationship


class VehicleRepair(db.Model):
    """
    Store Vehicle Repair Related information.
    """
    __tablename__ = 'vehicle_repair'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vehicle_id = db.Column(
        db.Text, db.ForeignKey('vehicle.id'),
        nullable=False
    )
    vehicle_no = db.Column(db.String(256), nullable=False)
    driver_name = db.Column(db.String(256), nullable=True)
    repair_detail = db.Column(db.String(256), nullable=True)
    repair_location = db.Column(db.String(256), nullable=True)
    repair_date = db.Column(db.Text, nullable=True)
    repair_receipt = db.Column(db.String(256), nullable=True)
    reminder_email = db.Column(db.String(256), nullable=True)
    updated_at = db.Column(db.Text, default=datetime.now().isoformat())
    vehicle = relationship("Vehicle", back_populates="vehicle_repairs")

    def __init__(self, vehicle_id, vehicle_no, driver_name, repair_detail, repair_location, repair_date,
                 reminder_email, updated_at=None, repair_receipt=None):
        self.vehicle_id = vehicle_id
        self.vehicle_no = vehicle_no
        self.driver_name = driver_name
        self.repair_detail = repair_detail
        self.repair_location = repair_location
        self.repair_date = repair_date
        self.repair_receipt = repair_receipt
        self.reminder_email = reminder_email
        self.updated_at = updated_at if updated_at else datetime.now().isoformat()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def as_dict(self):
        """
        Single object convert into Json.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @staticmethod
    def get_all_repair_records():
        """
        Queryset return all vehicle record.
        """
        return VehicleRepair.query.all()

    @staticmethod
    def get_vehicle_repair_record_by_id(vehicle_repair_id):
        """
        Get Vehicle Record by id.
        """
        vehicle_repair = VehicleRepair.query.get(vehicle_repair_id)
        return vehicle_repair

    @staticmethod
    def update_vehicle_repair(vehicle_repair_id, data_to_be_updated):
        """
        Update vehicle repair records by.
        """
        VehicleRepair.query.filter(VehicleRepair.id == vehicle_repair_id).update(data_to_be_updated)
        db.session.commit()

    @staticmethod
    def delete_vehicle_repair_by_id(vehicle_repair_id):
        """
        Delete record by id.
        """
        import os
        vehicle_repair = VehicleRepair.query.get(vehicle_repair_id)
        db.session.delete(vehicle_repair)
        db.session.commit()
        try:
            if os.path.exists(os.path.join(os.getcwd(), "project/static/vehicle_receipt", vehicle_repair.repair_receipt)):
                os.remove(os.path.join(os.getcwd(), "project/static/vehicle_receipt", vehicle_repair.repair_receipt))
        except Exception as e:
            print(e)
        return vehicle_repair

    def __str__(self) -> str:
        return super().__str__(self.vehicle_name)
