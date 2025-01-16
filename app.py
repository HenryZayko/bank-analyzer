from flask import Flask, request, jsonify
from flask_cors import CORS
from bank_statement_analyzer import BankStatementAnalyzer
import os
import tempfile

app = Flask(__name__)

# Enable CORS with more specific configuration
CORS(app, resources={
    r"/analyze": {
        "origins": ["http://localhost:3000"],  # Explicitly allow React dev server
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "max_age": 120  # Cache preflight requests for 2 minutes
    },
    r"/test": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET"]
    }
})

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze_statement():
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'POST'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    try:
        print("Received request")
        print("Request method:", request.method)
        print("Headers:", dict(request.headers))
        print("Files:", request.files)
        print("Form data:", request.form)
        
        if 'file' not in request.files:
            print("No file found in request")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if not file.filename:
            print("No filename")
            return jsonify({'error': 'No file selected'}), 400
            
        print(f"Received file: {file.filename}")
        
        # Check if file is PDF
        if not file.filename.lower().endswith('.pdf'):
            print("Not a PDF file")
            return jsonify({'error': 'File must be a PDF'}), 400
        
        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        print(f"Saved file to: {temp_path}")
        
        # Get API key from environment variable
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("No API key provided. Set ANTHROPIC_API_KEY environment variable")
        
        # Analyze the statement
        analyzer = BankStatementAnalyzer(temp_dir, api_key)
        analysis = analyzer.analyze_statement(temp_path)
        
        if not analysis:
            raise ValueError("Failed to analyze statement")
            
        # Calculate net change
        net_change = float(analysis.get('ending_balance', 0)) - float(analysis.get('opening_balance', 0))
        
        # Prepare response
        response = {
            'analysis': {
                'opening_balance': float(analysis.get('opening_balance', 0)),
                'ending_balance': float(analysis.get('ending_balance', 0)),
                'total_deposits': float(analysis.get('total_deposits', 0)),
                'total_withdrawals': float(analysis.get('total_withdrawals', 0)),
                'net_change': net_change
            },
            'recurring_transactions': analysis.get('recurring_transactions', []),
            'key_transactions': {
                'rent_payments': analysis.get('key_transactions', {}).get('rent_payments', []),
                'income_deposits': analysis.get('key_transactions', {}).get('salary_deposits', []),
                'utility_payments': analysis.get('key_transactions', {}).get('utility_payments', []),
                'loan_payments': analysis.get('key_transactions', {}).get('loan_payments', [])
            },
            'loan_assessment': {
                'decision': 'APPROVED' if analysis.get('loan_recommendation', {}).get('approved', False) else 'DENIED',
                'explanation': analysis.get('loan_recommendation', {}).get('explanation', 'No explanation provided')
            }
        }
        
        # Clean up temporary file
        os.remove(temp_path)
        os.rmdir(temp_dir)
        
        print("Sending response:", response)
        
        # Add CORS headers to response
        response_obj = jsonify(response)
        response_obj.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        return response_obj
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        error_response = jsonify({'error': str(e)})
        error_response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        return error_response, 500

@app.route('/test', methods=['GET'])
def test():
    response = jsonify({'message': 'Backend is working'})
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)