from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from model import Base


category_join_site = Table(
    'category_join_site',
    Base.metadata,
    Column('category_id',
           Integer,
           ForeignKey('category.id'),
           primary_key=True),
    Column('site_id',
           Integer,
           ForeignKey('site.id'),
           primary_key=True),
)


class Category(Base):
    ''' Data model for a profile. '''

    __tablename__ = 'category'
    __table_args__ = (
        UniqueConstraint('name', name='category_name'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    # One category has 0-n sites.
    sites = relationship(
        'Site',
        secondary=category_join_site
    )

    def __init__(self, name, sites):
        ''' Constructor. '''

        self.name = name
        self.sites = sites

    def as_dict(self):
        ''' Return dictionary representation of this site. '''
        # Sort labels by name
        sites = [site.as_dict() for site in self.sites]
        sorted_sites = sorted(sites, key=lambda x: x['name'])
        return {
            'id': self.id,
            'name': self.name,
            'sites': sorted_sites,
        }
