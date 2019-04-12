from anthill.framework.db import db
from anthill.framework.utils import timezone
from anthill.framework.utils.translation import translate as _
from .exceptions import ValidationError, ConstraintError
from sqlalchemy_utils.types import ChoiceType
from sqlalchemy import event
from celery import schedules
import datetime


class Model(db.Model):
    __abstract__ = True

    @classmethod
    def filter_by(cls, session, **kwargs):
        return session.query(cls).filter_by(**kwargs)

    @classmethod
    def get_or_create(cls, session, defaults=None, **kwargs):
        obj = session.query(cls).filter_by(**kwargs).first()
        if obj:
            return obj, False
        else:
            params = dict((k, v) for k, v in kwargs.iteritems())
            params.update(defaults or {})
            obj = cls(**params)
            return obj, True

    @classmethod
    def update_or_create(cls, session, defaults=None, **kwargs):
        obj = session.query(cls).filter_by(**kwargs).first()
        if obj:
            for key, value in defaults.iteritems():
                setattr(obj, key, value)
            created = False
        else:
            params = dict((k, v) for k, v in kwargs.iteritems())
            params.update(defaults or {})
            obj = cls(**params)
            created = True
        return obj, created


class IntervalSchedule(Model):
    __tablename__ = "interval_schedule"

    PERIOD_CHOICES = (
        ('days', _('Days')),
        ('hours', _('Hours')),
        ('minutes', _('Minutes')),
        ('seconds', _('Seconds')),
        ('microseconds', _('Microseconds'))
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    every = db.Column(db.Integer, nullable=False)
    period = db.Column(ChoiceType(PERIOD_CHOICES))
    periodic_tasks = db.relationship('PeriodicTask')

    @property
    def schedule(self):
        return schedules.schedule(datetime.timedelta(**{self.period.code: self.every}))

    @classmethod
    def from_schedule(cls, session, schedule, period='seconds'):
        every = max(schedule.run_every.total_seconds(), 0)
        obj = cls.filter_by(session, every=every, period=period).first()
        if obj is None:
            return cls(every=every, period=period)
        else:
            return obj

    def __str__(self):
        if self.every == 1:
            return _('every {0.period_singular}').format(self)
        return _('every {0.every} {0.period}').format(self)

    @property
    def period_singular(self):
        return self.period[:-1]


class CrontabSchedule(Model):
    """
    Task result/status.
    """
    __tablename__ = "crontab_schedule"
    __table_args__ = (
        db.UniqueConstraint('minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    minute = db.Column(db.String(length=120), default="*")
    hour = db.Column(db.String(length=120), default="*")
    day_of_week = db.Column(db.String(length=120), default="*")
    day_of_month = db.Column(db.String(length=120), default="*")
    month_of_year = db.Column(db.String(length=120), default="*")

    periodic_tasks = db.relationship('PeriodicTask')

    def __str__(self):
        rfield = lambda f: f and str(f).replace(' ', '') or '*'
        return '{0} {1} {2} {3} {4} (m/h/d/dM/MY)'.format(
            rfield(self.minute), rfield(self.hour), rfield(self.day_of_week),
            rfield(self.day_of_month), rfield(self.month_of_year),
        )

    @property
    def schedule(self):
        spec = {
            'minute': self.minute,
            'hour': self.hour,
            'day_of_week': self.day_of_week,
            'day_of_month': self.day_of_month,
            'month_of_year': self.month_of_year
        }
        return schedules.crontab(**spec)

    # noinspection PyProtectedMember
    @classmethod
    def from_schedule(cls, session, schedule):
        spec = {
            'minute': schedule._orig_minute,
            'hour': schedule._orig_hour,
            'day_of_week': schedule._orig_day_of_week,
            'day_of_month': schedule._orig_day_of_month,
            'month_of_year': schedule._orig_month_of_year
        }
        obj = cls.filter_by(session, **spec).first()
        if obj is None:
            return cls(**spec)
        else:
            return obj


class PeriodicTasks(Model):
    __tablename__ = "periodic_tasks"

    ident = db.Column(db.Integer, default=1, primary_key=True)
    last_update = db.Column(db.DateTime, default=timezone.now)

    @classmethod
    def changed(cls, session, instance):
        if not instance.no_changes:
            obj, _ = cls.update_or_create(
                session, defaults={'last_update': timezone.now()}, ident=1)
            session.add(obj)
            session.commit()

    @classmethod
    def last_change(cls, session):
        obj = cls.filter_by(session, ident=1).first()
        return obj.last_update if obj else None


class PeriodicTask(Model):
    __tablename__ = "periodic_task"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(length=120), unique=True)
    task = db.Column(db.String(length=120))
    crontab_id = db.Column(db.Integer, db.ForeignKey('crontab_schedule.id'))
    crontab = db.relationship("CrontabSchedule", back_populates="periodic_tasks")
    interval_id = db.Column(db.Integer, db.ForeignKey('interval_schedule.id'))
    interval = db.relationship("IntervalSchedule", back_populates="periodic_tasks")
    args = db.Column(db.String(length=120))
    kwargs = db.Column(db.String(length=120))
    last_run_at = db.Column(db.DateTime, default=timezone.now)
    total_run_count = db.Column(db.Integer, default=0)
    enabled = db.Column(db.Boolean, default=True)
    no_changes = False

    def __str__(self):
        fmt = '{0.name}: {0.crontab}'
        return fmt.format(self)

    @property
    def schedule(self):
        if self.crontab:
            return self.crontab.schedule
        if self.interval:
            return self.interval.schedule


Session = db.session.__class__


@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    for obj in session.new | session.dirty:
        if isinstance(obj, PeriodicTask):
            if not obj.interval and not obj.crontab:
                raise ConstraintError('One of interval or crontab must be set.')
            if obj.interval and obj.crontab:
                raise ConstraintError('Only one of interval or crontab must be set')
            PeriodicTasks.changed(session, obj)
