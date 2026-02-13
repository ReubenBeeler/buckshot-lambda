# Buckshot Lambda

This is an AWS Lambda function for validating images from the Raspberry Pi based on the presence of wildlife using SpeciesNet inference.

## AWS Lambda Files

```
lambda.py			# AWS Lambda event handler
create_layer.sh		# Auto-creates lambda_layer.zip
lambda_layer.zip	# AWS Lambda layer for lambda.py dependencies
```

## Technical Difficulties

TODO as I cleanup remnants of old problems...

- layer.zip

## TODOs

- Migrate validation to end-of-day batch
- Include bounding boxes in the S3 object metadata and conditionally render the bounding boxes in the frontend
