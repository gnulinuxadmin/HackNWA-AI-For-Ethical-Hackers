# HackNWA-AI-For-Ethical-Hackers
# BSidesOK, and ISACA Omaha Spring Event Labs & Demos

# Securing Agentic AI Systems - BSides OK
Originally Taught by Evan Wagner and Christopher Williams

Some documentation and comments added by AI.


# Requirements to run labs locally:

Linux system with modern Nvidia GPU or Ollama-compatible or Windows or Mac system with hypervisor (VMWare, Virtual Box, etc.)

VM Image: (Please use Fedora ISO [https://www.fedoraproject.org/server/download/])

Tools used: Python, PyTorch, Transformers, Ollama, Open WebUI, Gradio, FastMCP, LangChain, LangGraph, Openclaw, Elastic Search, Wazuh
Material covered is completely published between textbooks and open source documentation, assembled in an 8 hour workshop to prepare attendees to understand AI related threats and defense.

# Lab 1: (20 minutes)
ML Fundamentals

Lecture: We cover key terms from classification to learning types.

Lab: We label some data and run the glue benchmark on small purpose built model. How well can it classify plant, animal, or mineral?


# Lab 2: (20 minutes)
From ML to GenAI

Lecture: AI Models, LLMs, and Prompting

Lab: We connect a local LLM and ask it questions? How consistent are the results? Can you tell you're chatting with an AI?


# Lab 3: (45 minutes)
LLMs using Tools -> MCP primer

Lecture: What is a Tool Call?

Lab: A server and client example performing basic mathematical operations. Our agent can now invoke these tools.



15-20 minute break

# lab 4: (45 minutes)
Building Agents

Lecture: What is an agent? 

Lab: Building an agent with LangChain. 

# lab 5: (45 minutes)
Autonymous Agents

Lecture: Intro to OpenClaw

Lab: Giving OpenClaw directions.


# lab 6: (45 minutes)
Attacking LLMs

Lecture: Types of Attacks: Prompt Injections, Jailbreaking, Data Exfil, Poisoining Attacks, Social Engineering, Insecure Output, Multimodal, Tool/Agent, Supply Chain, DoS and Hybrid.

Lab: Try out these techniques. Best attacks win challenge coins.


Lunch Break

# lab 7: (45 minutes)
Watchword Observability

Lecture: Logs or it didn't happen. Looking at the attacks and architecture, what would you want to see logged? We log connection info, prompts, responses, and agent actions. 

Lab: Examing logs for evidence of attacks and malicious actions. Can you find the exfil?


# Lab 8: (45 minutes)
Detection and Alerting

Lecture: Needle In A Haystack: What Events Matter Most? Generating alrerts from events.

Lab: Configuring alerts 


15-20 minute break

# lab 9: (45 minutes)
Lecture: Canaries in the Coal Mine: Planting canary tokens to detect malicious behavior.

Lab: Planting and observing canary token usage. Discussion of use cases.


# Lab 10: (30 minutes)
Lecture: Here we have an attack against a customer service agent. Obtain attribution, determine impact, and discuss containment and prevention.

Lab: Using the alert and tracing the logs, figure out who carried out the attack and any information that they obtained. Finally, what could be done to better protect the app?


# End Q&A

# AI For Ethical Hackers
Originally Presented by Christopher Williams and Jesus Bordelon

Lecture: Intro, Jargon, Architecture, Threats, Threat Taxonomy, Observabilty, Canaries, and Demos

Demos: An example super agent for cypto trading and a vulnerable multi-agent demo chat bot powered web app for resturant ordering.


# Securing Agentic AI Systems - ISACA Omaha
By Christopher Williams

Lecure: Building Agents, Autonymous Agents, Attacking LLMs, Detection and Alerting, Canaries

Demos: Agent Source Code, Attacks, Demos



