class Validator(object):

    def __init__(self, source, args):
        self._source = source
        self._rules = args

    def iter_validate(self):
        for variable_name, validator in self._rules:
            yield variable_name, validator(
                self._source(variable_name), variable_name, ""
            )

    def validate(self):
        return {
            variable_name: validator(
                self._source(variable_name), variable_name, ""
            )
            for variable_name, validator
            in self._rules
        }
