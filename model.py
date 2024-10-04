from sqlalchemy import DateTime, ForeignKey, Integer, String, Column
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()


# User Model
class User(db.Model):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)  # Auto-incremented primary key
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    # One-to-many relationship with ChatHistory
    chat_histories = relationship('ChatHistory', backref='user', lazy=True)


# Chat Model
class Chat(db.Model):
    __tablename__ = 'chat'

    chat_id = Column(String, primary_key=True)  # Auto-incremented primary key
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # Foreign key from users

    # One-to-many relationship with ChatHistory
    chat_histories = relationship('ChatHistory', backref='chat', lazy=True)


# ChatHistory Model
class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    uid = Column(Integer, primary_key=True, autoincrement=True)  # Auto-incremented primary key
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # Foreign key from users
    chat_id = Column(Integer, ForeignKey('chat.chat_id'), nullable=False)  # Foreign key from chat
    question = Column(String(255), nullable=False)
    answer = Column(String(255), nullable=False)
    time_stamp = Column(DateTime, default=datetime.utcnow)  # Automatically set to current time


class Memories(db.Model):
    _tablename_ = 'memories'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Auto-incremented primary key
    url = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)  # Foreign key referencing users
    # chat_num = Column(String(255), nullable=True)
    # uuids = Column(String, nullable=True)  # uuids field to store UUIDs (as text)