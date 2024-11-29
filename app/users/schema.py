from marshmallow import Schema, fields


class UserSchema(Schema):
    id = fields.Int(required=True)
    username = fields.Str(required=True)
    score = fields.Int(required=True)
    points = fields.Int(required=True)


class ListUserSchema(Schema):
    users = fields.Nested("UserSchema", many=True)
