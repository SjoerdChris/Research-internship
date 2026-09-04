import os
import redis
from flask import Flask

app = Flask(__name__)
cache - redis.Redis(host=os.environ.get('REDIS_HOST', 'redis'), port=int(os.getenv('REDIS_PORT', 6379)))

@app.route('/')
def hello():
    count = cache.incr('hits')
    return f'Hello! This page has been visited {count} times.'