from marshmallow import Schema, fields


class AdminSchema(Schema):
    id = fields.Int(required=False)
    login = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)
