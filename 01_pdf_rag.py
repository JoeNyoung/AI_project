import os   # os 모듈을 사용하여 환경변수에 접근하기 위한 임포트
from dotenv import load_dotenv  # API 키를 환경변수로 관리하기 위한 설정 파일

load_dotenv()   # API 키 정보 로드 (.env 파일에 API 키를 입력해야 합니다.)

# LangSmith 추적 설정 (https://smith.langchain.com)
# !pip install -qU langchain-teddynote
from langchain_teddynote import logging
logging.langsmith("joeNyoung_pdf_rag_project")  # 프로젝트 이름 입력

print("==========================")

# RAG 파이프라인(1~8단계) 구성을 위한 LangChain 모듈 임포트
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# 단계 1: 문서 로드(Load Documents)
loader = PyMuPDFLoader("data/SPRI_AI_Brief_2023년12월호_F.pdf")
docs = loader.load()

print("문서의 metadata:", docs[10].__dict__)   # 문서의 메타데이터 확인
print(f"\nㅁ문서의 페이지수: {len(docs)}")        # 문서의 페이지 수 확인
print(f"\nㅁ목차 : {docs[1].page_content}")    # 문서의 1번째 페이지 내용 확인 (목차)


# 단계 2: 문서 분할(Split Documents)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50) # 청크 크기 설정: 500자, 겹치는 부분: 50자
split_documents = text_splitter.split_documents(docs)   # 청크 단위로 문서 분할
print(f"\nㅁ분할된 청크의수: {len(split_documents)}")   # 분할된 청크의 수 확인

# 단계 3: 임베딩(Embedding) 생성
embeddings = OpenAIEmbeddings()

# 단계 4: DB 생성(Create DB) 및 저장
vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings) # 벡터스토어 생성

for doc in vectorstore.similarity_search("구글"):   # 구글 관련 내용 출력
    print("구글 관련 내용 :",doc.page_content)
    
# 단계 5: 검색기(Retriever) 생성
retriever = vectorstore.as_retriever()  # 문서에 포함되어 있는 정보 검색 및 생성
retriever.invoke("삼성전자가 자체 개발한 AI 의 이름은?")    # 검색기에 쿼리를 날려 검색된 chunk 결과를 확인

# 단계 6: 프롬프트 생성(Create Prompt)
prompt = PromptTemplate.from_template(
    """You are an assistant for question-answering tasks. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. 
Answer in Korean.

#Context: 
{context}

#Question:
{question}

#Answer:"""
)

# 단계 7: 언어모델(LLM) 생성
llm = ChatOpenAI(model_name="gpt-4.1-mini", temperature=0)

# 단계 8: 체인(Chain) 생성
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 체인 실행(Run Chain) : 문서에 대한 질의를 입력하고, 답변을 출력합니다.
question = "삼성전자가 자체 개발한 AI 의 이름은?"
response = chain.invoke(question)
print(response)