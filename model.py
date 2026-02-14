from speciesnet import SpeciesNet

# Important for docker build:
#  This generates the KAGGLEHUB_CACHE if it doesn't exist, which saves a lot of time for future invocations
model = SpeciesNet(
	'kaggle:google/speciesnet/pyTorch/v4.0.1a',
	components='all',
	geofence=True,
)