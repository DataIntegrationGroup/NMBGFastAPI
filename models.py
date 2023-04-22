# ===============================================================================
# Copyright 2023 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================
from numbers import Real

import pyproj as pyproj
from sqlalchemy import (
    Column,
    Integer,
    UUID,
    String,
    Boolean,
    ForeignKey,
    Float,
    Numeric,
    Date,
    Time,
    DateTime,
)
from sqlalchemy.orm import relationship, declared_attr

from database import Base

zone = 12
PROJECTION = pyproj.Proj(proj="utm", zone=int(zone), ellps="WGS84")


class Location(Base):
    __tablename__ = "Location"
    LocationId = Column(UUID, primary_key=True)
    PointID = Column(String(50))
    PublicRelease = Column(Boolean)
    Easting = Column(Integer)
    Northing = Column(Integer)

    @property
    def geometry(self):
        e, n = self.Easting, self.Northing
        lon, lat = PROJECTION(e, n, inverse=True)
        return {"coordinates": [lon, lat], "type": "Point"}


class LU_Mixin(object):
    Code = Column(Integer, primary_key=True)
    Meaning = Column(String(50))


class LU_Formations(Base, LU_Mixin):
    __tablename__ = "LU_Formations"


class LU_MeasurementMethod(Base, LU_Mixin):
    __tablename__ = "LU_MeasurementMethod"


class LU_DataSource(Base, LU_Mixin):
    __tablename__ = "LU_DataSource"


class Well(Base):
    __tablename__ = "WellData"
    LocationId = Column(UUID, ForeignKey("Location.LocationId"))
    WellID = Column(UUID, primary_key=True)
    PointID = Column(String(50))
    HoleDepth = Column(Integer)
    WellDepth = Column(Integer)
    OSEWellID = Column(String(50))
    OSEWelltagID = Column(String(50))
    MeasuringPoint = Column(String(50))
    MPHeight = Column(Numeric)
    CasingDiameter = Column(Numeric)
    CasingDepth = Column(Numeric)
    CasingDescription = Column(String(50))
    FormationZone = Column(String(50), ForeignKey("LU_Formations.Code"))
    StaticWater = Column(Numeric)

    lu_formation = relationship("LU_Formations", backref="wells", uselist=False)
    location = relationship("Location", backref="well", uselist=False)
    waterlevels = relationship("WaterLevels", backref="well", uselist=False)

    @property
    def formation(self):
        return self.lu_formation.Meaning


class MeasurementMixin(object):
    MeasurementMethod = Column(String(50), ForeignKey("LU_MeasurementMethod.Code"))
    MeasuringAgency = Column(String(50))
    DataSource = Column(String(50), ForeignKey("LU_DataSource.Code"))

    @declared_attr
    def lu_measurement_method(cls):
        return relationship("LU_MeasurementMethod", uselist=False)

    @declared_attr
    def lu_data_source(cls):
        return relationship("LU_DataSource", uselist=False)

    @property
    def measurement_method(self):
        return self.lu_measurement_method.Meaning

    @property
    def data_source(self):
        return self.lu_data_source.Meaning


class WaterLevelsContinuous_Pressure(Base, MeasurementMixin):
    __tablename__ = "WaterLevelsContinuous_Pressure"
    GlobalID = Column(UUID, primary_key=True)
    OBJECTID = Column(Integer)
    WellID = Column(UUID, ForeignKey("WellData.WellID"))
    DepthToWaterBGS = Column(Numeric)

    DateMeasured = Column(DateTime)
    # MeasuringAgency = Column(String(50))
    # MeasurementMethod = Column(String(50), ForeignKey('LU_MeasurementMethod.Code'))
    # DataSource = Column(String(50), ForeignKey('LU_DataSource.Code'))
    #


class WaterLevels(Base, MeasurementMixin):
    __tablename__ = "WaterLevels"
    OBJECTID = Column(Integer, primary_key=True)
    WellID = Column(UUID, ForeignKey("WellData.WellID"), primary_key=True)
    DepthToWaterBGS = Column(Numeric)
    DateMeasured = Column(Date)
    TimeMeasured = Column(Time)

    PublicRelease = Column(Boolean)


# ============= EOF =============================================
