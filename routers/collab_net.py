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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.templating import Jinja2Templates

import models
import schemas
from crud import public_release_filter, read_waterlevels_manual_query
from dependencies import get_db

router = APIRouter(prefix="/collabnet", tags=["collabnet"])
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


@router.get("/map")
def map_view(request: Request, db: Session = Depends(get_db)):
    ls = get_locations(db)

    def make_point(i):
        return {
            "type": "Feature",
            "properties": {"name": f"Point {i.PointID}"},
            "geometry": i.geometry,
        }

    return templates.TemplateResponse(
        "map_view.html",
        {
            "request": request,
            "center": {"lat": 34.5, "lon": -106.0},
            "zoom": 7,
            "points": {
                "type": "FeatureCollection",
                "features": [make_point(i) for i in ls],
            }
            # "points": {
            #     'type': 'FeatureCollection',
            #     'features': [
            #     {'type': 'Feature',
            #      'geometry': {'type': 'Point', 'coordinates': [-106+i, 34.5+i]}}
            #      for i in range(10)
            #      ]
            # }
        },
    )


@router.get("/waterlevels/csv")
def read_waterlevels(db: Session = Depends(get_db)):
    q = db.query(models.Location)
    q = q.join(models.ProjectLocations)
    q = q.filter(models.ProjectLocations.ProjectName == "Water Level Network")
    q = public_release_filter(q)
    locations = q.all()

    rows = [
        (
            "PointID",
            "DateMeasured",
            "DepthToWaterBGS",
            "MeasurementMethod",
            "DataSource",
            "MeasuringAgency",
            "LevelStatus",
            "DataQuality",
        )
    ]

    stream = io.StringIO()
    writer = csv.writer(stream)
    n = len(locations)
    for i, l in enumerate(locations):
        print(f"getting waterlevels for {i}/{n}, {l.PointID}")
        waterlevels = read_waterlevels_manual_query(l.PointID, db)
        for wi in waterlevels:
            rows.append(
                (
                    l.PointID,
                    wi.DateMeasured,
                    wi.DepthToWaterBGS,
                    wi.measurement_method,
                    wi.data_source,
                    wi.MeasuringAgency,
                    wi.level_status,
                    wi.data_quality,
                )
            )
    writer.writerows(rows)

    # stream.write('\n'.join([','.join(map(str, r)) for r in rows]))
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=waterlevels.csv"
    return response


@router.get("/locations/geojson")
def read_locations_geojson(db: Session = Depends(get_db)):
    ls = get_locations(db)
    content = locations_geojson(ls)

    stream = io.StringIO()
    stream.write(json.dumps(content))
    response = StreamingResponse(
        iter([stream.getvalue()]), media_type="application/json"
    )
    response.headers["Content-Disposition"] = "attachment; filename=locations.json"
    return response


@router.get("/locations", response_model=schemas.LocationFeatureCollection)
def read_locations_geojson(db: Session = Depends(get_db)):
    ls = get_locations(db)
    content = locations_geojson(ls)
    return content


def get_locations(db: Session = Depends(get_db)):
    q = db.query(models.Location, models.Well)
    q = q.join(models.ProjectLocations)
    q = q.join(models.Well)
    q = q.filter(models.ProjectLocations.ProjectName == "Water Level Network")
    q = public_release_filter(q)
    try:
        return q.all()
    except Exception as e:
        return []


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


# ============= EOF =============================================
