from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3
import csv
import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import json
from openai_service import FUNCTIONS, execute_function_call
from collections import defaultdict

# Load environment variables
load_dotenv()  # Load from current directory
load_dotenv('../.env')  # Also try to load from parent directory (root)

app = Flask(__name__)
CORS(app)  # Allow all origins for local development

# Configure OpenAI client (new API)

print(f"🔍 Debug: API key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"🔍 Debug: API key starts with: {api_key[:10]}...")
    print(f"🔍 Debug: API key length: {len(api_key)}")
    client = OpenAI(api_key=api_key)
    print("✅ OpenAI client initialized (new API)")
else:
    print("❌ No API key found in environment variables")
    print("💡 Please create a .env file in the root directory with:")
    print("   OPENAI_API_KEY=your_api_key_here")
    print("💡 Or set the environment variable directly:")
    print("   $env:OPENAI_API_KEY='your_api_key_here'")
    client = None

# Database setup
DATABASE_PATH = os.getenv('DATABASE_PATH', './water_quality.db')

# In-memory session memory (cleared on backend restart)
session_histories = defaultdict(list)

def init_database():
    """Initialize SQLite database with water quality data"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Load CSV files into SQLite tables
    csv_files = [
        'SDWA_PUB_WATER_SYSTEMS.csv',
        'SDWA_VIOLATIONS_ENFORCEMENT.csv',
        'SDWA_LCR_SAMPLES.csv',
        'SDWA_FACILITIES.csv',
        'SDWA_SITE_VISITS.csv',
        'SDWA_GEOGRAPHIC_AREAS.csv',
        'SDWA_EVENTS_MILESTONES.csv',
        'SDWA_SERVICE_AREAS.csv',
        'SDWA_PN_VIOLATION_ASSOC.csv',
        'SDWA_REF_CODE_VALUES.csv'
    ]
    
    for csv_file in csv_files:
        file_path = f'../data/{csv_file}'
        if os.path.exists(file_path):
            table_name = csv_file.replace('.csv', '').lower()
            
            # Read CSV and create table
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)
                
                # Create table
                columns = ', '.join([f'"{col}" TEXT' for col in headers])
                cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
                cursor.execute(f'CREATE TABLE {table_name} ({columns})')
                
                # Insert data
                for row in csv_reader:
                    if len(row) == len(headers):  # Ensure row has correct number of columns
                        placeholders = ', '.join(['?' for _ in headers])
                        cursor.execute(f'INSERT INTO {table_name} VALUES ({placeholders})', row)
            
            print(f"Loaded {csv_file} into {table_name} table")
    
    conn.commit()
    conn.close()

def get_water_quality_context():
    """Get context about water quality data for OpenAI"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get summary statistics
    stats = {}
    
    # Water systems
    cursor.execute("SELECT COUNT(*) as total_systems, COUNT(CASE WHEN PWS_ACTIVITY_CODE = 'A' THEN 1 END) as active_systems FROM sdwa_pub_water_systems")
    result = cursor.fetchone()
    stats['total_systems'] = result[0] if result else 0
    stats['active_systems'] = result[1] if result else 0
    
    # Violations
    cursor.execute("SELECT COUNT(*) as total_violations, COUNT(CASE WHEN IS_HEALTH_BASED_IND = 'Y' THEN 1 END) as health_violations FROM sdwa_violations_enforcement")
    result = cursor.fetchone()
    stats['total_violations'] = result[0] if result else 0
    stats['health_violations'] = result[1] if result else 0
    
    # Samples
    cursor.execute("SELECT COUNT(*) as total_samples FROM sdwa_lcr_samples")
    result = cursor.fetchone()
    stats['total_samples'] = result[0] if result else 0
    
    # Counties
    cursor.execute("SELECT COUNT(DISTINCT COUNTY_SERVED) as counties FROM sdwa_geographic_areas WHERE AREA_TYPE_CODE = 'CN'")
    result = cursor.fetchone()
    stats['counties'] = result[0] if result else 0
    
    conn.close()
    
    return f"""
    Georgia Water Quality Data Context:
    - {stats['total_systems']} total water systems ({stats['active_systems']} active)
    - {stats['total_violations']} total violations ({stats['health_violations']} health-based)
    - {stats['total_samples']} lead/copper samples
    - {stats['counties']} counties covered
    
    Available data tables:
    - sdwa_pub_water_systems: Water system details, contact info, population served
    - sdwa_violations_enforcement: Violations, enforcement actions, compliance status
    - sdwa_lcr_samples: Lead and copper sampling results
    - sdwa_facilities: Water system facilities (wells, treatment plants, etc.)
    - sdwa_site_visits: Regulatory inspections and evaluations
    - sdwa_geographic_areas: Geographic coverage (counties, cities)
    - sdwa_events_milestones: Compliance milestones and events
    - sdwa_service_areas: Service area definitions
    - sdwa_pn_violation_assoc: Public notification violations
    - sdwa_ref_code_values: Reference codes and descriptions
    """

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot conversations with OpenAI using function calling"""
    try:
        if not client:
            return jsonify({
                'response': "I'm sorry, but the AI chat functionality is currently unavailable. Please check your OpenAI API key.",
                'timestamp': datetime.now().isoformat()
            }), 200
        
        data = request.get_json()
        user_message = data.get('message', '')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Use session ID from cookie or default
        session_id = request.cookies.get('session_id', 'default')
        history = session_histories[session_id]
        
        # Create system prompt
        system_prompt = """
You are a helpful, friendly, and conversational assistant for Georgia water quality data. Always use the provided database functions to get REAL data from Georgia's water systems.

Respond in a clear, engaging, and conversational style, like ChatGPT.
Use markdown formatting for lists, tables, and emphasis.
If the user includes math or requests formulas, use LaTeX (in markdown, e.g., $E=mc^2$ or $$a^2 + b^2 = c^2$$).
If the user's question is ambiguous, ask for clarification.
Always explain your reasoning, highlight important trends, and suggest possible next questions if relevant.
"""
        # Add user message to history
        history.append({"role": "user", "content": user_message})
        # Build messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}] + history
        # First call to OpenAI with function calling
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=FUNCTIONS,
            tool_choice="auto",
            max_tokens=1000,
            temperature=0.7
        )
        response_message = completion.choices[0].message
        # Check if OpenAI wants to call a function
        if response_message.tool_calls:
            messages.append(response_message)
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                function_result = execute_function_call(function_name, function_args)
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(function_result)
                })
            # Add a follow-up message to encourage reasoning and suggestions
            messages.append({
                "role": "user",
                "content": "Please explain the significance of this data, highlight any trends, and suggest what a user might want to know next."
            })
            # Second call to OpenAI with function results
            second_completion = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            bot_response = second_completion.choices[0].message.content
        else:
            bot_response = response_message.content
        # Add assistant response to history
        history.append({"role": "assistant", "content": bot_response})
        session_histories[session_id] = history
        return jsonify({
            'response': bot_response,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'response': f"I'm sorry, but I encountered an error while processing your request: {str(e)}. Please try again later.",
            'timestamp': datetime.now().isoformat()
        }), 200

@app.route('/api/water-systems', methods=['GET'])
def get_water_systems():
    """Get water systems with optional filtering"""
    try:
        county = request.args.get('county')
        city = request.args.get('city')
        limit = request.args.get('limit', 50)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT DISTINCT p.PWSID, p.PWS_NAME, p.POPULATION_SERVED_COUNT, 
               p.PWS_TYPE_CODE, p.PWS_ACTIVITY_CODE, p.CITY_NAME, p.STATE_CODE
        FROM sdwa_pub_water_systems p
        LEFT JOIN sdwa_geographic_areas g ON p.PWSID = g.PWSID
        WHERE p.PWS_ACTIVITY_CODE = 'A'
        """
        
        params = []
        if county:
            query += " AND g.COUNTY_SERVED = ?"
            params.append(county)
        if city:
            query += " AND p.CITY_NAME LIKE ?"
            params.append(f'%{city}%')
        
        query += " ORDER BY p.POPULATION_SERVED_COUNT DESC LIMIT ?"
        params.append(int(limit))
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/violations', methods=['GET'])
def get_violations():
    """Get violations for a specific water system"""
    try:
        pwsid = request.args.get('pwsid')
        if not pwsid:
            return jsonify({'error': 'PWSID required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT v.VIOLATION_ID, v.VIOLATION_CODE, v.VIOLATION_CATEGORY_CODE,
               v.IS_HEALTH_BASED_IND, v.CONTAMINANT_CODE, v.VIOLATION_STATUS,
               v.NON_COMPL_PER_BEGIN_DATE, v.NON_COMPL_PER_END_DATE,
               v.VIOL_MEASURE, v.UNIT_OF_MEASURE, v.FEDERAL_MCL
        FROM sdwa_violations_enforcement v
        WHERE v.PWSID = ?
        ORDER BY v.NON_COMPL_PER_BEGIN_DATE DESC
        LIMIT 50
        """
        
        cursor.execute(query, [pwsid])
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/samples', methods=['GET'])
def get_samples():
    """Get lead/copper samples for a specific water system"""
    try:
        pwsid = request.args.get('pwsid')
        if not pwsid:
            return jsonify({'error': 'PWSID required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT s.SAMPLE_ID, s.CONTAMINANT_CODE, s.SAMPLE_MEASURE,
               s.UNIT_OF_MEASURE, s.SAMPLING_START_DATE, s.SAMPLING_END_DATE
        FROM sdwa_lcr_samples s
        WHERE s.PWSID = ?
        ORDER BY s.SAMPLING_END_DATE DESC
        LIMIT 50
        """
        
        cursor.execute(query, [pwsid])
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/counties', methods=['GET'])
def get_counties():
    """Get list of counties with water systems"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT DISTINCT COUNTY_SERVED, COUNT(*) as system_count
        FROM sdwa_geographic_areas
        WHERE AREA_TYPE_CODE = 'CN' AND COUNTY_SERVED IS NOT NULL
        GROUP BY COUNTY_SERVED
        ORDER BY system_count DESC
        """
        
        cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Initialize database on first run
    if not os.path.exists(DATABASE_PATH):
        print("Initializing database...")
        init_database()
        print("Database initialized successfully!")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 