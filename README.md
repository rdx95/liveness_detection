  

# Liveness API


API to detect liveness of an image

  

## How To Setup

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

*Note: Additional requirements*


```

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y

```

Create ```.env``` file with the following variabales
```
DO_ACCESS_KEY_ID
DO_SECRET_ACCESS_KEY
DO_SPACES_NAME
DO_SPACES_REGION
DB_URI
DB_NAME
```
## To Run

run using gunicorn
```
gunicorn main:app -k uvicorn.workers.UvicornWorker
```
```
gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 app:app

```


To kill gunicorn process
```
pkill gunicorn
```


https://www.slingacademy.com/article/deploying-fastapi-on-ubuntu-with-nginx-and-lets-encrypt/