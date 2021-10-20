from datetime import datetime
from peewee import (
    Model,
    CharField,
    TextField,
    AutoField,
    DateTimeField,
    IntegerField,
    ForeignKeyField,
    BooleanField,
)
from .db import db


class BaseModel(Model):
    id = AutoField()
    creationDate = DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db
        legacy_table_names = False


class User(BaseModel):
    name = CharField(unique=True, null=False)
    coins = IntegerField(null=False, default=0)
    isActive = BooleanField(default=True)
    reported = IntegerField(default=0)


class Verification(BaseModel):
    countryCode = CharField(null=False)
    mobile = CharField(null=False)
    verificationCode = CharField(null=True)
    user = ForeignKeyField(User, null=True)

    class Meta:
        indexes = ((("countryCode", "mobile"), True),)


class Post(BaseModel):
    user = ForeignKeyField(User)
    text = TextField(null=False)
    liked = IntegerField(default=0)
    isActive = BooleanField(default=True)
    reported = IntegerField(default=0)

    userName = CharField(null=False)  # normalized


def createTables() -> bool:
    try:
        db.create_tables([User, Verification, Post])
    except Exception as e:
        print(e)
        return False
    return True


def dropTables() -> bool:
    try:
        db.drop_tables([Verification, User, Post])
    except Exception as e:
        print(e)
        return False
    return True
