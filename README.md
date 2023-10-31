  

# Liveness API


API to detect liveness of an image

  

## How To Run

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

*Note: Additional requirements*
```

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y

```

###

run using gunicorn
```
gunicorn main:app -k uvicorn.workers.UvicornWorker
```


To kill gunicorn process
```
pkill gunicorn
```