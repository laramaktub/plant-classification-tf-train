import json
import os
import tempfile

import numpy as np
import requests
import subprocess


import plant_classification.model_utils as utils
from plant_classification import my_utils

from plant_classification.my_utils import train_model
from plant_classification.data_utils import data_splits, meanRGB


homedir = os.path.dirname(os.path.realpath(__file__))

print(homedir)
# Loading label names and label info files
synsets = np.genfromtxt(os.path.join(homedir, '..', 'data', 'data_splits', 'synsets.txt'), dtype='str', delimiter='/n')
try:
    synsets_info = np.genfromtxt(os.path.join(homedir, 'model_files', 'data', 'info.txt'), dtype='str', delimiter='/n')
except:
    synsets_info = np.array(['']*len(synsets))
assert synsets.shape == synsets_info.shape, """
Your info file should have the same size as the synsets file.
Blank spaces corresponding to labels with no info should be filled with some string (eg '-').
You can also choose to remove the info file."""

# Load training info
info_files = os.listdir(os.path.join(homedir, 'training_info'))
info_file_name = [i for i in info_files if i.endswith('.json')][0]
info_file = os.path.join(homedir, 'training_info', info_file_name)
with open(info_file) as datafile:
    train_info = json.load(datafile)
mean_RGB = train_info['augmentation_params']['mean_RGB']
output_dim = train_info['training_params']['output_dim']

# Load net weights
weights_files = os.listdir(os.path.join(homedir, 'training_weights'))
weights_file_name = [i for i in weights_files if i.endswith('.npz')][0]
test_func = utils.load_model(os.path.join(homedir, 'training_weights', weights_file_name), output_dim=output_dim)

def catch_error(f):
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            raise e
            return {"status": "error",
                    "predictions": []}
    return wrap


@catch_error
def mount_nextcloud():

	# from deep-nextcloud into the container
	command = (['rclone', 'copy', 'ncplants:/plants_images', '/srv/plant-classification-tf-train/data/raw'])
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = result.communicate()
        print("Output --> ", output)
        print("Error --> ", error)

	command = (['rclone', 'copy', 'ncplants:/data_splits', '/srv/plant-classification-tf-train/data/data_splits'])
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = result.communicate()
        print("Output (data_splits) --> ", output)
        print("Error (data_splits)--> ", error)
   
        return output, error

@catch_error
def predict_url(urls, test_func=test_func):
    if not isinstance(urls, list):
        urls = [urls]

    pred_lab, pred_prob = my_utils.single_prediction(test_func,
                                                     im_list=urls,
                                                     aug_params={'mean_RGB': mean_RGB,
                                                                 'filemode':'url'})
    return format_prediction(pred_lab, pred_prob)


@catch_error
def predict_file(filenames, test_func=test_func):
    if not isinstance(filenames, list):
        filenames = [filenames]

    pred_lab, pred_prob = my_utils.single_prediction(test_func,
                                                    im_list=filenames,
                                                    aug_params={'mean_RGB':
                                                                mean_RGB, 'filemode':'local'})
    return format_prediction(pred_lab, pred_prob)


@catch_error
def predict_data(images, test_func=test_func):
    if not isinstance(images, list):
        images = [images]

    filenames = []
    for image in images:
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(image)
        f.close()
        filenames.append(f.name)

    try:
        pred_lab, pred_prob = my_utils.single_prediction(test_func,
                                                        im_list=filenames,
                                                        aug_params={'mean_RGB':
                                                                    mean_RGB, 'filemode':'local'})
    except Exception as e:
        raise e
    finally:
        for f in filenames:
            os.remove(f)
    return format_prediction(pred_lab, pred_prob)


@catch_error
def train(user_conf):
	
        mount_nextcloud()
        nepochs=int(user_conf["nepochs"])
	bsize=int(user_conf["bsize"])
     
	im_dir = '/srv/plant-classification-tf-train/data/raw/'  # absolute path to file_dir
	X_train, y_train, X_val, y_val, metadata, tags = data_splits(im_dir)

	mean_RGB, std_RGB = meanRGB(X_train)
	net_params = {'output_dim': len(metadata), 'batchsize': bsize, 'num_epochs': nepochs} #network parameters
	aug_params = {'tags': tags, 'mean_RGB': mean_RGB} #data augmentation parameters
	train_model(X_train, y_train, X_val, y_val, net_params=net_params, aug_params=aug_params)
        print("llega aqui 3")
	return user_conf


def format_prediction(labels, probabilities):
    d = {
        "status": "ok",
         "predictions": [],
    }

    for label_id, prob in zip(labels, probabilities):
        name = synsets[label_id]

        pred = {
            "label_id": label_id,
            "label": name,
            "probability": float(prob),
            "info": {
                "links": [{"link": 'Google images', "url": image_link(name)},
                          {"link": 'Wikipedia', "url": wikipedia_link(name)}],
                'metadata': synsets_info[label_id],
            },
        }
        d["predictions"].append(pred)
    return d


def image_link(pred_lab):
    """
    Return link to Google images
    """
    base_url = 'https://www.google.es/search?'
    params = {'tbm':'isch','q':pred_lab}
    link = base_url + requests.compat.urlencode(params)
    return link


def wikipedia_link(pred_lab):
    """
    Return link to wikipedia webpage
    """
    base_url = 'https://en.wikipedia.org/wiki/'
    link = base_url + pred_lab.replace(' ', '_')
    return link


def metadata():
    d = {
        "author": None,
        "description": None,
        "url": None,
        "license": None,
        "version": None,
    }
    return d
