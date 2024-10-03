from helper_functions import (parse_pdf ,concatenate_document_text,
                              generate_number_from_input,convert_to_langchain_document,
                              split_documents_into_chunks,map_chat_num_to_uuids,manage_faiss_index)

path = "E:/EQUITY RESEARCH ANALYSIS TOOL UPDATED/pdf1/central limit theorem.pdf"
document = parse_pdf(path)
pdf_name = document[0]


content = concatenate_document_text(document[1])
unique_number = generate_number_from_input(pdf_name)

category = "PDF"
doc = convert_to_langchain_document(content,pdf_name,category,unique_number)

docs = split_documents_into_chunks(doc)
ids = map_chat_num_to_uuids(docs)[0]
chat_num_uuid_mapping = map_chat_num_to_uuids(docs)[1]
user_id = 100
vector_db = manage_faiss_index(user_id, docs, ids)
print(docs)