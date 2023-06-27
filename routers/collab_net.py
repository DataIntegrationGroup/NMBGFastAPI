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
import csv
import io
import json
import os
import threading
import time

from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from sqlalchemy.testing import in_
from starlette.requests import Request
from starlette.responses import StreamingResponse, FileResponse
from starlette.templating import Jinja2Templates

import models
import schemas
from crud import (
    public_release_filter,
    read_waterlevels_manual_query,
    get_waterlevels_csv_stream,
)
from dependencies import get_db
from routers import csv_response, json_response

router = APIRouter(prefix="/collabnet", tags=["collabnet"])
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


@router.get("/map")
def map_view(request: Request, db: Session = Depends(get_db)):
    # ls = get_locations(db)
    # def make_point(loc, well):
    #     return {
    #         "type": "Feature",
    #         "properties": {"name": f"Point {loc.PointID}"},
    #         "geometry": loc.geometry,
    #     }

    return templates.TemplateResponse(
        "collabnet_map_view.html",
        {
            "request": request,
            "center": {"lat": 34.5, "lon": -106.0},
            "zoom": 6,
            "data_url": "/collabnet/locations",
            "nlocations": get_nlocations(db),
        },
    )


@router.get("/waterlevels/csv")
async def read_waterlevels(db: Session = Depends(get_db)):
    # if not os.path.isfile("waterlevels.csv"):
    #     txt = get_waterlevels_csv(db)
    #     with open("waterlevels.csv", "w") as fp:
    #         fp.write(txt)
    #
    # return FileResponse("waterlevels.csv")
    stream = get_waterlevels_csv_stream(db)
    response = StreamingResponse(stream, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=waterlevels.csv"
    return response


# def get_waterlevels_csv_old(db):
#     q = db.query(models.Location)
#     q = q.join(models.ProjectLocations)
#     q = q.filter(models.ProjectLocations.ProjectName == "Water Level Network")
#     q = public_release_filter(q)
#     locations = q.all()
#
#     rows = [
#         (
#             "PointID",
#             "DateMeasured",
#             "DepthToWaterBGS",
#             "MeasurementMethod",
#             "DataSource",
#             "MeasuringAgency",
#             "LevelStatus",
#             "DataQuality",
#         )
#     ]
#
#     stream = io.StringIO()
#     writer = csv.writer(stream)
#     n = len(locations)
#     for i, l in enumerate(locations):
#         print(f"getting waterlevels for {i}/{n}, {l.PointID}")
#         waterlevels = read_waterlevels_manual_query(l.PointID, db)
#         for wi in waterlevels:
#             rows.append(
#                 (
#                     l.PointID,
#                     wi.DateMeasured,
#                     wi.DepthToWaterBGS,
#                     wi.measurement_method,
#                     wi.data_source,
#                     wi.MeasuringAgency,
#                     wi.level_status,
#                     wi.data_quality,
#                 )
#             )
#     writer.writerows(rows)
#     return stream.getvalue()


@router.get("/locations/csv")
def read_locations_csv(db: Session = Depends(get_db)):
    stream = io.StringIO()
    writer = csv.writer(stream)
    ls = get_locations(db)
    writer.writerow(
        (
            "index",
            "PointID",
            "Latitude",
            "Longitude",
            "Elevation (ft asl)",
            "WellDepth (ft bgs)",
        )
    )
    for i, (l, w) in enumerate(ls):
        lon, lat = l.lonlat
        row = (
            i + 1,
            l.PointID,
            lat,
            lon,
            f"{l.Altitude :0.2f}",
            f"{w.WellDepth or 0:0.2f}",
        )
        writer.writerow(row)

    return csv_response("locations", stream.getvalue())


@router.get("/locations/geojson")
def read_locations_geojson(db: Session = Depends(get_db)):
    ls = get_locations(db)
    content = locations_geojson(ls)
    return json_response("locations", content)

    # stream = io.StringIO()
    # stream.write(json.dumps(content))
    # response = StreamingResponse(
    #     iter([stream.getvalue()]), media_type="application/json"
    # )
    # response.headers["Content-Disposition"] = "attachment; filename=locations.json"
    # return response


@router.get("/locations", response_model=schemas.LocationFeatureCollection)
def read_locations_geojson(db: Session = Depends(get_db)):
    ls = get_locations(db)
    content = locations_geojson(ls)
    return content


def get_nlocations(db: Session = Depends(get_db)):
    q = get_locations_query(db)
    return q.count()


def get_locations(db: Session = Depends(get_db)):
    q = get_locations_query(db)
    try:
        return q.all()
    except Exception as e:
        return []


def get_locations_query(db):
    q = db.query(models.Location, models.Well)
    q = q.join(models.ProjectLocations)
    q = q.join(models.Well)
    q = q.filter(models.ProjectLocations.ProjectName == "Water Level Network")
    q = public_release_filter(q)
    q = q.order_by(models.Location.PointID)
    return q


def locations_geojson(locations):
    def togeojson(l, w):
        return {
            "type": "Feature",
            "properties": {
                "name": l.PointID,
                "well_depth": {"value": w.WellDepth, "units": "ft"},
            },
            "geometry": l.geometry,
        }

    content = {
        "features": [togeojson(*l) for l in locations],
    }

    return content


# def waterlevels_loop():
#     evt = threading.Event()
#     while 1:
#         if os.path.isfile("waterlevels.csv"):
#             s = os.stat("waterlevels.csv")
#             if time.time() - s.st_mtime < 60 * 60 * 24:
#                 continue
#
#         db = next(get_db())
#         txt = get_waterlevels_csv(db)
#         with open("waterlevels.csv", "w") as fp:
#             fp.write(txt)
#
#         evt.wait(1)
#
#
# t = threading.Thread(target=waterlevels_loop)
# t.start()


# ============= EOF =============================================
