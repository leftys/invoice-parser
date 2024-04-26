import shutil
import tempfile
from typing import List, Optional, IO

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from pydantic.v1 import BaseModel


class Invoice(BaseModel):
    id: str
    date: str
    description: str
    tax_rate: Optional[float]
    total_amount: float
    currency: str
    supplier_name: str
    invoice_language: str
    variabilni_symbol: Optional[str]


class ExtracterAgent:
    output_parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Invoice)

    def __init__(self, openai_api_key) -> None:
        self._openai_api_key = openai_api_key

    def parse_pdf_inputs(self, uploaded_files: List[IO]):
        parded_pdf = []
        for file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                shutil.copyfileobj(file, tmp)
            pdf_loader = PyPDFLoader(tmp.name)
            pdf_reader = pdf_loader.load()
            parded_pdf.append(pdf_reader)
        return parded_pdf

    def create_prompt(self):
        sys_template = """You are expert at data extraction. You tasked to extract data from given tax invoice.
Use dates in iso format and currencies in 3 letter codes.
Invoice description should not be over 50 characters long.
Only invoices in Czech language have variabilni symbol and it is number, invoices in English have it missing.
My company, Maker Technologies, is never the supplier.
"""
        prompt = ChatPromptTemplate.from_messages(
            [("system", sys_template), ("human", "{pdf_input}")]
        ).partial(format_instruction=self.output_parser.get_format_instructions())
        return prompt

    def create_chain(self):
        llm = ChatOpenAI(model="gpt-3.5-turbo",
                         api_key=self._openai_api_key)
        prompt = self.create_prompt()
        chain = (
            {"pdf_input": RunnablePassthrough()}
            | prompt
            | llm.with_structured_output(schema=Invoice)
        )
        return chain

    def run_agent(self, pdfs: List[IO]) -> List[Invoice]:
        loaded_files = self.parse_pdf_inputs(pdfs)
        chain = self.create_chain()
        llm_res = chain.batch(loaded_files)
        return llm_res
