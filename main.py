import litellm
import json
import pprint
import raghelper as rag
import config as cfg


#this habdles the interaction with the user, building the prompt from history and getting the response from litellm

def get_response(prompt, jsonOutput=False, schema=None):
    global context
    userMessage = {'role':'user', 'content': f"{prompt}"}
    rag.add_to_history(userMessage)

    #join the user and assistant messages from history to create the prompt. This is done to preserve context
    modPrompt = "\n".join([h["content"] for h in cfg.history if h["role"] == "user" or h["role"] == "assistant"])
    print("modPrompt: {}".format(modPrompt)) if cfg.debugLevel > 0 else None

    ragData = rag.query_vectorstore(modPrompt)
    print("Length of RAG list: {}".format(len(ragData))) if cfg.debugLevel > 0 else None
    response = get_litellm_response(ragData, jsonOutput=jsonOutput, schema=schema)
    print("Full response: {}".format(response)) if cfg.debugLevel > 1 else None

    assistantMessage = {'role':'assistant', 'content': response.choices[0].message.content}
    print("Assistant Message: {}".format(assistantMessage)) if cfg.debugLevel > 0 else None

    rag.add_to_history(assistantMessage)
    text = assistantMessage['content']
    return text

def get_litellm_response(ragData, jsonOutput=False, schema=None):
    global sysPrompt

    context = [d for d in ragData['documents']]
    print("Number of context documents: {}".format(len(context))) if cfg.debugLevel > 1 else None

    systemPrompt = sysPrompt + f"""
<context>
    {context}
</context>
"""

    print("System Prompt: {}".format(systemPrompt)) if cfg.debugLevel > 1 else None

    messages = [
        {"role": "system", "content": systemPrompt}
    ]

    messages.extend(cfg.history)
    print("Number of messages: {}, context length: {}".format(len(messages), len(json.dumps(context)))) if cfg.debugLevel > 1 else None

    args = {
        "model" : cfg.modelId,
        "messages" : messages,
        "temperature" : cfg.temperature
    }

    if jsonOutput:
        args["format"] = "json"
        args["response_format"] = {
            "type": "json_schema",
            "json_schema": {"schema": schema, "name": "schema", "strict": True},
        }

    response = litellm.completion(
        **args
    )

    return response

def normal_mode():
    global sysPrompt
    sysPrompt = cfg.normalModePrompt
    while(True):
        document = select_document("Awesome. Which document would you like to talk about?")
        rag.clear_history()
        q = "Use the document {} for the following discussion.".format(document)
        response = get_response(q)
        print(response + "\n")
        print("And remember, you can type 'clear' to switch documents or topics, and 'bye' or 'quit' to end the conversation.\n")
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
                    response = get_response(q)
                    print(response + "\n")
                    if response.startswith("I'm sorry"):
                        print("It seems I don't have the information you're looking for in my library. Type 'clear' to switch documents or topics.\n")
            else:
                continue

        if status == "clear":
            continue
        elif status == "exit":
            break

def interactive_quiz_mode():
    global sysPrompt
    print("Great, let's start the quiz!")

    while True:
        document = select_document("What document would you like to be quizzed on?")
        number_of_questions = cfg.interactiveQuizModeNumberOfQuestions
        score = 0
        max_score = 0

        rag.clear_history()
        sysPrompt = cfg.interactiveQuizModePrompt
        q = "Please create a quiz with {} questions about the document {}.".format(number_of_questions, document)

        try:
            examStr = get_response(q, jsonOutput=True, schema=cfg.examSchema)
            #print("Original response:\n{}".format(examStr))
            exam = json.loads(examStr, strict=True)
        except Exception as e:
            print("Error parsing quiz JSON: {}".format(e))
            break
        while True:
            for question in exam['questions']:
                print(f"Question: {question['question']}")
                print(f"Options: ")
                for k,v in question['options'].items():
                    print("{}: {}".format(k,v))
                your_answer = input("Your answer (A, B, C, or D): ")
                if your_answer.lower() in question['answer'].lower():
                    print("Correct!")
                    score += 1
                    max_score += 1
                else:
                    print(f"Incorrect! The correct answer was {question['answer']}.")
                    print(f"Explanation: {question['explanation']}")
                    print(f"Reference: {question['reference']}")
                    max_score += 1
                proceed = input(f"Score {score} / {max_score}.\nWould you like to continue? (y/[n]): ")
                if proceed.lower() != "y":
                    break
                print("-"*40)
            print(f"Final Score: {score} out of {max_score}")
            print("Quiz ended.")
            print("="*40)
            break

        play_again = input("Play again? (y/[n]): ")
        print("-"*40)
        if play_again.lower() == "y" or play_again.lower() == "yes":
            continue
        else:
            break

def exam_mode():
    global sysPrompt
    print("Great, let's create the exam!")
    document = select_document("What document would you like the exam to be about?")

    number_of_questions = input("How many questions would you like? (default 5): ")
    print("-"*40)
    if not number_of_questions.isdigit():
        number_of_questions = cfg.examModeNumberOfQuestions

    sysPrompt = cfg.examModePrompt
    q = "Please create an exam with {} questions about the document {}. Leave out the answer keys".format(number_of_questions, document)
    response = get_response(q)
    print(response)
    q = """
Now provide the answer keys to the above questions in JSON format as shown below:
answer_keys = {
    "comments": "What fun! Let's have some curious adventures! Here are your questions:",
    "questions": [
        {
            "question": "The question text",
            "options": {
                "A": "Option A text",
                "B": "Option B text",
                "C": "Option C text",
                "D": "Option D text"
            },
            "answer": "The correct answer letter (A, B, C, or D)",
            "explanation": "The explanation text",
            "reference": "The chapter and line reference text"
        }
    ]
}
"""
    print("-"*40)
    print("\n\nLet me get the answer keys for you...")
    responseStr = get_response(q, jsonOutput=True, schema=cfg.examSchema)
    responseJson = json.loads(responseStr, strict=True)
    pprint.pprint(responseJson)
    print("="*40)

def flashcard_mode():
    global sysPrompt
    print("Great, let's create flashcards!")
    document = select_document("What document would you like the flashcards to be about?")

    number_of_flashcards = input("How many flashcards would you like? (default 5): ")
    print("-"*40)
    if not number_of_flashcards.isdigit():
        number_of_flashcards = cfg.flashcardModeNumberOfFlashcards

    sysPrompt = cfg.flashcardModePrompt
    q = "Please create {} flashcards from the document {}.".format(number_of_flashcards, document)
    responseStr = get_response(q, jsonOutput=True, schema=cfg.flashcardSchema)
    print("responseStr: {}".format(responseStr)) if cfg.debugLevel > 0 else None
    responseJson = json.loads(responseStr, strict=True)
    pprint.pprint(responseJson)
    print("="*40)


def select_document(msg):
    tries = 0
    while True and tries < 4:
        tries += 1
        if tries >= 4:
            print("Sorry, I'm unable to help you.  Please try later!")
            status = "exit"
            break

        print(msg)
        for i,d in enumerate(cfg.documents):
            print("{}. {}".format(i+1,d))

        numDocuments = len(cfg.documents)
        num = input("Select (1-{}): ".format(numDocuments))
        if num.strip().lower() in ["exit", "bye", "quit", "end"]:
            status = "exit"
            break
        elif not num.isdigit() or int(num) < 1 or int(num) > numDocuments:
            print("Invalid number.")
            continue
        else:
            status="ok"
            break

    print("-"*40)
    if status == "exit":
        print("Goodbye!")
        exit(0)
    elif status == "ok":
        return cfg.documents[int(num)-1]

#main loop
if __name__ == '__main__':
    global sysPrompt
    rag.initialize()
    sysPrompt = cfg.openingPrompt
    name = input("What is your name? ")
    if name.strip().lower() in ["exit", "bye", "quit", "end"]:
        print("Goodbye!")
        print("="*40)
        exit(0)
    userMessage = {'role':'user', 'content': "My name is {}.  You can greet me by this name going forward".format(name)}
    rag.add_to_history(userMessage)
    print("Hi {}, nice to meet you!\n".format(name))

    tries = 0
    while True and tries < 4:
        tries += 1
        if tries >= 4:
            print("Sorry, I'm unable to help you.  Please try later!")
            break

        mode = input("First, choose a mode\n(1) Normal (default)\n(2) Interactive Quiz\n(3) Exam\n(4) Flash Cards\n(enter [1], 2, 3 or 4): ")
        print("-"*40)
        if mode == "":
            normal_mode()
            break
        elif mode == "1" or "normal" in mode:
            normal_mode()
            break
        elif mode == "2" or "interactive" in mode:
            interactive_quiz_mode()
            break
        elif mode == "3" or "exam" in mode:
            exam_mode()
            break
        elif mode == "4" or "flash" in mode:
            flashcard_mode()
            break
        elif mode.strip().lower() in ["exit", "bye", "quit", "end"]:
            break
        else:
            print("Enter 1, 2, 3 or 4 to select a mode.")
            continue

    print("Goodbye!")