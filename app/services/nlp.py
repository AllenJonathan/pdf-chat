from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_together import TogetherEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough


text_splitter = CharacterTextSplitter(
    # shows how to seperate
    separator="\n",
    # Shows the document token length
    chunk_size=1000,
    # How much overlap should exist between documents
    chunk_overlap=150,
    # How to measure length
    length_function=len
)

# a simple function that removes \n newline from the content
def remove_ws(d):
    text = d.page_content.replace('\n','')
    d.page_content = text
    return d

def load_pdf(filepath):
    loader_py = PyMuPDFLoader(filepath)
    pages_py = loader_py.load()
    return pages_py

def split_text(pages):
    # Applying the splitter
    docs = text_splitter.split_documents(pages)
    docs = [remove_ws(d) for d in docs]
    return docs

def build_retriever(docs):
    embeddings = TogetherEmbeddings(model="togethercomputer/m2-bert-80M-8k-retrieval")
    # Creates the document retriever using docs and embeddings
    store = DocArrayInMemorySearch.from_documents(docs, embedding=embeddings)
    retriever = store.as_retriever()
    print(retriever)
    return retriever

def format_docs(docs):
  return "\n\n".join(doc.page_content for doc in docs)

def get_answer(docs, question):
    print(question)
    retriever = build_retriever(docs)
    template = """
    Answer the question based only on the context provided.

    Context: {context}

    Question: {question}
    """
    # Converts the prompt into a prompt template
    prompt = ChatPromptTemplate.from_template(template)
    llm = ChatGroq(temperature=0, model_name="mixtral-8x7b-32768")

    print("Processing...")

    # Construction of the chain
    chain = (
        {
            'context': retriever | format_docs,
            'question': RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    # asking for something inside the PDF image shown
    answer = chain.invoke(question)

    return answer
