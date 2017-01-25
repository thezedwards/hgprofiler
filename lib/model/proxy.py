from sqlalchemy import Column
from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import Enum
from model import Base


class Proxy(Base):
    ''' Data model for a proxy. '''

    __tablename__ = 'proxy'

    id = Column(Integer, primary_key=True)
    protocol = Column(
        Enum('http', name='proxy_protocol_types')
    )
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint('protocol',
                         'host',
                         'port',
                         name='_proxy_protocol_host_port_uc'),
    )

    def __init__(self, protocol, host, port,
                 username=None, password=None, active=True):
        ''' Constructor. '''

        self.protocol = protocol
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.active = active

    def as_dict(self):
        ''' Return dictionary representation of this site. '''
        return {
            'id': self.id,
            'protocol': self.protocol,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'active': self.active
        }
