import os
import streamlit as st
from openai import OpenAI
import plotly.graph_objects as go
import networkx as nx
import sqlite3
from datetime import datetime

# Initialize OpenAI client
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception as e:
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()

# Database setup for user authentication and progress tracking
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (user_id INTEGER, topic TEXT, progress FLOAT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shared_maps
                 (user_id INTEGER, topic TEXT, map_data TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

# Function to register a new user
def register_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()

# Function to authenticate a user
def authenticate_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    user_id = c.fetchone()
    conn.close()
    return user_id[0] if user_id else None

# Function to track user progress
def track_progress(user_id, topic, progress):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO progress (user_id, topic, progress, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, topic, progress, datetime.now()))
    conn.commit()
    conn.close()

# Function to generate a concept map with explanations for connections
def generate_concept_map_with_explanations(topic):
    prompt = f"Generate a list of key concepts related to {topic}, along with their relationships and explanations for how they are connected. Format: Concept -> Related Concept: Explanation"
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a concept mapping assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content
        concepts = content.split("\n")
        concept_map = []
        for concept in concepts:
            if "->" in concept:
                parts = concept.split(": ")
                if len(parts) == 2:
                    relationship, explanation = parts
                    concept1, concept2 = relationship.split(" -> ")
                    concept_map.append((concept1.strip(), concept2.strip(), explanation.strip()))
        return concept_map
    except Exception as e:
        st.error(f"Error generating concept map with OpenAI API: {e}")
        return []

# Function to generate an interactive network graph with Plotly
def generate_interactive_network_graph(concepts, topic):
    G = nx.Graph()
    for concept1, concept2, explanation in concepts:
        G.add_node(concept1)
        G.add_node(concept2)
        G.add_edge(concept1, concept2, description=explanation)
    pos = nx.spring_layout(G, seed=42)
    edge_traces = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace = go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=1, color='gray'),
            hoverinfo='text',
            text=G.edges[edge]['description'],
            mode='lines')
        edge_traces.append(edge_trace)
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(size=20, color='lightblue'),
        hoverinfo='text',
        textfont=dict(size=12))
    fig = go.Figure(data=edge_traces + [node_trace],
                    layout=go.Layout(
                        title=f"Concept Map: {topic}",
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
    return fig, G

# Function to get information about a node
def get_node_information(node, concepts):
    info = []
    for concept1, concept2, explanation in concepts:
        if node == concept1 or node == concept2:
            info.append(f"**{concept1} -> {concept2}:** {explanation}")
    return "\n".join(info)

# Function to generate quiz questions
def generate_quiz_questions(concepts):
    questions = []
    for concept1, concept2, explanation in concepts:
        question = f"What is the relationship between {concept1} and {concept2}?"
        answer = explanation
        questions.append((question, answer))
    return questions

# Function to share a concept map
def share_concept_map(user_id, topic, map_data):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO shared_maps (user_id, topic, map_data, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, topic, map_data, datetime.now()))
    conn.commit()
    conn.close()

# Streamlit UI for Interactive Visualization
def interactive_ui():
    st.title("AI-Driven Concept Mapper & Adaptive Learning Pathways")
    
    # Initialize session state variables
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'topic' not in st.session_state:
        st.session_state.topic = None
    if 'concepts' not in st.session_state:
        st.session_state.concepts = []
    if 'selected_node' not in st.session_state:
        st.session_state.selected_node = None
    if 'quiz_questions' not in st.session_state:
        st.session_state.quiz_questions = []
    if 'quiz_answers' not in st.session_state:
        st.session_state.quiz_answers = {}

    # User authentication
    st.sidebar.title("User Authentication")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user_id = authenticate_user(username, password)
        if user_id:
            st.sidebar.success("Logged in successfully!")
            st.session_state.user_id = user_id
        else:
            st.sidebar.error("Invalid username or password")
    
    if not st.session_state.user_id:
        st.write("Please log in to continue.")
        return
    
    # Main application
    topic = st.text_input("Enter a topic to generate a concept map:", value=st.session_state.topic or "")
    if st.button("Generate Concept Map") and topic:
        st.session_state.topic = topic
        with st.spinner("Generating Concept Map..."):
            st.session_state.concepts = generate_concept_map_with_explanations(topic)
            st.session_state.quiz_questions = generate_quiz_questions(st.session_state.concepts)
    
    if st.session_state.topic and st.session_state.concepts:
        st.subheader("Concept Map Visualization")
        
        # Display explanations for connections
        st.write("### Explanations for Connections")
        for concept1, concept2, explanation in st.session_state.concepts:
            st.write(f"**{concept1} -> {concept2}:** {explanation}")
        
        # Generate and display the interactive network graph
        st.subheader("Interactive Network Graph")
        fig, G = generate_interactive_network_graph(st.session_state.concepts, st.session_state.topic)
        st.plotly_chart(fig, use_container_width=True)

        # Handle node selection using a dropdown menu
        st.subheader("Select a Node to Explore")
        nodes = list(G.nodes())
        selected_node = st.selectbox("Choose a node", nodes, key="node_select")

        # Display information about the selected node
        if selected_node:
            st.subheader(f"Information about: {selected_node}")
            node_info = get_node_information(selected_node, st.session_state.concepts)
            st.write(node_info)

        # Progress Tracking
        st.subheader("Progress Tracking")
        progress = st.slider("How much of this topic have you completed?", 0, 100, 0, key="progress_slider")
        if st.button("Update Progress"):
            track_progress(st.session_state.user_id, st.session_state.topic, progress)
            st.success("Progress updated successfully!")

        # Collaborative Learning: Share the concept map
        st.subheader("Collaborative Learning")
        if st.button("Share Concept Map"):
            share_concept_map(st.session_state.user_id, st.session_state.topic, str(st.session_state.concepts))
            st.success("Concept map shared successfully!")

        # Interactive Quiz
        st.subheader("Interactive Quiz")
        if st.session_state.quiz_questions:
            for i, (question, answer) in enumerate(st.session_state.quiz_questions):
                st.write(f"**Question {i + 1}:** {question}")
                user_answer = st.text_input(f"Your answer for Question {i + 1}:", key=f"quiz_answer_{i}")
                if user_answer:
                    st.session_state.quiz_answers[i] = user_answer
            if st.button("Submit Quiz"):
                correct_answers = 0
                for i, (question, answer) in enumerate(st.session_state.quiz_questions):
                    if st.session_state.quiz_answers.get(i, "").strip().lower() == answer.lower():
                        correct_answers += 1
                st.write(f"**Quiz Results:** You got {correct_answers} out of {len(st.session_state.quiz_questions)} correct!")
        else:
            st.write("No quiz questions available yet. Generate a concept map first.")

        # Chat Assistance
        st.subheader("Chat Assistance")
        user_input = st.text_input("Ask a question about the topic:", key="chat_input")
        if user_input:
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_input}
                    ]
                )
                st.write(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Error generating response: {e}")

if __name__ == '__main__':
    init_db()
    interactive_ui()