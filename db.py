# -*- coding: utf-8 -*-
"""
数据库模型与简单持久化（使用 SQLAlchemy + SQLite）
- 初始化数据库
- 保存成绩（排行榜）
- 读取 top N 成绩
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import datetime
import os

BASE = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE, "escape_maze.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    time = Column(Integer, nullable=False)       # 通关时间（秒）
    coins = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now,server_default=func.now())

'''class User(Base):
    __tablename__ = "users"
'''

def init_db():
    """创建数据表（若不存在）"""
    Base.metadata.create_all(bind=engine)

def save_score(name, time_seconds, coins):
    """保存一条成绩记录"""
    db = SessionLocal()
    try:
        rec = Score(name=name, time=int(time_seconds), coins=int(coins))
        db.add(rec)
        db.commit()
    finally:
        db.close()

def get_top_scores(limit=10):
    """按通关时间升序返回前 limit 条记录（name,time,coins,created_at）"""
    db = SessionLocal()
    try:
        rows = db.query(Score).order_by(Score.time.asc()).limit(limit).all()
        return [(r.name, r.time, r.coins, r.created_at) for r in rows]
    finally:
        db.close()

def user_exist(name):
    return True

def add_user(user):
    return True

def password_correct(user):
    return True