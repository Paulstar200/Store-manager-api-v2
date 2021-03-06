import datetime
import re

from flask_restful import Resource, reqparse
from flask import make_response, jsonify
from flask_jwt_extended import (create_access_token, jwt_required,
                                get_jwt_identity, get_raw_jwt)

from app.api.V2.models import UserModel
from app.db_con import db_connection


class UserRegistration(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', required=True,
                        help='Username cannot be blank', type=str)
    parser.add_argument('email', required=True, help='Email cannot be blank')
    parser.add_argument('password', required=True,
                        help='Password cannot be blank', type=str)
    parser.add_argument('role', required=True,
                        help="Role cannot be blank", type=str)

    @jwt_required
    def post(self):
        args = UserRegistration.parser.parse_args()
        raw_password = args.get('password').strip()
        username = args.get('username').strip()
        email = args.get('email').strip()
        role = args.get('role').strip()
        user = UserModel.find_by_email(get_jwt_identity())

        if not username:
            return {"message": "Username cannot be blank."}, 400

        if user[4] != "admin":
            return {
                "message":
                "You do not have authorization to access this feature."
            }, 401
        if role not in ["attendant", "admin"]:
            return {"message": "Please insert a role of 'attendant' or an 'admin' only."}, 400

        email_format = re.compile(
            r"(^[a-zA-Z0-9_.-]+@[a-zA-Z-]+\.[.a-zA-Z-]+$)")

        if len(raw_password) < 6 or not (re.match(email_format, email)):
            return {
                'message':
                'Please use a valid email and ensure the password exceeds 6 characters.'
            }, 400
        try:
            password = UserModel.generate_hash(raw_password)
            current_user_by_username = UserModel.find_by_username(username)
            current_user_by_email = UserModel.find_by_email(email)

            if current_user_by_username == None or current_user_by_email == None:
                result = UserModel.create_user(username, email, password, role)
                return make_response(
                    jsonify({"message": "User created successfully"}),
                    201)
            else:
                return {
                    'message':
                    'A user with that username or email already exists.'
                }, 409
        except Exception as my_exception:
            print(my_exception)
            return {"message": "User already exists"}, 400


class UserLogin(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, help='Email cannot be blank')
    parser.add_argument('password', required=True,
                        help='Password cannot be blank', type=str)

    def post(self):
        args = UserLogin.parser.parse_args()
        password = args.get('password').strip()
        email = args.get('email').strip()

        if not email:
            return {"message": "Email cannot be blank"}, 400
        if not password:
            return {"message": "Password cannot be blank"}, 400

        # check if user by the email exists
        current_user = UserModel.find_by_email(email)
        if current_user == None:
            return {"message": "User does not exist."}, 400

        if UserModel.verify_hash(password, current_user[3]):
            access_token = create_access_token(
                identity=email, expires_delta=datetime.timedelta(days=5))
            return {
                'message': 'Log in successful!',
                'username': current_user[1],
                'role': current_user[4],
                'access_token': access_token
            }, 201
        else:
            return {
                'message':
                'Incorrect password.'
            }, 400


class UserLogout(Resource):
    def __init__(self):
        self.db = db_connection()
        self.curr = self.db.cursor()

    @jwt_required
    def post(self):
        jti = get_raw_jwt()['jti']
        blacklist_token = """
                        INSERT INTO tokens (tokens) VALUES ('{}')
        """.format(jti)
        self.curr.execute(blacklist_token)
        self.db.commit()
        return {"msg": "Successfully logged out"}, 200


class GetAllUsers(Resource):
    @jwt_required
    def get(self):
        return UserModel.get_all_users()


class GetEachUser(Resource):
    @jwt_required
    def get(self, id):
        return UserModel.get_single_user(id)
