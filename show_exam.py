
import json
# exam = [
#         "{\n    \"comments\": \"\",\n    \"question\": {\n        \"text\": \"What is the subject of Chapter 8?\",\n        \"options\": {\n            \"A\": \"Rotational dynamics\",\n            \"B\": \"Translational kinematics\",\n            \"C\": \"Rotational kinematics\",\n            \"D\": \"Motion in one dimension\"\n        },\n        \"answer\": \"C\",\n        \"explanation\": \"The chapter begins to consider the general motion of a rigid body, which includes rotational as well as translational motions.\",\n        \"reference\": \"Chapter 8, first paragraph\"\n    }\n}",
#         "{\n    \"comments\": \"\",\n    \"question\": {\n        \"text\": \"What is considered in Chapter 9?\",\n        \"options\": {\n            \"A\": \"Rotational kinematics\",\n            \"B\": \"Translational dynamics\",\n            \"C\": \"Rotational dynamics\",\n            \"D\": \"Motion of particles\"\n        },\n        \"answer\": \"C\",\n        \"explanation\": \"Chapter 9 begins the study of rotational dynamics, which is the subject of causes of rotation.\",\n        \"reference\": \"CHAPTER 9, ROTATIONAL DYNAMICS, first paragraph\"\n    }\n}",
#         "{\n    \"comments\": \"\",\n    \"question\": {\n        \"text\": \"What type of motion is considered in Chapter 8?\",\n        \"options\": {\n            \"A\": \"Pure rotational motion\",\n            \"B\": \"Combined rotation and translation\",\n            \"C\": \"Translational motion only\",\n            \"D\": \"Motion in one dimension\"\n        },\n        \"answer\": \"A\",\n        \"explanation\": \"Chapter 8 considers only pure rotational motion, excluding the more complicated case of combined rotation and translation.\",\n        \"reference\": \"Chapter 8, first paragraph\"\n    }\n}",
#         "{\n    \"comments\": \"\",\n    \"question\": {\n        \"text\": \"What is the subject of Chapter 9?\",\n        \"options\": {\n            \"A\": \"Rotational kinematics\",\n            \"B\": \"Translational dynamics\",\n            \"C\": \"Rotational dynamics and translational motion\",\n            \"D\": \"Motion of particles\"\n        },\n        \"answer\": \"C\",\n        \"explanation\": \"Chapter 9 begins the study of rotational dynamics, which is the subject of causes of rotation. It also considers the interaction of an object with its environment.\",\n        \"reference\": \"CHAPTER 9, ROTATIONAL DYNAMICS, first paragraph\"\n    }\n}"
# ]

def read_exam(file):
    with open(file, 'r') as f:
        exam = json.load(f)
    return exam

if __name__ == '__main__':
    score = 0
    max_score = 0
    print("="*40)
    examFile = input("Name of exam file: ")
    exam = read_exam(examFile)
    for question in exam:
        if "comments" in question and "INSUFFICIENT CONTEXT" in question["comments"]:
            continue
        
        if "text" not in question:
            continue

        if question["verdict"]["desirability"] == 0:
            continue

        print(f"Question: {question['text']}")
        print(f"Options: ")
        for k,v in question['options'].items():
            print("{}: {}".format(k,v))
        your_answer = input("Your answer (A, B, C, or D): ")
        if your_answer.lower() in question['answer'].lower():
            print("\nCorrect!")
            print(f"Explanation: {question['explanation']}")
            print(f"Reference: {question['reference']}")
            score += 1
            max_score += 1
        elif your_answer.strip().lower() in ["exit", "bye", "quit", "end"]:
            status="exit"
            break
        else:
            print(f"\nIncorrect! The correct answer was {question['answer']}.")
            print(f"Explanation: {question['explanation']}")
            print(f"Reference: {question['reference']}")
            max_score += 1
        print(f"Score {score} / {max_score}")
        print("-"*40)
        print("Judge's interpretation of the above:")
        verdict = question["verdict"]
        if (verdict["score"] == 1):
            print("This question is acceptable.")
            print("Reasoning: {}".format(verdict["reasoning"]))
        print("-"*40)
    print(f"Final Score: {score} out of {max_score}")
    print("Exam ended.")
    print("="*40)
