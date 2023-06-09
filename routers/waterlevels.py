# ===============================================================================
# Copyright 2023 ross
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
from fastapi import Depends, APIRouter
from fastapi_pagination import Page, LimitOffsetPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session

import models
from schemas import waterlevels
from crud import (
    read_waterlevels_manual_query,
    read_waterlevels_acoustic_query,
    read_waterlevels_pressure_query,
)
from dependencies import get_db

router = APIRouter(prefix="/waterlevels", tags=["waterlevels"])


# ============= EOF =============================================
@router.get("/manual", response_model=Page[waterlevels.WaterLevels])
@router.get(
    "/manual/limit-offset", response_model=LimitOffsetPage[waterlevels.WaterLevels]
)
def read_waterlevels_manual(pointid: str = None, db: Session = Depends(get_db)):
    q = read_waterlevels_manual_query(pointid, db)
    return paginate(q)


@router.get(
    "/pressure", response_model=Page[waterlevels.WaterLevelsContinuous_Pressure]
)
@router.get(
    "/pressure/limit-offset",
    response_model=LimitOffsetPage[waterlevels.WaterLevelsContinuous_Pressure],
)
def read_waterlevels_pressure(pointid: str = None, db: Session = Depends(get_db)):
    q = read_waterlevels_pressure_query(pointid, db)
    return paginate(q)


@router.get(
    "/acoustic", response_model=Page[waterlevels.WaterLevelsContinuous_Acoustic]
)
@router.get(
    "/acoustic/limit-offset",
    response_model=LimitOffsetPage[waterlevels.WaterLevelsContinuous_Acoustic],
)
def read_waterlevels_acoustic(pointid: str = None, db: Session = Depends(get_db)):
    q = read_waterlevels_acoustic_query(pointid, db)
    return paginate(q)
