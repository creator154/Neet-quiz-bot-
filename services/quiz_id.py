import random,string

def generate_quiz_id():
    return ''.join(
      random.choice(
      string.ascii_uppercase+string.digits
      ) for _ in range(8)
)
