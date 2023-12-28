from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Response,
    status,
    HTTPException,
    Form,
    HTTPException,
    Security,
    FastAPI,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from bson import json_util
from pydantic import BaseModel, json
from typing import Annotated
import aiofiles
import calendar
import time
import os
import json
from liveness import checkLiveness, classifier
from model import mongo
from spaces import spaces
import os
from dotenv import load_dotenv


load_dotenv()

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICE_API_KEY = os.getenv("SERVICE_API_KEY")
api_key_header = APIKeyHeader(name="apikey")


def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header == SERVICE_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )


class Feedback(BaseModel):
    file_name: str
    classification: bool


mongo_db = mongo.MongoDBClient(os.getenv("DB_URI"), os.getenv("DB_NAME"))  # type: ignore
spaces_instance = spaces.DigitalOceanSpacesClient(
    os.getenv("DO_ACCESS_KEY_ID"),
    os.getenv("DO_SECRET_ACCESS_KEY"),
    os.getenv("DO_SPACES_NAME"),
    os.getenv("DO_SPACES_REGION"),
)


@app.get("/")
async def root():
    return {"message": "welcome to liveness detection service!"}


@app.post("/liveness", status_code=200)
async def create_upload_file(file: UploadFile, response: Response):
    ts = getTimestamp()
    ext = getExtension(file.content_type)
    if ext == "jpg":
        file_name = "{fname}.{ext}".format(fname=ts, ext=ext)
        image_dir = "images/"
        image_path = image_dir + file_name
        async with aiofiles.open(image_path, "wb") as out_file:
            while content := await file.read(1024):  # async read chunk
                await out_file.write(content)
            prediction = checkLiveness(image_path)
            classification = classifier(prediction)
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File {file.filename} has unsupported extension type",
        )
    return {
        "predictions": json.dumps(prediction.tolist()),
        "classification": classification,
        "result": True if classification == "0" else False,
        "filename": file_name,
    }


@app.post("/beta/detect")
async def detect_liveness(
    response: Response,
    apikey: Annotated[str | None, Header()] = None,
    api_key: str = Security(get_api_key),
    employee_id: str = Form(...),
    company_id: str = Form(...),
    client_id: str = Form(...),
    shift_name: str = Form(...),
    punch_type: str = Form(...),
    device_make: str = Form(...),
    device_model: str = Form(...),
    camera: str = Form(...),
    image: UploadFile = File(...),
):
    try:
        ts = getTimestamp()
        ext = getExtension(image.content_type)
        if ext == "jpg":
            file_name = "{fname}.{ext}".format(fname=ts, ext=ext)
            image_dir = "images/"
            image_path = image_dir + file_name

            async with aiofiles.open(image_path, "wb") as out_file:
                while content := await image.read(1024):  # async read chunk
                    await out_file.write(content)
                prediction = checkLiveness(image_path)
                classification = classifier(prediction)

            payload = {
                "created_at": time.ctime(),
                "employee_id": employee_id,
                "company_id": company_id,
                "client_id": client_id,
                "shift_name": shift_name,
                "punch_type": punch_type,
                "device_make": device_make,
                "device_model": device_model,
                "camera": camera,
                "image_path": file_name,
                "classification": classification,
                "result": True if classification == "0" else False,
                "is_classified": False,
            }
            insert_result = mongo_db.create_document("dataset-meta", payload)
            upload_result = spaces_instance.upload_file(image_path, file_name)
        else:
            response.status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            return {"detail": f"File {image.filename} has unsupported extension type"}
        return {
            "predictions": json.dumps(prediction.tolist()),
            "classification": classification,
            "result": True if classification == "0" else False,
            "filename": file_name,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server error",
        )


@app.get("/beta/listallfiles")
async def getAllImages(per_page:int, page:int,response: Response):
    try:
        pipeline = [
            {"$match": {"is_classified": False}},
            {
                "$facet": {
                    "data": [
                        {
                            "$skip": (page - 1) * per_page,
                        },
                        {
                            "$limit": per_page,
                        },
                        {
                            "$project": {
                                "employee_id": 1,
                                "company_id": 1,
                                "client_id": 1,
                                "shift_name": 1,
                                "punch_type": 1,
                                "camera": 1,
                                "is_classified": 1,
                                "result": 1,
                                "image_path": 1,
                            },
                        },
                    ],
                    "meta": [
                        {
                            "$count": "count",
                        },
                    ],
                }
            }
        ]
        image_data = mongo_db.aggregate_pipeline(
            "dataset-meta", pipeline
        )
        parsed_data = parse_json(image_data)
        return parsed_data[0]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server error",
        )


@app.get("/beta/getimage")
async def getImage(file_name:str, response:Response):
    file_stream = spaces_instance.download_file_from_space(file_name)
    if file_stream:
        return StreamingResponse(file_stream, media_type='application/octet-stream', headers={'Content-Disposition': f'attachment; filename="{file_name}"'})
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.put("/beta/classify")
async def classifyImage(file_name:str,classification:str, response:Response):
    try:
        if classification == 'real' or classification == 'fake':
            image_data = mongo_db.read_document("dataset-meta",{'image_path':file_name, 'is_classified':False})
            if image_data != None:
                if (classification == 'real'):
                    dest_path = 'real/{}'.format(file_name)
                else :
                    dest_path = 'fake/{}'.format(file_name)

                is_file_moved = spaces_instance.move_file_within_space(file_name,dest_path)
                if is_file_moved:    
                    update_record = mongo_db.update_document("dataset-meta",{'image_path':file_name},{"is_classified":True})
                return {
                    'detail':"file moved successfully"
                } 
            else :
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"detail": f"File Not Found or already classified"}
        else :
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"detail": "Invalid Classification data"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server error",
        )

@app.post("/liveness/feedback")
async def getFeedback(body: Feedback, response: Response):
    try:
        image_dir = "images/"
        file_name = body.file_name
        dir_real = "images/real/"
        dir_fake = "images/fake/"
        image_path = image_dir + file_name
        if os.path.exists(image_path):
            if body.classification == True:
                os.rename(image_path, dir_real + file_name)
            else:
                os.rename(image_path, dir_fake + file_name)
            return {"message": "classification success"}
        else:
            raise HTTPException(
                status_code=404,
                detail="File Not Found",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server error",
        )

def getTimestamp():
    # Current GMT time in a tuple format
    current_GMT = time.gmtime()

    # ts stores timestamp
    ts = calendar.timegm(current_GMT)
    return ts


def getExtension(content_type):
    switch = {
        "image/jpeg": "jpg",
    }
    return switch.get(content_type, "Invalid input")


def parse_json(data):
    return json.loads(json_util.dumps(data))
