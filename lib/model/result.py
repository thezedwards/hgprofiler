from datetime import datetime
from sqlalchemy import (Column,
                        DateTime,
                        ForeignKey,
                        Integer,
                        String,
                        Text,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ChoiceType

from model import Base


class Result(Base):
    ''' Data model for a job result. '''

    __tablename__ = 'result'
    __table_args__ = (
        UniqueConstraint('tracker_id', 'site_url', name='tracker_id_site_url'),
    )

    STATUS_TYPES = [
        (u'f', u'Found'),
        (u'n', u'Not Found'),
        (u'e', u'Error')
    ]

    id = Column(Integer, primary_key=True)
    tracker_id = Column(String(255), nullable=False)
    site_name = Column(String(255), nullable=False)
    site_url = Column(String(255), nullable=False)
    site_id = Column(Integer, nullable=False)
    status = Column(ChoiceType(STATUS_TYPES), nullable=False)
    image_file_id = Column(Integer,
                           ForeignKey('file.id',
                                      name='fk_image_file'),
                           nullable=True)
    image_file = relationship('File',
                              lazy='joined',
                              backref='result',
                              uselist=False,
                              cascade='all')
    error = Column(String(255), nullable=True)
    html = Column(Text, nullable=True)
    username = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self,
                 tracker_id,
                 site_name,
                 site_url,
                 site_id,
                 status,
                 username,
                 image_file_id=None,
                 thumb=None,
                 error=None,
                 html=None):
        ''' Constructor. '''

        self.tracker_id = tracker_id
        self.site_id = site_id
        self.site_name = site_name
        self.site_url = site_url
        self.status = status
        self.image_file_id = image_file_id
        self.thumb = thumb
        self.error = error
        self.html = html
        self.username = username

    def as_dict(self):
        ''' Return dictionary representation of this result. '''

        if self.image_file is not None:
            image_file_url = self.image_file.url()
            image_file_name = self.image_file.name
        else:
            image_file_url = None
            image_file_name = None

        return {
            'created_at': self.created_at.isoformat(),
            'error': self.error,
            'html': self.html,
            'id': self.id,
            'image_file_id': self.image_file_id,
            'image_file_url': image_file_url,
            'image_file_name': image_file_name,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'site_url': self.site_url,
            'status': self.status.code,
            'tracker_id': self.tracker_id,
            'username': self.username,
        }
