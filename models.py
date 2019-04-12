# For more details, see
# http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#declare-a-mapping
from anthill.framework.db import db
from sqlalchemy.ext.declarative import declared_attr


class BaseApplication(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    name = db.Column(db.String(128), nullable=False, unique=True)

    @declared_attr
    def versions(self):
        return db.relationship('ApplicationVersion', backref='application', lazy='dynamic')

    @classmethod
    def latest_version(cls):
        pass


class BaseApplicationVersion(db.Model):
    __abstract__ = True
    __table_args__ = (
        db.UniqueConstraint('value', 'application_id'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    value = db.Column(db.String(128), nullable=False)

    @declared_attr
    def application_id(self):
        return db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    @classmethod
    def latest(cls):
        pass

    def __lt__(self, other):
        return self.value < other.value
