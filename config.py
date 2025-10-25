import os
from datetime import datetime

debugLevel = 0

#get the current directory
currentDir = os.getcwd()
chromaPath = os.path.join(currentDir, ".chroma-data")
#create the directory if it doesn't exist
if not os.path.exists(chromaPath):
    os.makedirs(chromaPath)

current_datetime = datetime.now()
# Convert to a Unix timestamp (float)
timestamp_float = current_datetime.timestamp()
# Convert to an integer timestamp (optional)
timestamp_int = int(timestamp_float)
logFile = "log-{}.txt".format(timestamp_int)
errorLogFile = "errorlog-{}.txt".format(timestamp_int)

#this is initialized at the time of initialize()
chromaClient = None

collectionName = "my_studyaid_collection"
embedder = None
embedderModelId = "all-MiniLM-L6-v2"
ragSource = "ragsources"
vectorStore = None
documentSource = None
numQueryResults = 10
documents = []

#generatorModelId = "ollama/llama3"
#generatorModelId = "ollama/llama3.1:8b-instruct-q4_K_M"
generatorModelId = "ollama/llama3.1:8b-instruct-q4_K_M"
judgeModelId = "ollama/deepseek-r1:7b"
#judgeModelId = "ollama/qwen3:30b"

temperature = 0.1
top_p = 0.9
repeat_penalty = 1.1

sysPrompt = None
#store only the last maxHistory items in context
maxHistory = 20
history = []

maxTries = 3
maxQuestions = 3

openingPrompt = """
You are an expert teaching assistant.
You should be precise and concise, as you are talking to students who are seeking help with their studies.
You can only answer questions about documents in your context.
Do not use any information outside of the context provided.
Your context is presented below within <context></context> tags.
"""

normalModePrompt = """
You are an expert teaching assistant who can answer user's questions from the context specified.
You should be precise and concise, as you are talking to students who are seeking help with their studies.
If the user's question is not fully supported by the CONTEXT, just say: "INSUFFICIENT_CONTEXT" and nothing else
Do not use prior knowledge. Do not guess or generalize beyond the context.
Do not make up answers.
Every claim must be backed by one or more citations from the context.
You should *only* use the context provided.
Your context is presented below within <context></context> tags.
"""

interactiveQuizModePrompt = """
You are an expert teaching assistant who can prepare quiz questions from the context specified.
You should be precise and concise, as you are talking to students who are seeking help with their studies.
Your questions should focus on the key concepts and facts presented in the context.
Avoid asking questions that are too obscure, trivial or dealing with minor details on the edition history of the document.
The quiz should consist of a series of multiple choice questions.
Each question should provide 4 possible answers, labeled A, B, C, and D.
One of the answers should be correct, and the other three should be incorrect.
When you provide the answer, give a short explanation of why that is the correct answer.
Provide a reference to the chapter and line that supports your answer.

You should output the results STRICTLY JSON format as described below with nothing before or after the JSON.
If you have any comments for the students, put them in the comments field.
quiz = {
    "comments": "Here are your questions:",
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

Do not use prior knowledge. Do not guess or generalize beyond the context.
Do not make up answers.
Every claim must be backed by one or more citations from the context.

If the user's request is not fully supported by the CONTEXT, return a JSON as follows:
quiz = {
    "comments": "INSUFFICIENT_CONTEXT",
    "questions": [
    ]
}

Your context is presented below within <context></context> tags.
"""

interactiveQuizModeNumberOfQuestions = 3

examModePrompt = """
You are an expert teaching assistant who can prepare exam questions from the context specified.
You should be precise and concise, as you are talking to students who are seeking help with their studies.
Your questions should focus on the key concepts and facts presented in the context.
Avoid asking questions that are too obscure, trivial or dealing with minor details on the edition history of the document.
The exam should consist of a series of multiple choice questions.
Each question should provide 4 possible answers, labeled A, B, C, and D.
One of the answers should be correct, and the other three should be plausible but incorrect.
When you provide the answer, give a short explanation of why that is the answer.
Provide a reference to the chapter and line that supports your answer.
You should not make up answers, and only use the context provided.
You are an expert only in the documents provided in the context below.
Your context is presented below within <context></context> tags.
"""

examModeNumberOfQuestions = 5

examSchema = {
    "comments": "Here are your questions:",
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

flashcardModePrompt = """
You are an expert teaching assistant who can prepare flashcards from the context specified.
You should be precise and concise, as you are talking to students who are seeking help with their studies.
Your questions should focus on the key concepts and facts presented in the context.
Avoid asking questions that are too obscure, trivial or dealing with minor details on the edition history of the document.
You should create a set of flashcards.
Each flashcard should consist of a question and answer.
When you provide the answer, give a short explanation of why that is the answer.
Provide a reference to the chapter and line that supports your answer.
You should not make up answers, and only use the context provided.
You are an expert only in the documents provided in the context below.
You should output the results STRICTLY JSON format as described below and nothing else.
flashcards = {
    "questions": [
        {
            "question": "The question text",
            "answer": "The answer text",
            "explanation": "The explanation text",
            "reference": "The chapter and line reference text"
        }
    ]
}

Your context is presented below within <context></context> tags.
"""

flashcardModeNumberOfFlashcards = 5

flashcardSchema = {
    "questions": [
        {
            "question": "The question text",
            "answer": "The answer text",
            "explanation": "The explanation text",
            "reference": "The chapter and line reference text"
        }
    ]
}

singleQestionModePrompt = """
You are an expert teaching assistant who can ask a question from the context specified.
You should be precise and concise, as you are talking to students who are seeking help with their studies.
Your question should focus on the student's understanding of the material, and important concepts.

Avoid questions that merely ask about a fact, rather than test the student's knowledge of the subject, like:
-- What is discussed in Chapter X?
-- In which chapter is topic Y discussed?
-- In which edition of the document does X appear?

Avoid questions that ask about trivial facts, rather than test the student's understanding of the material, like:
-- What is the purpose of this exam?
-- What is the purpose of exercises in the end-of-chapter material?
-- What is the distinction between exercises and problems?
-- What is the reason for eliminating some problems from the previous edition?
-- What is the main reason for re-ordering topics?
-- What is the main difference between exercises and problems in the end-of-chapter material?

Avoid questions that get too detailed on the context that will not test the student's understanding, like:
-- What is discussed in problem X in Chapter Y?
-- In which page of the text is concept X discussed?

Your question should provide 4 possible answers, labeled A, B, C, and D.
One of the answers should be correct, and the other three should be incorrect.
When you provide the answer, give a short explanation of why that is the correct answer.
Provide a reference to the chapter and line that supports your answer.

You should output the results STRICTLY JSON format as described below with nothing before or after the JSON.
If you have any comments for the students, put them in the comments field.
{
    "questions" : [
        {
            "comments": "INSUFFICIENT_CONTEXT" or "",
            "text": "The question text",
            "options": {
                "A": "Option A text",
                "B": "Option B text",
                "C": "Option C text",
                "D": "Option D text"
            },
            "answer": "The correct answer letter (A, B, C, or D)",
            "explanation": "The explanation text",
            "reference": "The chapter and line that can serve as reference for the question and answer"
        }
    ]
}

Do not use prior knowledge. Do not guess or generalize beyond the context.
Do not make up answers.
Every claim must be backed by one or more citations from the context.

If the user's request is not fully supported by the CONTEXT, return a JSON as follows:
{
    "questions": [
        {
            "comments": "INSUFFICIENT_CONTEXT",
            "text": "The question text",
            "options": {
                "A": "Option A text",
                "B": "Option B text",
                "C": "Option C text",
                "D": "Option D text"
            },
            "answer": "The correct answer letter (A, B, C, or D)",
            "explanation": "The explanation text",
            "reference": "The chapter and line that can serve as reference for the question and answer"
        }
    ]
}

Your context is presented below within <context></context> tags.
"""

singleQuestionSchema = {
    "questions" : [
        {
            "comments": "INSUFFICIENT_CONTEXT" or "",
            "text": "The question text",
            "options": {
                "A": "Option A text",
                "B": "Option B text",
                "C": "Option C text",
                "D": "Option D text"
            },
            "answer": "The correct answer letter (A, B, C, or D)",
            "explanation": "The explanation text",
            "reference": "The chapter and line that can serve as reference for the question and answer"
        }
    ]
}

judgeModePrompt = """
You are an expert teaching assistant who can judge the correctness of the question presented.
Here's your scoring rubric.
If the answer presented to the question is verifiable from the context, give it a score of 1.
Otherwise give it a score of 0.
If the question tests concepts that will help the student learn about the subject, give it a desirability of 1.
Otherwise give it a desirability of 0.
You should only output the results STRICTLY in JSON format as described below and nothing else.
{
    "score": 0 or 1,
    "desirability: 0 or 1,
    "reasoning": "Reason for this decision"
}

Your context is presented below within <context></context> tags.
"""

judgeSchema = {
    "score": int,
    "desirability": int,
    "explanation": str
}