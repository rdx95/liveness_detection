from fastapi import FastAPI, File, UploadFile, Response, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from typing import Annotated
import aiofiles
import calendar
import time
import os
import json
from liveness import checkLiveness, classifier

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Feedback(BaseModel):
    file_name: str
    classification: bool


@app.get("/")
async def root():
    return {"message": "Hello World!"}


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
        "result": True if classification == '0' else False,
        "filename": file_name,
    }


@app.post("/liveness/feedback")
async def getFeedback(body: Feedback, response: Response):
    image_dir = "images/"
    file_name = body.file_name
    dir_real = "images/real/"
    dir_fake = "images/fake/"
    image_path = image_dir + file_name
    if body.classification == True:
        os.rename(image_path, dir_real + file_name)
    else:
        os.rename(image_path, dir_fake + file_name)
    return {"message": "classification success"}


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
