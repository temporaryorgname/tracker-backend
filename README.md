To start development server: `sudo ENV/bin/python3 main.py`

# Deployment (From Scratch)

* Clone the `tracker-backend` and `tracker-frontend` repositories
* Front end setup:
  * `npm install`
  * `npm run build`
  * Create directory `tracker-backend/fitnessapp/static`, and copy the contents of `tracker-frontend/build` into it.
* Ensure that all endpoints are correct
  * Front end should point to the correct REST API address
  * Back end should point to the correct database address
* Create virtual environment with `virtuelenv ENV`, and activate it with `source ENV/bin/activate`
* Install all dependencies with `pip install -r requirements.txt`
* Zappa
  * `zappa init`
  * Modify the `zappa_settings.json` to include `"aws_region": "us-east-1"`
  * `zappa deploy production`

## AWS Setup

Ceate an API Gateway to the flask app.
This gives you a Cloudfront address under `Target Domain Name`, which can your domain name can be CNAME'd to.
