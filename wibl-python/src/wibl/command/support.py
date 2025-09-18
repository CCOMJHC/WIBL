import click

class ProbabilityParamType(click.ParamType):
    name = "probability"

    def convert(self, value, param, ctx):
        try:
            p = float(value)
        except ValueError:
            self.fail(f"{value} is not a valid floating point number.", param, ctx)
        if p < 0.0 or p > 1.0:
            self.fail(f"{value} must be between 0.0 and 1.0.", param, ctx)
        return p

PROBABILITY = ProbabilityParamType()
