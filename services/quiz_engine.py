def check_answer(user_ans, correct_ans):
    return user_ans == correct_ans

def next_question(index,total):
    if index+1 < total:
        return index+1
    return None
