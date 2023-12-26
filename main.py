from fastapi import FastAPI, File, UploadFile, Response, status, HTTPException, Form, HTTPException, Security, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
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

SERVICE_API_KEY = os.getenv('SERVICE_API_KEY')
api_key_header = APIKeyHeader(name="apikey")

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    print(SERVICE_API_KEY)
    if api_key_header == SERVICE_API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )

class Feedback(BaseModel):
    file_name: str
    classification: bool


mongo_db = mongo.MongoDBClient(os.getenv('DB_URI'), os.getenv('DB_NAME')) # type: ignore
spaces_instance = spaces.DigitalOceanSpacesClient(
    os.getenv('DO_ACCESS_KEY_ID'),
    os.getenv('DO_SECRET_ACCESS_KEY'),
    os.getenv('DO_SPACES_NAME'),
    os.getenv('DO_SPACES_REGION')
)


@app.get("/")
async def root(api_key: str = Security(get_api_key)):
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


@app.post("/beta/detect", status_code=200)
async def detect_liveness(
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
                "result": True if classification == "0" else False
            }
            insert_result = mongo_db.create_document("dataset-meta", payload)
            upload_result = spaces_instance.upload_file(image_path, file_name)
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File {image.filename} has unsupported extension type",
            )
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


@app.post("/liveness/feedback")
async def getFeedback(body: Feedback, response: Response):
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
