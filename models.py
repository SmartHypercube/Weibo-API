#!/usr/bin/python3
# coding=utf-8

from peewee import (Model, SqliteDatabase,
                    ForeignKeyField, BareField,
                    IntegerField, BooleanField, TextField, DateTimeField)

__all__ = [
    'User',
    'UserInfo',
    'Post',
    'PostVote',
    'Comment',
    'PostPic',
    'Picture',
]

db = SqliteDatabase('weibo.db')


class BaseModel(Model):
    class Meta:
        database = db

    def __repr__(self):
        return '%s(\n    ' % type(self).__name__ + \
               ',\n    '.join(name + '=' + repr(getattr(self, name)).replace('\n', '\n    ')
                              for name in sorted(self._meta.fields)) + \
               ')'


class Picture(BaseModel):
    uri = TextField(unique=True)
    hash = TextField(null=True)


class User(BaseModel):
    uid = IntegerField(primary_key=True)
    name = TextField(unique=True)


class UserInfo(BaseModel):
    user = ForeignKeyField(User, 'info_set')
    key = TextField()
    value = BareField(null=True)


class Post(BaseModel):
    pid = TextField(unique=True)
    loaded = BooleanField(default=True)
    deleted = BooleanField(default=False)
    author = ForeignKeyField(User, null=True)
    time = DateTimeField(null=True)
    text = TextField(null=True)
    origin = ForeignKeyField('self', 'forward_set', null=True)
    picture_count = IntegerField(default=0)
    vote_count = IntegerField(default=0)
    forward_count = IntegerField(default=0)
    comment_count = IntegerField(default=0)


class PostVote(BaseModel):
    post = ForeignKeyField(Post, 'vote_set')
    user = ForeignKeyField(User)
    value = IntegerField(default=1)


class Comment(BaseModel):
    cid = IntegerField(primary_key=True)
    post = ForeignKeyField(Post)
    author = ForeignKeyField(User)
    time = DateTimeField()
    text = TextField()
    replyto = ForeignKeyField('self', null=True)
    vote_count = IntegerField()
    reply_count = IntegerField()


class PostPic(BaseModel):
    post = ForeignKeyField(Post, 'picture_set')
    picture = ForeignKeyField(Picture)


db.connect()
db.create_tables([User, UserInfo, Post, PostVote, Comment, PostPic, Picture], True)
