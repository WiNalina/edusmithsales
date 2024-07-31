from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

#Create the Limiter object for limiting the number of possible login attempts
limiter = Limiter(key_func=get_remote_address)