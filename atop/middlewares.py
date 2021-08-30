from functools import wraps

import jwt
from flask import request

from .configs import SECRET


def auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("authorization")
        if token is None:
            return {"message": "login is required."}, 401
        else:
            try:
                payload: dict = jwt.decode(token, SECRET, algorithms=["HS256"])
            except jwt.PyJWTError:
                return {"message": "token is invalid."}, 401
            try:
                userId: int = payload["id"]
            except KeyError:
                return {"message": "token is invalid."}, 401

        return f(userId, *args, **kwargs)

    return decorated_function
