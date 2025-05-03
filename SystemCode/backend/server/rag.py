import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
from dotenv import load_dotenv
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_core.output_parsers import StrOutputParser
from typing import Tuple, List, Dict
from pydantic import BaseModel, Field
from predefined_queries_graph_like import get_queries_dict

queries_dict = get_queries_dict()

print("🟢 [RAG] Initializing RAG system...")

class Entities(BaseModel):
    """Identifying information about entities."""
    venue_type: str = Field(
        None,
        description="The venue type mentioned in the text. Must be one of: ARTS, APPAREL, CAFE, CLUBS, DOCTOR, RESTAURANT, SHOPPING, PERSONAL_CARE, SCHOOL, VEHICLE, SPORTS_COMPLEX. Return None if no valid venue type is found."
    )
    planning_area: str = Field(
        None,
        description="The Singapore subzone / planning area mentioned in the text (e.g., Ang Mo Kio, Bedok, etc.). Return None if no subzone /planning area is found."
    )

class IntentClassifier:
    def __init__(self, llm, queries_dict):
        print("🟢 [RAG] Initializing Intent Classifier...")
        self.llm = llm
        self.queries_dict = queries_dict
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for a business location advisor system. 
Your task is to classify the user's question into one or more of these exact intents.
You MUST use the exact phrases below, as they map directly to database queries.
Do not modify or paraphrase these intents.

Available intents:
- competitor information in given planning area
- competitor information of given business type in 5 planning areas with highest competitor scores
- competitor information of given business type in given planning area
- population statistics in given planning area
- age distribution in given planning area
- housing profile in given planning area
- average property pricing by property type in given planning area
- available properties in given planning area
- location suggestion given a business type
- business type suggestion given a planning area
- business advice for given venue type at given planning area

Important Classification Rules:
1. If the user asks about opening/starting a specific business type in a specific location (e.g., "Can I open a cafe in Clementi?"), use "business advice for given venue type at given planning area"
2. If the user asks about what business to open in a location WITHOUT specifying a business type, use "business type suggestion given a planning area"
3. If the user asks about where to open a specific business type WITHOUT specifying a location, use "location suggestion given a business type"

Return ONLY the exact matching intent(s) from the list above, separated by commas if multiple intents match.
Do not include any other text in your response."""),
            ("human", "{question}")
        ])
        
    def classify_intent(self, question: str) -> str:
        print(f"🟢 [RAG] Classifying intent for question: {question[:50]}...")
        response = self.intent_prompt | self.llm | StrOutputParser()
        intent = response.invoke({"question": question}).lower().strip()
        print(f"🟢 [RAG] Classified intent: {intent}")
        return intent

    def get_matching_queries(self, intent: str) -> List[str]:
        """Get all matching queries for a given intent"""
        # Split intents if multiple were returned
        intents = [i.strip() for i in intent.split(',')]
        matching_queries = []
        
        for i in intents:
            if i in self.queries_dict:
                matching_queries.append(self.queries_dict[i])
            else:
                print(f"🟢 [RAG] Warning: Intent '{i}' not found in queries dictionary")
        
        return matching_queries

def build_rag_chain(llm):
    print("🟢 [RAG] Building RAG chain...")
    # Extract entities from text
    queries_dict = get_queries_dict()
    intent_classifier = IntentClassifier(llm, queries_dict)

    # Retrieve Neo4j config variables
    load_dotenv()
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    print("🟢 [RAG] Connecting to Neo4j database...")
    # Get knowledge graph from neo4j instance
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD
    )

    # Build an entity chain that extracts entities in KG from text
    print("🟢 [RAG] Creating fulltext index of all entities if not exists...")
    graph.query(
        """CREATE FULLTEXT INDEX entity_index IF NOT EXISTS
        FOR (n:PlanningArea|VenueType|Competitor|AgeDistribution|HousingProfile|PopulationStats)
        ON EACH [n.subzone, n.type_name, n.venue_name]"""
    )

    print("🟢 [RAG] Creating fulltext index of planning area entities if not exists...")
    graph.query(
        """CREATE FULLTEXT INDEX planning_area_index IF NOT EXISTS
        FOR (n:PlanningArea)
        ON EACH [n.subzone]"""
    )

    print("🟢 [RAG] Creating fulltext index of venue type entities if not exists...")
    graph.query(
        """CREATE FULLTEXT INDEX venue_type_index IF NOT EXISTS
        FOR (n:VenueType)
        ON EACH [n.type_name]"""
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are extracting specific entities from user queries about business locations in Singapore.

For venue types, you must ONLY extract one of these exact values (case-sensitive):
- ARTS
- APPAREL
- CAFE
- CLUBS
- DOCTOR
- RESTAURANT
- SHOPPING
- PERSONAL_CARE
- SCHOOL
- VEHICLE
- SPORTS_COMPLEX

For planning areas, extract Singapore planning area names (e.g., Ang Mo Kio, Bedok, Tampines, etc.).

Return None for any field where a valid value is not found in the text.
Do not modify, paraphrase, or create new venue types."""
            ),
            (
                "human",
                "Extract the venue type and planning area from this text: {question}"
            ),
        ]
    )

    entity_chain = prompt | llm.with_structured_output(Entities)

    def _format_chat_history(chat_history: List[Tuple[str, str]]) -> str:
        """Format chat history into a string format"""
        if not chat_history:
            return ""
        formatted_history = "\nChat History:\n"
        for human, ai in chat_history:
            formatted_history += f"Human: {human}\nAssistant: {ai}\n"
        return formatted_history

    def extract_entities_from_history(chat_history: List[Tuple[str, str]]) -> Tuple[str, str]:
        """Extract the most recent venue type and planning area from chat history"""
        if not chat_history:
            return None, None
            
        # Combine all messages for entity extraction
        combined_text = " ".join([f"{human} {ai}" for human, ai in chat_history])
        try:
            entities = entity_chain.invoke({"question": combined_text})
            return entities.venue_type, entities.planning_area
        except Exception as e:
            print(f"🟢 [RAG] Error extracting entities from history: {str(e)}")
            return None, None

    def structured_retriever(input_data) -> str:
        """Execute query and return formatted results"""
        try:
            # Handle both string and dict inputs
            question = input_data if isinstance(input_data, str) else input_data.get("question", "")
            chat_history = input_data.get("chat_history", []) if isinstance(input_data, dict) else []
            
            # First classify the intent
            intent = intent_classifier.classify_intent(question)
            print(f"🟢 [RAG] Classified intent: {intent}")
            
            # Split intents if multiple were returned
            intents = [i.strip() for i in intent.split(',')]
            all_results = []
            
            # Process each intent separately
            for current_intent in intents:
                print(f"🟢 [RAG] Processing intent: {current_intent}")
                
                # Get query templates for this intent
                query_templates = intent_classifier.get_matching_queries(current_intent)
                if not query_templates:
                    print(f"🟢 [RAG] No query templates found for intent: {current_intent}")
                    continue
                
                # Extract entities from current question
                current_entities = entity_chain.invoke({"question": question})
                
                # If entities are missing, try to get them from chat history
                if (not current_entities.venue_type or not current_entities.planning_area) and chat_history:
                    history_venue_type, history_planning_area = extract_entities_from_history(chat_history)
                    
                    # Use historical entities if current ones are missing
                    if not current_entities.venue_type:
                        current_entities.venue_type = history_venue_type
                    if not current_entities.planning_area:
                        current_entities.planning_area = history_planning_area
                
                # Prepare parameters based on intent type
                if (
                    "business advice for given venue type at given planning area" in current_intent
                    or "competitor information of given business type in given planning area" in current_intent
                ):
                    params = {
                        "venue_type_query": current_entities.venue_type,
                        "planning_area_query": current_entities.planning_area
                    }
                else:
                    # Special-case the two “suggestion” intents so we pick the right entity:
                    if current_intent == "business type suggestion given a planning area":
                        # user wants “what business should I open in Tanjong Pagar?”
                        query_field = current_entities.planning_area
                    elif current_intent == "location suggestion given a business type":
                        # user wants “where should I open a coffee shop?”
                        query_field = current_entities.venue_type
                    else:
                        # all other single-entity intents:
                        #   if it mentions “business type”/“venue type” pull venue_type, otherwise planning_area
                        if any(k in current_intent for k in ["business type", "venue type"]):
                            query_field = current_entities.venue_type
                        else:
                            query_field = current_entities.planning_area
                    params = {"query": query_field or ""}
                
                # Execute queries for this intent
                for query_template in query_templates:
                    print(f"🟢 [RAG] Executing query with params: {params}")
                    response = graph.query(query_template, params)
                    
                    if not response:
                        print(f"🟢 [RAG] No response from query for intent: {current_intent}")
                        continue
                        
                    # Handle different response formats
                    for result in response:
                        if result is None:
                            print(f"🟢 [RAG] Skipping None result for intent: {current_intent}")
                            continue
                            
                        try:
                            if isinstance(result, dict):
                                if 'output' in result:
                                    output = result['output']
                                    if output is not None:
                                        all_results.append(str(output))
                                else:
                                    # If no 'output' key, try to convert the whole dict
                                    all_results.append(str(result))
                            elif isinstance(result, str):
                                all_results.append(result)
                            else:
                                # For any other type, try to convert to string
                                all_results.append(str(result))
                        except Exception as e:
                            print(f"🟢 [RAG] Error processing result for intent {current_intent}: {str(e)}")
                            continue
            
            if not all_results:
                print("🟢 [RAG] No valid results found in Neo4j")
                return "No relevant information found."
                
            return "\n".join(all_results)
        except Exception as e:
            print(f"🟢 [RAG] Error in structured retriever: {str(e)}")
            return f"Error retrieving information: {str(e)}"

    # Define RAG chain
    print("🟢 [RAG] Setting up RAG chain components...")
    
    # Define the condense question prompt
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(
        """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question.
        IMPORTANT: Make sure to preserve any mentions of business types (ARTS, APPAREL, CAFE, CLUBS, DOCTOR, RESTAURANT, SHOPPING, PERSONAL_CARE, SCHOOL, VEHICLE, SPORTS_COMPLEX) 
        and Singapore planning area names from either the chat history or the follow-up question.
        
        Chat History:
        {chat_history}
        
        Follow Up Input: {question}
        
        Rephrase as a standalone question, keeping all relevant business types and planning areas mentioned in either the history or follow-up:"""
    )

    _search_query = RunnableBranch(
        (
            RunnableLambda(lambda x: bool(x.get("chat_history"))).with_config(
                run_name="HasChatHistoryCheck"
            ),
            RunnablePassthrough.assign(
                chat_history=lambda x: _format_chat_history(x["chat_history"])
            )
            | CONDENSE_QUESTION_PROMPT
            | ChatOpenAI(temperature=0)
            | StrOutputParser(),
        ),
        RunnableLambda(lambda x: x["question"]),
    )

    template = """Answer the question based on the following context and chat history:
    {context}
    {chat_history}

    Question: {question}
    Intent: {intent}
    Use natural language and be concise.
    Perform detailed reasoning based on the questions and each aspects of the context. 
    Do provide values to support your reasoning. If no results were returned from the context, add a disclaimer stating due to no data found in system knowledge base, the response / reasoning was performed based on general knowledge.
    If referring to previous context from chat history, explicitly mention it. 
    Note: overall_score is an overall measurement consists of different criteria such as competitors, demographics, underserved score and etc.
    Answer:"""
    prompt = ChatPromptTemplate.from_template(template)

    print("🟢 [RAG] Building final chain...")
    chain = (
        RunnableParallel(
            {
                "context": _search_query | structured_retriever,
                "question": RunnablePassthrough(),
                "chat_history": lambda x: _format_chat_history(x.get("chat_history", [])),
                "intent": RunnableLambda(lambda x: intent_classifier.classify_intent(x["question"]))
            }
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    print("🟢 [RAG] Chain built successfully")
    return chain

def invoke_rag_chain(llm, question: str, chat_history: List[Tuple[str, str]] = None) -> str:
    """Execute the RAG chain with error handling"""
    try:
        print("\n🟢 [RAG] Invoking RAG chain...")
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")
        
        rag_chain = build_rag_chain(llm=llm)
        print("🟢 [RAG] Chain built, processing question...")
        rag_response = rag_chain.invoke({"question": question, "chat_history": chat_history or []})
        print("🟢 [RAG] Response generated successfully")
        return rag_response
    except Exception as e:
        print(f"🟢 [RAG] Error in RAG chain: {str(e)}")
        return f"Error processing question: {str(e)}"
