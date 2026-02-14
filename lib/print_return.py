
import sys
from typing import Any, Callable, TypeVar

def print_return[T: Callable](*,
	prefix:str='',
	indent:str='',
	to_str:Callable[[Any], str]=str,
	print:Callable[[str],None]=print,
	on_err: Callable[[str],None]=lambda s: print(s, file=sys.stderr),
	continue_on_err:bool=True
) -> Callable[[T], T]:
	def decorator(fn: T) -> T:
		def new_function(*args, **kwargs):
			ret = fn(*args, **kwargs)
			try:
				s: str = to_str(ret)
				if indent != '':
					s = s.replace('\n', f'\n{indent}')
				print(f'{prefix}{s}')
			except Exception as e:
				on_err(f'ERROR: print_return caught exception: {e}') # which print?
				if not continue_on_err:
					raise e
			return ret
		return new_function # pyright: ignore[reportReturnType]
	return decorator