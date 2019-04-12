class MarshmallowMixin:
    schema_class = None

    def get_schema_class(self):
        return self.schema_class

    def serialize(self, data):
        return self.get_schema().dump(data).data
