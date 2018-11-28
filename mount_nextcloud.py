import subprocess
 
# from deep-nextcloud into the container
command = (['rclone', 'copy', 'nextcloud-plants:/plants_images', '/srv/plant-classification-tf-train/data/raw'])
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
output, error = result.communicate()



command = (['rclone', 'copy', 'nextcloud-plants:/data_splits', '/srv/plant-classification-tf-train/data/data_splits'])
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
output, error = result.communicate()
