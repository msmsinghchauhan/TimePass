from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain

import os
os.environ["REQUESTS_CA_BUNDLE"] = "/Users/sinm/Library/CloudStorage/OneDrive-NetAppInc/Desktop/Mukesh/TimePass/NetApp_ECO_FMC_CA.cer"
pem_path = "/opt/homebrew/etc/openssl@3/certs/../cert.pem"
os.environ['REQUESTS_CA_BUNDLE'] = pem_path
os.environ['SSL_CERT_FILE']      = pem_path


def load_your_key():
    # Load your OpenAI API key from a secure location
    # For example, you can use environment variables or a secure vault
    import os
    return os.getenv("OPENAI_API_KEY")

def detect_user():
    # Detect the user based on your application's logic
    # For example, you can use the current user's ID or username
    import getpass
    #return getpass.getuser()  # Returns the username of the current user
    return "sinm"



# Chat example
llm = ChatOpenAI(model_name      = "gpt-4o",
                 openai_api_base = "https://llm-proxy-api.ai.eng.netapp.com",
                 openai_api_key  = load_your_key(), # DO NOT HARDCODE YOUR KEY
                 model_kwargs    = {'user': detect_user() }) # DO NOT HARDCODE A USER HERE
# conversation = ConversationChain(llm=llm)
# completion = conversation.run("Write a function that prints n primes in python")
# print(completion)

#conversation = RunnableWithMessageHistory(llm=llm)
#completion = conversation.run("Write a function that prints n primes in python")
#print(completion)


class MessageHistory:
    def __init__(self, messages):
        self.messages = messages

def get_session_history(session_id):
    # Return a MessageHistory object, not a plain list
    return MessageHistory([
        {"role": "user", "content": "Hello"}
    ])
    


#def get_session_history(session_id):
#    return  [{"role": "user", "content": "Hello"}]

conversation = RunnableWithMessageHistory(
    runnable=llm,
    get_session_history=get_session_history
)

#completion = conversation.run("Write a function that prints n primes in python", session_id="test-session")
#print(completion)

completion = conversation.invoke(
    "Write a function that prints n primes in python",
    config={"session_id": "test-session"}
)
print(completion)



# Embeddings example
# from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(
                model           = "text-embedding-ada-002",
                openai_api_base = "https://llm-proxy-api.ai.eng.netapp.com",
                openai_api_key  = load_your_key(), # DO NOT HARDCODE YOUR KEY
                model_kwargs    = {'user': detect_user() }) # DO NOT HARDCODE A USER HERE
e = embeddings.embed_query("test string")

