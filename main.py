from fastapi import FastAPI, File, UploadFile, Response, status, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from typing import Annotated
import aiofiles 
import calendar
import time
from liveness import checkLiveness;
app = FastAPI()

@app.get('/')
async def root():
    return {'message': 'Hello World!'}

@app.post("/liveness", status_code=200)
async def create_upload_file(file: UploadFile, response: Response):
    ts = getTimestamp();
    ext = getExtension(file.content_type);
    if (ext == 'jpg'):
        file_name = "{fname}.{ext}".format(fname = ts, ext = ext)
        image_dir = 'images/'
        image_path = image_dir+file_name;
        async with aiofiles.open(image_path, 'wb') as out_file:
            while content := await file.read(1024):  # async read chunk
                await out_file.write(content) 
            pred = checkLiveness(image_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f'File {file.filename} has unsupported extension type',
        )   
    return pred


def getTimestamp():
    # Current GMT time in a tuple format
    current_GMT = time.gmtime()

    # ts stores timestamp
    ts = calendar.timegm(current_GMT)
    return ts;

def getExtension(content_type):
    switch={
      'image/jpeg':'jpg',
      }
    return switch.get(content_type,"Invalid input")
print(getExtension('image/jpeg'))