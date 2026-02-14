import os
from typing import Callable


def require_env[T: Callable](*vars: str) -> Callable[[T], T]:
	'''
	Ensures environment variables are present when the target function is loaded
	
	:param vars: The required environment variable names
	:type vars: str
	:return: Returns an identity decorator (i.e. the target function behaves the same) \
		if the required environment variables are present, otherwise raises an EnvironmentError
	:rtype: Callable[[Callable[..., Any]], None]
	'''
	missing_env_vars = [var for var in vars if os.getenv(var, '') == '']
	if missing_env_vars:
		raise EnvironmentError(f"Missing environment variables: {', '.join(missing_env_vars)}")
	
	return lambda x: x