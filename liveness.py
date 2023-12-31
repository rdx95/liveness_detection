import numpy as np
import cv2
import torch
import seaborn as sns
import pandas as pd
import albumentations as albu
from albumentations.pytorch.transforms import ToTensorV2
from iglovikov_helper_functions.dl.pytorch.utils import tensor_from_rgb_image
from iglovikov_helper_functions.utils.image_utils import load_rgb
from datasouls_antispoof.pre_trained_models import create_model
from datasouls_antispoof.class_mapping import class_mapping
def checkLiveness(image_path):
    model = create_model("tf_efficientnet_b3_ns")
    model.eval();

    image_replay = load_rgb(image_path)

    transform = albu.Compose([albu.PadIfNeeded(min_height=500, min_width=500),
                          albu.CenterCrop(height=500, width=500),
                          albu.Normalize(p=1),
                          albu.pytorch.ToTensorV2(p=1)], p=1)

    with torch.no_grad():
        prediction = model(torch.unsqueeze(transform(image=image_replay)['image'], 0)).numpy()[0]
    return prediction

def classifier(prediction):
    prediction_list = prediction.tolist();
    classification = str(np.argmax(prediction))
    return classification