import json
import pprint
import raghelper as rag
import config as cfg

#A study aid which does not have llm as a judge
#this habdles the interaction with the user, building the prompt from history and getting the response from litellm

def normal_mode():
    cfg.sysPrompt = cfg.normalModePrompt
    while(True):
        cfg.documentSource = rag.select_document("Which document would you like to talk about?")
        rag.clear_history()
        print("Thank you. Type 'clear' to switch documents and 'bye' or 'quit' to end.\n")
        while True:
            q = input(":").lower().strip()
            print("-"*40)
            if q != "":
                if q.strip().lower() == "clear":
                    status="clear"
                    break
                elif q.strip().lower() in ["exit", "bye", "quit", "end"]:
                    status="exit"
                    break
                else:
                    #q += ".\n Use only the context provided to answer the question. If the context does not contain the answer, respond with INSUFFICIENT_CONTEXT."
                    response = rag.get_response(q)
                    print(response + "\n")
                    # if response.startswith("I'm sorry"):
                    #     print("It seems I don't have the information you're looking for in my library. Type 'clear' to switch documents or topics.\n")
            else:
                continue

        if status == "clear":
            continue
        elif status == "exit":
            break


# def interactive_quiz_mode():
#     print("Great, let's start the quiz!")

#     while True:
#         cfg.documentSource = rag.select_document("What document would you like to be quizzed on?")
#         number_of_questions = cfg.interactiveQuizModeNumberOfQuestions
#         score = 0
#         max_score = 0

#         rag.clear_history()
#         cfg.sysPrompt = cfg.interactiveQuizModePrompt
#         instructions = """Any additional instructions?
# For example, 'Focus on chapter 2' or
# 'Only ask about key terms' or
# 'Ask math problems on specific topics', or
# press enter for none: """
#         extra_instructions = input(instructions)
#         if extra_instructions.strip() == "":
#             extra_instructions = "Focus on a variety of topics."
#         print("-"*40)
#         q = "Please create an exam in JSON format, with {} questions from the document {}. {}.".format(number_of_questions, cfg.documentSource, extra_instructions)
#         print(q) if cfg.debugLevel > 1 else None
#         print("Let me get the questions for you...")
#         try:
#             examStr = rag.get_response(q, jsonOutput=True, schema=cfg.examSchema)
#             examStr = examStr[examStr.index('{'):examStr.rindex('}')+1]
#             #print("Extracted JSON string:\n{}".format(examStr)) if cfg.debugLevel > 0 else None
#             exam = json.loads(examStr, strict=True)
#         except Exception as e:
#             print("Error parsing quiz JSON: {}".format(e))
#             break

#         if 'questions' not in exam or len(exam['questions']) == 0:
#             print("No questions found for your criteria.")
#         else:
#             while True:
#                 for question in exam['questions']:
#                     print(f"Question: {question['question']}")
#                     print(f"Options: ")
#                     for k,v in question['options'].items():
#                         print("{}: {}".format(k,v))
#                     your_answer = input("Your answer (A, B, C, or D): ")
#                     if your_answer.lower() in question['answer'].lower():
#                         print("Correct!")
#                         score += 1
#                         max_score += 1
#                     elif your_answer.strip().lower() in ["exit", "bye", "quit", "end"]:
#                         status="exit"
#                         break
#                     else:
#                         print(f"Incorrect! The correct answer was {question['answer']}.")
#                         print(f"Explanation: {question['explanation']}")
#                         print(f"Reference: {question['reference']}")
#                         max_score += 1
#                     print(f"Score {score} / {max_score}.\nWould you like to continue? (y/[n]): ")
#                     #if proceed.lower() != "y":
#                     #    break
#                     print("-"*40)
#                 print(f"Final Score: {score} out of {max_score}")
#                 print("Quiz ended.")
#                 print("="*40)
#                 break

#         play_again = input("Play again? (y/[n]): ")
#         print("-"*40)
#         if play_again.lower() == "y" or play_again.lower() == "yes":
#             continue
#         else:
#             break

# def exam_mode():
#     print("Great, let's create the exam!")
#     cfg.documentSource = rag.select_document("What document would you like the exam to be about?")
#     instructions = """Any additional instructions?
# For example, 'Focus on chapter 2' or
# 'Only ask about key terms' or
# 'Ask math problems on specific topics', or
# press enter for none: """
#     extra_instructions = input(instructions)
#     if extra_instructions.strip() == "":
#         extra_instructions = "Focus on a variety of topics."
#     number_of_questions = input("How many questions would you like? (default 5): ")
#     print("-"*40)
#     if not number_of_questions.isdigit():
#         number_of_questions = cfg.examModeNumberOfQuestions

#     cfg.sysPrompt = cfg.examModePrompt
#     q = "Please create an exam with {} questions from the document {}. {}. Leave out the answer keys".format(number_of_questions, cfg.documentSource, extra_instructions)
#     response = rag.get_response(q)
#     print(response)
#     q = """
# Now provide the answer keys to the above questions in JSON format as shown below:
# answer_keys = {
#     "comments": "What fun! Let's have some curious adventures! Here are your questions:",
#     "questions": [
#         {
#             "question": "The question text",
#             "options": {
#                 "A": "Option A text",
#                 "B": "Option B text",
#                 "C": "Option C text",
#                 "D": "Option D text"
#             },
#             "answer": "The correct answer letter (A, B, C, or D)",
#             "explanation": "The explanation text",
#             "reference": "The chapter and line reference text"
#         }
#     ]
# }
# """
#     print("-"*40)
#     print("\n\nLet me get the answer keys for you...")
#     responseStr = rag.get_response(q, jsonOutput=True, schema=cfg.examSchema)
#     responseJson = json.loads(responseStr, strict=True)
#     pprint.pprint(responseJson)
#     print("="*40)

# def flashcard_mode():
#     print("Great, let's create flashcards!")
#     cfg.documentSource = rag.select_document("What document would you like the flashcards to be about?")

#     number_of_flashcards = input("How many flashcards would you like? (default 5): ")
#     print("-"*40)
#     if not number_of_flashcards.isdigit():
#         number_of_flashcards = cfg.flashcardModeNumberOfFlashcards

#     rag.clear_history()
#     cfg.sysPrompt = cfg.flashcardModePrompt
#     instructions = """Any additional instructions?
# For example, 'Focus on chapter 2' or
# 'Only ask about key terms' or
# 'Ask math problems on specific topics', or
# press enter for none: """
#     extra_instructions = input(instructions)
#     if extra_instructions.strip() == "":
#         extra_instructions = "Focus on a variety of topics."
#     print("-"*40)
#     q = "Please create {} flashcards from the document {}. {}.".format(number_of_flashcards, cfg.documentSource, extra_instructions)
#     print(q) if cfg.debugLevel > 1 else None
#     print("\n\nLet me get the flashcards for you...")
#     responseStr = rag.get_response(q, jsonOutput=True, schema=cfg.flashcardSchema)
#     print("responseStr: {}".format(responseStr)) if cfg.debugLevel > 0 else None
#     responseJson = json.loads(responseStr, strict=True)
#     pprint.pprint(responseJson)
#     print("="*40)


#main loop
if __name__ == '__main__':
    rag.initialize()
    normal_mode()
    print("Goodbye!")

    # name = input("What is your name? ")
    # if name.strip().lower() in ["exit", "bye", "quit", "end"]:
    #     print("Goodbye!")
    #     print("="*40)
    #     exit(0)
    # userMessage = {'role':'user', 'content': "My name is {}.  You can greet me by this name going forward".format(name)}
    # rag.add_to_history(userMessage)
    # print("Hi {}, nice to meet you!\n".format(name))

    # tries = 0
    # while True and tries < 4:
    #     tries += 1
    #     if tries >= 4:
    #         print("Sorry, I'm unable to help you.  Please try later!")
    #         break

    #     mode = input("First, choose a mode\n(1) Normal (default)\n(2) Interactive Quiz\n(3) Exam\n(4) Flash Cards\n(enter [1], 2, 3 or 4): ")
    #     print("-"*40)
    #     if mode == "":
    #         normal_mode()
    #         break
    #     elif mode == "1" or "normal" in mode:
    #         normal_mode()
    #         break
    #     elif mode == "2" or "interactive" in mode:
    #         interactive_quiz_mode()
    #         break
    #     elif mode == "3" or "exam" in mode:
    #         exam_mode()
    #         break
    #     elif mode == "4" or "flash" in mode:
    #         flashcard_mode()
    #         break
    #     elif mode.strip().lower() in ["exit", "bye", "quit", "end"]:
    #         break
    #     else:
    #         print("Enter 1, 2, 3 or 4 to select a mode.")
    #         continue
