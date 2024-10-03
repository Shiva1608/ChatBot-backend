from flask import Flask, request, jsonify
# from flask_mysqldb import MySQL
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_cors import CORS
from helper_functions import (
    extract_content_from_url,
    generate_number_from_input,
    convert_to_langchain_document,
    split_documents_into_chunks,
    map_chat_num_to_uuids,
    manage_faiss_index, get_youtube_video_details,
    parse_pdf,
    concatenate_document_text, load_faiss_vector_db, query_retrieval_qa
)
from model import db

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
db.init_app(app)
app.app_context().push()

DATABASE = './instance/database.sqlite3'


@app.route('/update_url_vdb', methods=['POST'])
def update_url_vdb():
    # try:
    # Parse request body
    data = request.get_json()
    url = data.get("url")
    user_id = data.get("user_id")
    category = data.get("category")

    if not url or not user_id or not category:
        return jsonify({"error": "Missing one or more required parameters: url, user_id, category"}), 400

    # Step 1: Extract content from the URL
    scraped_data = extract_content_from_url(url)

    # Step 2: Generate a unique number from the URL
    unique_number = generate_number_from_input(url)

    # Step 3: Convert the scraped data into a LangChain document
    document = convert_to_langchain_document(scraped_data, url, category, unique_number)

    # Step 4: Split documents into chunks
    docs = split_documents_into_chunks(document)

    # Step 5: Map chat_num to UUIDs
    ids = map_chat_num_to_uuids(docs)[0]
    chat_num_uuid_mapping = map_chat_num_to_uuids(docs)[1]

    # Step 6: Manage the FAISS index for the given user_id
    vector_db = manage_faiss_index(user_id, docs, ids)

    # Return a successful response
    return jsonify({
        "message": "FAISS vector database updated successfully.",
        "user_id": user_id,
        "url": url,
        "category": category,
        "uuid_mapping": chat_num_uuid_mapping
    }), 200

    # except Exception as e:
    #     return jsonify({"error": str(e)}), 500


@app.route('/update_yt_url_vdb', methods=['POST'])
def update_yt_url_vdb():
    try:
        # Get data from request body
        data = request.get_json()
        url = data.get('url')
        user_id = data.get('user_id')
        category = data.get('category')

        if not url or not user_id or not category:
            return jsonify({"error": "url, user_id, and category are required fields."}), 400

        # Fetch YouTube video details
        document_content = get_youtube_video_details(url)

        if document_content.startswith("Please provide"):
            return jsonify({"error": document_content}), 400

        # Generate unique number based on input
        unique_number = generate_number_from_input(url)

        # Convert document content to LangChain document
        document = convert_to_langchain_document(document_content, url, category, unique_number)

        # Split the document into chunks
        docs = split_documents_into_chunks(document)

        # Map documents to UUIDs
        ids, chat_num_uuid_mapping = map_chat_num_to_uuids(docs)

        # Manage FAISS vector index
        vector_db = manage_faiss_index(user_id, docs, ids)

        # Return the success response
        return jsonify({
            "message": "FAISS vector database updated successfully.",
            "user_id": user_id,
            "url": url,
            "category": category,
            "uuid_mapping": chat_num_uuid_mapping
        }), 200

    except Exception as e:
        # Handle any exceptions and return an error message
        return jsonify({"error": str(e)}), 500


@app.route('/update_pdf_vdb', methods=['POST'])
def update_pdf_vdb():
    # try:
    # Get data from request body
    if 'file' not in request.files:
        print(1)
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    print(file)

    if file.filename == '':
        print(2)
        return jsonify({'error': 'No selected file'}), 400

    if file:
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(pdf_path)

    # user_id = data.get('user_id')
    # category = data.get('category')
    user_id = 1004
    category = "Resume"

    if not pdf_path or not user_id or not category:
        print(3)
        return jsonify({"error": "pdf_path, user_id, and category are required fields."}), 400

    # Parse the PDF
    document = parse_pdf(pdf_path)
    pdf_name = document[0]
    content = concatenate_document_text(document[1])

    # Generate unique number based on PDF name
    unique_number = generate_number_from_input(pdf_name)

    # Convert content to LangChain document
    doc = convert_to_langchain_document(content, pdf_name, category, unique_number)

    # Split the document into chunks
    docs = split_documents_into_chunks(doc)

    # Map documents to UUIDs
    ids, chat_num_uuid_mapping = map_chat_num_to_uuids(docs)

    # Manage FAISS vector index
    vector_db = manage_faiss_index(str(user_id), docs, ids)

    # Return the success response
    return jsonify({
        "message": "FAISS vector database updated successfully.",
        "user_id": user_id,
        "source": pdf_name,
        "category": category,
        "uuid_mapping": chat_num_uuid_mapping
    }), 200

    # except Exception as e:
    #     # Handle any exceptions and return an error message
    #     return jsonify({"error": str(e)}), 500


@app.route('/response', methods=['POST'])
def get_response():
    """
    Flask route to process a query with a FAISS retriever based on user_id and category.
    """
    try:
        # Get parameters from the request
        data = request.get_json()
        user_id = data.get('user_id')
        query = data.get('query')
        category = data.get('category', None)  # Optional, default to None
        print(category)
        if not user_id or not query:
            return jsonify({"error": "user_id and query are required fields"}), 400

        # Load FAISS vector database for the given user_id
        vect_db = load_faiss_vector_db(user_id)

        # Run the query retrieval
        output = query_retrieval_qa(query, category, vect_db)

        # Return the output as JSON
        return jsonify(output), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_chat")
def get_chat():
    user_id = request.args.get("userid")
    if not user_id:
        return jsonify({"error": "userid is required"}), 400
    connection = sqlite3.connect(DATABASE)
    if connection:
        cursor = connection.cursor()
        select_query = "SELECT chat_id FROM chat WHERE user_id = ?"
        cursor.execute(select_query, (user_id, ))
        chat = cursor.fetchall()
        res = []
        for index, id in enumerate(chat):
            res.append({"id": index + 1, "chat_id": id[0]})
        return jsonify(res)
    else:
        return jsonify({"error": "Failed to connect to the database"}), 500


@app.route("/get_current_chat")
def get_current_chat():
    user_id = request.args.get("userid")
    chat_id = request.args.get("chatid")
    print(user_id, chat_id)
    if not user_id or not chat_id:
        return jsonify({"error": "userid and chatid are required"}), 400
    connection = sqlite3.connect(DATABASE)
    if connection:
        cursor = connection.cursor()
        select_query = "SELECT uid, question, answer, time_stamp FROM chat_history WHERE user_id = ? AND chat_id = ?"
        cursor.execute(select_query, (user_id, chat_id))
        chat = cursor.fetchall()
        res = []
        for msg in chat:
            res.append({
                "id": msg[0],
                "question": msg[1],
                "answer": msg[2],
                "timestamp": msg[3]
            })
        return jsonify(res)
    else:
        return jsonify({"error": "Failed to connect to the database"}), 500


@app.route("/voice", methods=["POST"])
def text_to_voice():
    data = request.json['inputText']
    


@app.route('/store_chat', methods=['POST'])
def store_chat():
    # Extract data from the incoming JSON request
    data = request.json
    user_id = data['user_id']
    chat_id = data['chat_id']
    question = data['question']
    answer = data['answer']

    # Validate that all required fields are provided
    if not user_id or not chat_id or not question or not answer:
        return jsonify({"error": "user_id, question, and answer are required"}), 400

    # Store the chat in the database
    connection = sqlite3.connect(DATABASE)
    if connection:
        # try:
        cursor = connection.cursor()
        select_query = "SELECT chat_id FROM chat WHERE user_id = ? AND chat_id = ?"
        cursor.execute(select_query, (user_id, chat_id))
        chat = cursor.fetchone()

        if not chat:
            insert_query1 = """
                        INSERT INTO chat (user_id, chat_id)
                        VALUES (?, ?)
                    """
            cursor.execute(insert_query1, (user_id, chat_id))
            connection.commit()
        # Insert query to store the question, response, and timestamp
        insert_query = """
            INSERT INTO chat_history (user_id, chat_id, question, answer, time_stamp)
            VALUES (?, ?, ?, ?, ?)
        """
        time_now = datetime.now()
        cursor.execute(insert_query, (user_id, chat_id, question, answer, time_now))
        connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Return a success message
        return jsonify({"message": "Chat stored successfully"}), 201
        # except Exception as e:
        #     return jsonify({"error": f"Database error: {e}"}), 500
    else:
        return jsonify({"error": "Failed to connect to the database"}), 500


# Signup API function
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    # Hash the password before storing it in the database
    hashed_password = generate_password_hash(password)

    connection = sqlite3.connect(DATABASE)
    if connection:
        #     try:
        cursor = connection.cursor()

        # Insert new user data into the users table
        insert_query = """
            INSERT INTO users (username, email, password) 
            VALUES (?, ?, ?)
        """
        cursor.execute(insert_query, (username, email, hashed_password))
        connection.commit()

        select_query = "SELECT user_id FROM users WHERE email = ?"
        cursor.execute(select_query, (email,))
        user = cursor.fetchone()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return jsonify({"message": "User registered successfully", "user_id": user[0]}), 201
        # except sqlite3.IntegrityError:  # This handles the case of duplicate emails
        #     return jsonify({"error": "Email already exists"}), 409
        # except Exception as e:
        #     return jsonify({"error": f"Database error: {e}"}), 500
    else:
        return jsonify({"error": "Failed to connect to the database"}), 500


# Login API function
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    connection = sqlite3.connect(DATABASE)
    if connection:
        try:
            cursor = connection.cursor()

            # Retrieve the user with the given email
            select_query = "SELECT user_id, password FROM users WHERE email = ?"
            cursor.execute(select_query, (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                return jsonify({"message": "Login successful", "user_id": user[0]}), 200
            else:
                return jsonify({"error": "Invalid email or password"}), 401
        except Exception as e:
            return jsonify({"error": f"Database error: {e}"}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({"error": "Failed to connect to the database"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
