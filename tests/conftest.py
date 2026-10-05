from hypothesis import settings

settings.register_profile("ci", derandomize=True)
settings.register_profile("fuzz", max_examples=5000)
