from flask import Flask
from fitnessapp import app

if __name__=="__main__":
    app.run(host='0.0.0.0', port=5000, ssl_context=('/etc/letsencrypt/live/logs.hhixl.net/fullchain.pem','/etc/letsencrypt/live/logs.hhixl.net/privkey.pem'), threaded=True)
