import json
from datetime import datetime

import config as cfg
import raghelper as rag

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

#A study aid to prepare multiple choice exam questions

# Exam flow
# [START] -----> [generate_response] ------------> [evaluate_response] ----score = 1 or tries = max-----[next_question]------(numq == maxq) ---> [END]
#                      ^                                    |                                                |
#                      |                                    |                                                |                                     
#                      |                           (score = 0 and tries < max)                           (numq < maxq) 
#                      |                                 [retry]                                          [new]                                         
#                      |                                    |                                                | 
#                      |                                    v                                                v
#                      ---------------------------------------------------------------------------------------
#
#  []:  Nodes
#  (?): Conditional branching

#1. Define the state structure for email processing
class LlmState(TypedDict):
    user_prompt: str
    generator_response: Dict[str, Any]
    evaluator_response: Dict[str, Any]
    score: int
    num_tries: int
    max_tries: int
    num_questions: int
    max_questions: int
    questions: List[str]

#2. Define the processing functions that will form the nodes for the state graph
def generate_response(state: LlmState):
    """Generate a response to the user prompt"""
    cfg.sysPrompt = cfg.singleQestionModePrompt
    userPrompt = state["user_prompt"]

    print("-"*40)
    print(f"Working on question {state["num_questions"]+1} of {state['max_questions']}")
    print("User prompt: {}".format(userPrompt))
    print("Generating response...")

    userMessage = {'role':'user', 'content': f"{userPrompt}"}
    rag.write_log(cfg.logFile, f"User prompt: {userPrompt}\n")
    rag.add_to_history(userMessage)

    #join the user and assistant messages from history to create the prompt. This is done to preserve context
    chatHistory = "\n".join([h["content"] for h in cfg.history if h["role"] == "user" or h["role"] == "assistant"])
    ragData = rag.query_vectorstore(chatHistory, cfg.documentSource)
    response = rag.get_litellm_generator_response(ragData, jsonOutput=True, schema=cfg.singleQuestionSchema)
    
    #wrap this around a try / exception block
    try:
        generatorResponse = json.loads(response.choices[0].message.content)
        rag.write_log(cfg.logFile, f"Generator response: {generatorResponse}\n")
    except Exception as e:
        print(f"Error parsing generator response: {e}")
        print(f"Generator response: {response.choices[0].message.content}")
        rag.write_log(cfg.errorLogFile, f"Generator response (Error): {response.choices[0].message.content}")
        generatorResponse = {}

    return {
        "generator_response": generatorResponse,
        }

def evaluate_response(state: LlmState):
    """Judge the response from the generator"""
    print("Evaluating response...")
    numTries = state["num_tries"] + 1
    generatorResponse = state["generator_response"]

    if "INSUFFICIENT_CONTEXT" in generatorResponse:
        score = 1
        evaluatorResponse = "Insufficient context.  Evaluation skipped!"
    else:
        chatHistory = "\n".join([h["content"] for h in cfg.history if h["role"] == "user" or h["role"] == "assistant"])
        ragData = rag.query_vectorstore(chatHistory, cfg.documentSource)
        response = rag.get_litellm_evaluator_response(generatorResponse, ragData, jsonOutput=False, schema=cfg.judgeSchema)
        evaluatorResponse = response.choices[0].message.content

        start = evaluatorResponse.find("{")
        end = evaluatorResponse.rfind("}")
        if start != -1 and end != -1:
            verdictStr = evaluatorResponse[start:end+1]
        else:
            verdictStr = evaluatorResponse

        try:
            verdictJson = json.loads(verdictStr, strict=True)
            score = verdictJson["score"]
            rag.write_log(cfg.logFile, f"Evaluator response: {verdictJson}\n")
        except Exception as e:
            print(f"Error parsing evaluator response: {e}")
            print(f"Generated question / answer: {generatorResponse}")
            print(f"Evaluator response: {evaluatorResponse}")
            rag.write_log(cfg.errorLogFile, f"Evaluator response (Error): {evaluatorResponse}") 
            verdictJson = {}
            score = 0

    generatorResponse["questions"][0]["verdict"] = verdictJson

    return {
        "score": score,
        "num_tries": numTries,
        "generator_response": generatorResponse,
        "evaluator_response": evaluatorResponse
    }

def next_question(state: LlmState):
    numQuestions = state["num_questions"]
    questions = state["questions"]
    if (state["score"] == 1):
        """save the generator response to previous question in history"""
        assistantMessage = {'role':'assistant', 'content': f"{state["generator_response"]}"}
        rag.add_to_history(assistantMessage)

        """save the generator response['questions'] in questions list"""
        questions.append(state["generator_response"]["questions"][0])

        #print(f"generator response: {state["generator_response"]}")
        numQuestions += 1

    """Ask a new question"""
    userPrompt = "Ask me another question on the same topic. Do not repeat a question asked previously!"
    return {
        "user_prompt": userPrompt,
        "generator_response": "",
        "evaluator_response": "",
        "score": 0, 
        "num_tries": 0,
        "num_questions": numQuestions,
        "questions": questions
    }

#3. Define routing logic based on state
def route_flow(state: LlmState) -> str:
    """Determine the next step based on num tries for the question"""

    print(f"Checking answer for question {state["num_questions"]}:  Score: {state["score"]}, num_tries: {state["num_tries"]}")
    rag.write_log(cfg.logFile, f"Checking answer for question {state["num_questions"]}:  Score: {state["score"]}, num_tries: {state["num_tries"]}\n")

    if state["score"] == 0:
        if state["num_tries"] >= state["max_tries"]:
            print("Max tries reached.  New question.")
            return "done"
        else:
            print("Incorrect response.  Retrying...")
            return "retry"
    else:
        return "done"

def route_flow2(state: LlmState) -> str:
    """Determine the next step based num questions"""
    print(f"{state["num_questions"]} / {state["max_questions"]} done.")
    rag.write_log(cfg.logFile, f"{state["num_questions"]} / {state["max_questions"]} done.\n")

    if state["num_questions"] >= state["max_questions"]:
        print("Max questions reached.  Done.")
        return "done"
    else:
        return "new"

#4. Create the state graph
llm_as_judge_graph = StateGraph(LlmState)
llm_as_judge_graph.add_node("generate_response", generate_response)
llm_as_judge_graph.add_node("evaluate_response", evaluate_response)
llm_as_judge_graph.add_node("next_question", next_question)

#5. Add the edges
llm_as_judge_graph.add_edge(START, "generate_response")

llm_as_judge_graph.add_edge("generate_response", "evaluate_response")
# Add conditional branching from generate_response
llm_as_judge_graph.add_conditional_edges(
    "evaluate_response",
    route_flow,
    {
        "done": "next_question",
        "retry": "generate_response"
    }
)

llm_as_judge_graph.add_conditional_edges(
    "next_question",
    route_flow2,
    {
        "done": END,
        "new": "generate_response"
    }
)

#6. Compile the graph
compiled_graph = llm_as_judge_graph.compile()

#7. Example invocation
initial_state = {
    "user_prompt": "",
    "generator_response": "",
    "evaluator_response": "",
    "score": 0,
    "num_tries": 0,
    "max_tries" : cfg.maxTries,
    "num_questions" : 0,
    "max_questions" : cfg.maxQuestions,
    "questions" : []
}

config = {"recursion_limit": 100}

#8. Save exam
def save_exam(state: LlmState):
    """Save the exam to a file"""
    print("Saving exam...")
    exam = state["questions"]
    examFile = "exam-{}.txt".format(cfg.timestamp_int)
    with open(examFile, "w") as f:
        f.write(json.dumps(exam, indent=4))
    print("Exam saved to {}".format(examFile))


#main loop
if __name__ == '__main__':
    rag.initialize()
    cfg.documentSource = rag.select_document("What subject would you like me to ask questions on?")
    topic = input("What area / topic would you like the exam to be on? Hit enter for all topics: ")
    print("Thank you. Preparing the questions...")
    cfg.sysPrompt = cfg.normalModePrompt
    if topic.strip() == "":
        response = rag.get_response("Generate a list of topics", jsonOutput=False, schema=None)
        #print("List of topics: {}".format(response))
        initial_state["user_prompt"] = f"""Please create a multiple choice exam in JSON format, 
with {cfg.maxQuestions} question(s) from the document {cfg.documentSource}.  
The questions should be about the following topics: {response}"""
    else:
        initial_state["user_prompt"] = f"""Please create a multiple choice exam in JSON format, 
with {cfg.maxQuestions} question(s) from the document {cfg.documentSource}.
The questions should be about the following topic: {topic}"""

    result = compiled_graph.invoke(initial_state, config=config)
    #print("Final state:")
    #print(json.dumps(result, indent=4))
    save_exam(result)
  
