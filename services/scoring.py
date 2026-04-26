def calculate_score(correct, wrong, negative=0.25):
    return (correct * 4) - (wrong * negative * 4)
