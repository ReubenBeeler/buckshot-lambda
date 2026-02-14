from dotenv import load_dotenv
for path in ('.env', '.env.public'):
	load_dotenv(path, override=(__name__ == '__main__'))

import os
import sys
import json
import boto3
import tempfile
from PIL import Image
from itertools import batched
from mypy_boto3_s3 import S3Client

from lib.print_return import print_return
from lib.require_env import require_env

def check_AWS_response(response:dict, err_msg:str) -> None:
	status_code:int = response['ResponseMetadata']['HTTPStatusCode']
	if status_code // 100 != 2:
		raise Exception(f'ERROR: AWS responded with HTTPStatusCode {status_code}: {err_msg}')

def split(s: str) -> list[str]:
	return [e.strip() for e in s.split(', ')]

env_var_names: list[str] = split('''
	AWS_BUCKET, UNVALIDATED_IMAGE_PATH, VALIDATED_IMAGE_PATH, \
	VALIDATED_METADATA_PATH, CLASSIFICATION_SCORE_THRESHOLD, \
	CLASSIFICATION_BLACKLIST
	''')

@require_env(*env_var_names)
@print_return(prefix='Lambda returned:\n' + ' '*4, indent=' '*4, to_str=lambda ret: json.dumps(ret, indent=4))
def lambda_handler(event: dict, context) -> dict:
	try:
		AWS_BUCKET, UNVALIDATED_IMAGE_PATH, VALIDATED_IMAGE_PATH, \
		VALIDATED_METADATA_PATH, CLASSIFICATION_SCORE_THRESHOLD, \
		CLASSIFICATION_BLACKLIST = (os.environ[name] for name in env_var_names)
		
		CLASSIFICATION_SCORE_THRESHOLD = float(CLASSIFICATION_SCORE_THRESHOLD)
		blacklist: set[str] = set(CLASSIFICATION_BLACKLIST.split(':'))

		path_names = split('UNVALIDATED_IMAGE_PATH, VALIDATED_IMAGE_PATH, VALIDATED_METADATA_PATH')
		paths: tuple[str, ...] = tuple(os.environ[name] for name in path_names)

		for i, path_i in enumerate(paths):
			for j, path_j in enumerate(paths):
				if i != j and path_i.startswith(path_j):
					raise Exception(f'ERROR: the following S3 object paths should be orthogonal: {", ".join(path_names)}')

		s3_client: S3Client = boto3.client('s3')

		print(f"Listing images from s3://{AWS_BUCKET}/{UNVALIDATED_IMAGE_PATH}...")

		# List all images in the unvalidated path
		response:dict = s3_client.list_objects_v2(
			Bucket=AWS_BUCKET,
			Prefix=UNVALIDATED_IMAGE_PATH,
		) # pyright: ignore[reportAssignmentType]

		zero_response:dict = {
				'statusCode': 200,
				'message': 'No images to validate!',
				'total_count': 0,
				'valid_count': 0,
				'invalid_count': 0,
			}

		if 'Contents' not in response or len(response['Contents']) == 0:
			return zero_response

		keys: list[str] = [obj['Key'] for obj in response['Contents']]
		keys = [key for key in keys if s3_client.head_object(Bucket=AWS_BUCKET, Key=key)['ContentType'].startswith('image/')]
		key_suffixes: list[str] = [key[len(UNVALIDATED_IMAGE_PATH):] for key in keys]

		num_images: int = len(key_suffixes)

		if num_images == 0:
			return zero_response

		print(f"Found {num_images} images to validate.")

		print(f'Loading SpeciesNet...')
		from model import model
	
		max_batch_size = 8  # Adjust based on Lambda memory configuration
		print(f'Beginning batch-processing with {max_batch_size=}')
		batched_key_suffixes = tuple(batched(key_suffixes, max_batch_size))
		num_batches: int = len(batched_key_suffixes)

		valid_count = 0
		for batch, batch_key_suffixes in enumerate(batched_key_suffixes):
			batch_size:int = len(batch_key_suffixes)
			print(f'Starting batch {batch+1} out of {num_batches} with batch_size={batch_size}')

			print(f'  - copying batch from s3 to /tmp...')
			with tempfile.TemporaryDirectory() as batch_dirname:
				def get_image_path(i: int) -> str: return f'{batch_dirname}/{i}'

				for i, key_suffix in enumerate(batch_key_suffixes):
					key=f'{UNVALIDATED_IMAGE_PATH}{key_suffix}'
					response = s3_client.get_object(Bucket=AWS_BUCKET, Key=key) # pyright: ignore[reportAssignmentType]
					check_AWS_response(response, f'failed to get object at {key}')

					with open(get_image_path(i), 'wb') as image_file:
						image_file.write(response['Body'].read())
				del i, key_suffix
			
				instances = [{
					'filepath': get_image_path(i),
					'country': 'USA', # TODO get from object metadata
					'admin1_region': 'UT'
				} for i in range(batch_size)]

				print(f'  - detecting...')
				predictions_json:dict|None = model.detect(
					instances_dict={'instances': instances},
					run_mode='multi_thread', # TODO test this on AWS Lambda
				)

				assert predictions_json is not None

				predictions:list[dict] = predictions_json['predictions']

				print(f'  - classifying...')
				for i, prediction in enumerate(predictions):
					animal_detections: list[dict] = [
						detection for detection in prediction['detections']
						if detection["label"] == "animal" # and detection["conf"] >= DETECTION_CONFIDENCE_THRESHOLD
					]

					validated_animals:list[dict] = []

					if len(animal_detections) > 0:
						with tempfile.TemporaryDirectory() as tmp_dir_path:
							def get_cropped_image_path(i: int) -> str:
								return f'{tmp_dir_path}/crop_{i}.jpg'
							
							bboxes:list[list[float]] = [detection['bbox'] for detection in animal_detections]
							
							with Image.open(prediction['filepath']) as img:
								img_w, img_h = img.size
								for j, bbox in enumerate(bboxes):
									# bbox is [x_min, y_min, width, height] in normalized coords
									bx, by, bw, bh = bbox

									# Convert to pixel coordinates
									left   = int(bx * img_w)
									upper  = int(by * img_h)
									right  = int((bx + bw) * img_w)
									lower  = int((by + bh) * img_h)
									
									pad_frac = 0.15 # play with this
									pad_x = int(bw * img_w * pad_frac)
									pad_y = int(bh * img_h * pad_frac)
									left   = max(0, left - pad_x)
									upper  = max(0, upper - pad_y)
									right  = min(img_w, right + pad_x)
									lower  = min(img_h, lower + pad_y)

									# Crop and save temporarilymulti_classify.py
									crop = img.crop((left, upper, right, lower))
									with open(get_cropped_image_path(j), 'wb') as file:
										crop.save(file.name)

							result:dict = model.classify(
								folders=[tmp_dir_path],
								country='USA',
								admin1_region='UT',
								batch_size=len(animal_detections)
							) # pyright: ignore[reportAssignmentType]
						
						for j, prediction in enumerate(result["predictions"]):
							classifications:dict = prediction['classifications']

							# ranked by best to worst, so grab the first!
							classification:str = classifications['classes'][0]
							score:float = classifications['scores'][0]
						
							if classification not in blacklist and score >= CLASSIFICATION_SCORE_THRESHOLD:
								_, _, _, _, genus, species, common_name = classification.split(';')
								scientific_name:str = f'{genus} {species}'.capitalize()
								common_name:str = common_name.capitalize()
								validated_animals.append({
									'classification': classification,
									'common_name': common_name,
									'scientific_name': scientific_name,
									'score': score,
									'bbox': bboxes[j]
								})
					
					key_suffix: str = batch_key_suffixes[i]
					if len(validated_animals) > 0:
						valid_count += 1
						# Metadata is too close to the 2KB limit, so let's create a .json file

						key:str = f"{VALIDATED_METADATA_PATH}{key_suffix}.json"
						response = s3_client.put_object(
							Bucket=AWS_BUCKET,
							Key=key,
							Body=json.dumps(validated_animals, indent=4),
							ContentType='application/json',
							StorageClass='INTELLIGENT_TIERING',
						) # pyright: ignore[reportAssignmentType]
						check_AWS_response(response, f'failed to put object at {key}')
						
						# Upload the validated image
						key:str = f"{VALIDATED_IMAGE_PATH}{key_suffix}"
						with open(get_image_path(i), 'rb') as image_file:
							response = s3_client.put_object(
								Bucket=AWS_BUCKET,
								Key=key,
								Body=image_file,
								ContentType='image/jpg',
								StorageClass='INTELLIGENT_TIERING',
							) # pyright: ignore[reportAssignmentType]
							check_AWS_response(response, f'failed to put object at {key}')
					
					# Delete the old (unvalidate) image
					key = f"{UNVALIDATED_IMAGE_PATH}{key_suffix}"
					response = s3_client.delete_object(
						Bucket=AWS_BUCKET,
						Key=key,
					) # pyright: ignore[reportAssignmentType]
					check_AWS_response(response, f'failed to delete object at {key}')

		return {
			'statusCode': 200,
			'message': 'Successfully processed all images!',
			'total_count': len(key_suffixes),
			'valid_count': valid_count,
			'invalid_count': len(key_suffixes) - valid_count,
		}

	except Exception as e:
		import traceback
		traceback.print_exc()
		return {
			'statusCode': 500,
			'stackTraceString': traceback.format_exc(),
			'errorMessage': str(e),
			'errorType': str(type(e)),
			'stackTrace': traceback.format_stack(),
		}

if __name__ == '__main__':
	import sys
	import argparse

	args = sys.argv[1:]
	parser = argparse.ArgumentParser(sys.argv[0], description='Process images from S3 using SpeciesNet')
	parsed = parser.parse_args(args)

	# Run the Lambda handler
	lambda_handler({}, None)