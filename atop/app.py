import os
from string import digits
from random import choices
from typing import List

import jwt
from flask import Flask, request, jsonify, make_response
from flask_expects_json import expects_json
from jsonschema import ValidationError
from flask_cors import CORS
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict
from kavenegar import KavenegarAPI, APIException, HTTPException
from celery import Celery

from .configs import DEBUG, SECRET, KAVENEGAR_APIKEY, KAVENEGAR_VERIFICATION_TEMPLATE
from .models import Verification, User, Post
from .db import db
from .email import send_email as _send_email
from .middlewares import auth


app = Flask(__name__)
CORS(app)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.config.update(
    CELERY_BROKER_URL="redis://localhost:6379/1",
    CELERY_RESULT_BACKEND="redis://localhost:6379/1",
)
if DEBUG:
    os.environ["FLASK_ENV"] = "development"
# app.logger.debug("DEBUG")
# app.logger.warning("WARN")
# app.logger.error("ERROR")

celery = Celery(
    app.import_name,
    backend=app.config["CELERY_RESULT_BACKEND"],
    broker=app.config["CELERY_BROKER_URL"],
)
celery.conf.update(app.config)


class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask


@celery.task(bind=True)
def send_email(self, **kwargs):
    _send_email(**kwargs)


@app.errorhandler(400)
def bad_request(error):
    if isinstance(error.description, ValidationError):
        original_error = error.description
        return make_response(jsonify({"message": original_error.message}), 400)
    # handle other "Bad Request"-errors
    return error


@app.route("/v1/hello", methods=["GET"])
def hello():
    return "hello"


@app.route("/v1/verifications", methods=["PUT"])
@expects_json(
    {
        "type": "object",
        "properties": {
            "countryCode": {"type": "string", "pattern": r"^\+\d{2,8}$"},
            "mobile": {"type": "string", "pattern": r"^\d{6,24}$"},
        },
        "required": ["countryCode", "mobile"],
    }
)
def upsertVerification():
    j: dict = request.get_json()
    verificationCode: str = "".join(choices(digits, k=4))
    isUserNew: bool
    try:
        verification: Verification = Verification.get(
            Verification.countryCode == j["countryCode"],
            Verification.mobile == j["mobile"],
        )
    except Verification.DoesNotExist:
        isUserNew = True
        Verification.insert(
            countryCode=j["countryCode"],
            mobile=j["mobile"],
            verificationCode=verificationCode,
        ).execute()
    else:
        isUserNew = False
        updated: int = (
            Verification.update({Verification.verificationCode: verificationCode})
            .where(Verification.id == verification.id)
            .execute()
        )
        if updated != 1:
            return {"message": "database error"}, 500
    try:
        api = KavenegarAPI(KAVENEGAR_APIKEY)
        params = {
            "receptor": j["countryCode"] + j["mobile"],
            "token": verificationCode,
            "template": KAVENEGAR_VERIFICATION_TEMPLATE,
        }
        response = api.verify_lookup(params)
        print(response)
    # except APIException as e:
    #    print(e)
    #    return jsonify({"message": "sms failed"}), 500
    # except HTTPException as e:
    #    print(e)
    #    return jsonify({"message": "sms failed"}), 500
    # except Exception as e:
    #    print(e)
    #    return jsonify({"message": "sms failed"}), 500
    except Exception as e:
        print(e)
        return {"isUserNew": isUserNew}, 201 if isUserNew else 200

    return {"isUserNew": isUserNew}, 201 if isUserNew else 200


@app.route("/v1/users", methods=["PUT"])
@expects_json(
    {
        "type": "object",
        "properties": {
            "countryCode": {"type": "string", "pattern": r"^\+\d{2,8}$"},
            "mobile": {"type": "string", "pattern": r"^\d{6,24}$"},
            "verificationCode": {"type": "string", "minLength": 1},
            "name": {"type": "string", "minLength": 1},
        },
        "required": ["countryCode", "mobile", "verificationCode"],
    }
)
def upsertUser():
    j: dict = request.get_json()
    try:
        verification: Verification = Verification.get(
            Verification.countryCode == j["countryCode"],
            Verification.mobile == j["mobile"],
            Verification.verificationCode == j["verificationCode"],
        )
        print("vu", verification.user)
    except Verification.DoesNotExist:
        return {"message": "verification not found."}, 404
    userId: int
    if verification.user is None:
        name: str = j["name"]
        print("name", name)
        while True:
            try:
                userId = User.insert(name=name, coins=25).execute()
                print(userId)
            except IntegrityError:
                name += "".join(choices(digits, k=8))
                print("another name", name)
            except Exception as e:
                print("EEEEEEEE", e)
            else:
                break
        (
            Verification.update(user=userId, verificationCode=None)
            .where(Verification.id == verification.id)
            .execute()
        )
        print(userId, verification.id)
    else:
        userId = verification.user.id
        (
            Verification.update(verificationCode=None)
            .where(Verification.id == verification.id)
            .execute()
        )

    token = jwt.encode({"id": userId}, SECRET, algorithm="HS256")
    return {"token": token}, 201 if verification.user is None else 200


@app.route("/v1/users/current", methods=["GET"])
@auth
def showUser(userId):
    try:
        user: User = User.get(User.id == userId)
    except User.DoesNotExist:  # noqa: E722
        return {"message": "not found"}, 404

    _user: dict = model_to_dict(user)

    return _user, 200


@app.route("/v1/posts", methods=["POST"])
@auth
@expects_json(
    {
        "type": "object",
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 1000},
        },
        "required": ["text"],
    }
)
def createPost(userId):
    j: dict = request.get_json()
    with db.atomic() as transaction:
        updated: List[User] = list(
            User.update({User.coins: User.coins - 10})
            .where(User.id == userId, User.coins >= 10)
            .returning(User)
            .execute()
        )
        if len(updated) != 1:
            transaction.rollback()
            return {"message": "not enough coins"}, 402
        postId: int = Post.insert(
            user=userId, text=j["text"], userName=updated[0].name
        ).execute()

    return {"id": postId}, 201


@app.route("/v1/posts", methods=["GET"])
@auth
def showPosts(userId):
    try:
        limit: int = request.args.get("limit", 10, int)
        offset: int = request.args.get("offset", 0, int)
    except ValueError:
        return {"message": "limit or offset is invalid."}, 400
    posts: List[Post] = list(
        Post.select(Post.userName, Post.user, Post.text, Post.liked)
        .where(Post.isActive == True)
        .limit(limit)
        .offset(offset)
        .order_by(Post.creation_date.desc())
        .dicts()
    )
    return {"results": posts}, 200


@app.route("/v1/posts/{postId}", methods=["PATCH"])
@auth
def editPost(userId, postId):
    action = request.args.get("action")
    if action is None:
        return {"message": "action is required as GET query string."}, 400
    if action == "like":
        with db.atomic as transaction:
            updatedUsers: int = (
                User.update({User.coins: User.coins - 1})
                .where(User.id == userId, User.coins >= 1)
                .execute()
            )
            if updatedUsers != 1:
                transaction.rollback()
                return {"message": "not enough coins"}, 402
            updatedPosts: List[Post] = list(
                Post.update({Post.liked: Post.liked + 1})
                .where(Post.id == postId)
                .returning(Post)
                .execute()
            )
            if len(updatedPosts) != 1:
                transaction.rollback()
                return {"message": "post not found"}, 404
            updatedUsers: int = (
                User.update({User.coins: User.coins + 1})
                .where(User.id == updatedPosts[0].user)
                .execute()
            )
            if updatedUsers != 1:
                transaction.rollback()
                return {"message": "user not found"}, 404
        return {}, 200
    else:
        return {"message": "a valid action is required as GET query string."}, 400

    return {"id": postId}, 201
