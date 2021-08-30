from datetime import datetime
from peewee import (
    Model,
    CharField,
    AutoField,
    DateTimeField,
    IntegerField,
    ForeignKeyField,
    BooleanField,
)
from .db import db


class BaseModel(Model):
    id = AutoField()
    creation_date = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        legacy_table_names = False


class User(BaseModel):
    countryCode = CharField(null=False)
    mobile = CharField(null=False)
    verificationCode = CharField(null=True)
    name = CharField(unique=True, null=False)
    coins = IntegerField(null=False, default=0)
    isActive = BooleanField(default=True)
    isReported = BooleanField(default=False)
    reported = IntegerField(default=0)

    class Meta:
        indexes = ((("countryCode", "mobile"), True),)


class Post(BaseModel):
    user = ForeignKeyField(User)
    text = CharField(null=False)
    liked = IntegerField(default=0)
    isActive = BooleanField(default=True)
    isReported = BooleanField(default=False)
    reported = IntegerField(default=0)

    userName = CharField(null=False)  # normalized


def createTables() -> bool:
    try:
        db.create_tables([User, Post])
    except Exception as e:
        print(e)
        return False
    return True


def dropTables() -> bool:
    try:
        db.drop_tables([User, Post])
    except Exception as e:
        print(e)
        return False
    return True
