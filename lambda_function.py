import os
import base64

# TODO move validation over to raspi -- just use Lambda for speciesnet and that's it
blacklist: set[str] = {
	"f1856211-cfb7-4a5b-9158-c0f72fd09ee6;;;;;;blank",
	"e2895ed5-780b-48f6-8a11-9e27cb594511;;;;;;vehicle",
	"990ae9dd-7a59-4344-afcb-1b7b21368000;mammalia;primates;hominidae;homo;sapiens;human",
	"3d80f1d6-b1df-4966-9ff4-94053c7a902a;mammalia;carnivora;canidae;canis;familiaris;domestic dog",
}

def lambda_handler(event:dict, context) -> dict:
	try:
		if event == {'test': True}:
			with open('test.png', 'rb') as image_file:
				image_bytes: bytes = image_file.read()
		elif len(event) == 1 and 'image' in event:
			image_b64: str = event['image']
			image_bytes: bytes = base64.b64decode(image_b64.encode('utf-8'))
		else:
			raise Exception(f'unknown event format', event)

		fd: int = os.memfd_create('image') # name is unimportant
		
		ret: int = os.write(fd, image_bytes)
		if ret < 0: raise Exception(f'failed to write image_bytes to in-memory file descriptor: returned {ret}')

		ret: int = os.lseek(fd, 0, os.SEEK_SET)
		if ret: raise Exception(f'failed to lseek image fd to 0 offset: returned {ret}')

		filepath:str = f"/proc/self/fd/{fd}"

		from speciesnet import SpeciesNet
		model = SpeciesNet(
			'kaggle:google/speciesnet/pyTorch/v4.0.1a', # or v4.0.1b
			components='all',
			geofence=True,
		)
		
		instances_dict = {
			'instances': [{'filepath': filepath, 'country': 'USA', 'admin1_region': 'UT'}]
		}

		# TODO consider changing run_mode and batch_size if using more than one image
		predictions_json = model.predict(
			instances_dict=instances_dict,
			run_mode='single_thread',
			batch_size=1,
			progress_bars=False,
			# predictions_json=output_path,
		)
		assert predictions_json is not None # output path not specified

		data: dict = predictions_json["predictions"][0]
		print(f'data:\n{data}')
		classification: str = data['prediction']
		score: float = data['prediction_score']
		source: str = data['prediction_source']

		_, _, _, _, genus, species, common_name = classification.split(';')

		species.capitalize()
		scientific_name = f'{genus} {species}'.capitalize()
		common_name = common_name.capitalize()
		
		return {
			'statusCode': 200,
			'valid': classification not in blacklist,
			'prediction': {
				'classification': classification,
				'common_name': common_name,
				'scientic_name': scientific_name,
				'score': score,
				'source': source,
			}
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
	finally:
		try:
			if 'fd' in locals():
				os.close(fd)
		except:
			print("Couldn't close fd. Whatever...")

if __name__ == '__main__':
	import sys
	import json
	import argparse
	from time import time_ns

	args = sys.argv[1:]

	# parser = argparse.ArgumentParser(sys.argv[0], description='Runs SpeciesNet prediction')
	# parser.add_argument('input_path', type=str, help='Input path for the image')
	# parsed = parser.parse_args(args)

	# with open(parsed.input_path, 'rb') as image_file:
	# 	ret = lambda_handler(image_file.read(), None)
	# 	print(json.dumps(ret, indent=4))

	parser = argparse.ArgumentParser(sys.argv[0], description='Runs a test on the lambda_handler for SpeciesNet prediction')
	parsed = parser.parse_args(args)

	print(json.dumps(lambda_handler({'test': True}, None), indent=4))