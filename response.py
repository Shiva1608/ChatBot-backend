
user_id = 1000
from helper_functions import load_faiss_vector_db,query_retrieval_qa

vect_db = load_faiss_vector_db(user_id)
query = "give me the certifications of sriram vasudeven?"
category = "LINKEDIN"  # Optional; if no category, pass None
# category = None 
output = query_retrieval_qa(query,category,vect_db)
print(output)