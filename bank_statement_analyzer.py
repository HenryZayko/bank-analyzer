import os
import pdfplumber
from anthropic import Anthropic
import json
from datetime import datetime

class BankStatementAnalyzer:
    def __init__(self, statements_dir, api_key):
        self.statements_dir = statements_dir
        self.anthropic = Anthropic(api_key=api_key)
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        print(f"\nExtracting text from {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n\n"
            return text

    def analyze_statement(self, pdf_path):
        """Analyze a single bank statement using Claude"""
        # Extract text from PDF
        statement_text = self.extract_text_from_pdf(pdf_path)
        
        # Prepare prompt for Claude
        prompt = f"""You are a bank loan officer analyzing a bank statement. Please analyze this statement and provide:
        1. Opening balance
        2. Ending balance
        3. Total deposits for the period
        4. Total withdrawals for the period
        5. List of recurring transactions (transactions that appear multiple times)
           - Include the description, amount, and frequency for each recurring transaction
           - Only include transactions that occur at least twice
           - If the amounts vary slightly, calculate the average amount
        6. Key Transaction Analysis:
           - Identify all rent/lease payments (amount and frequency)
           - Identify salary/income deposits (amount and frequency)
           - List all utility payments (type, amount, frequency)
           - Find any existing loan payments or debt obligations
        7. Loan recommendation
           - Whether you would approve a business loan (true/false)
           - Maximum recommended loan amount
           - Brief explanation of your decision (2-3 sentences)

        Here is the bank statement text:
        {statement_text}

        Return your response as a simple JSON object with these values. Format all numbers as plain numbers without commas. For example:
        {{
            "opening_balance": "1234.56",
            "ending_balance": "2345.67",
            "total_deposits": "5000.00",
            "total_withdrawals": "3889.89",
            "recurring_transactions": [
                {{
                    "description": "Monthly Rent Payment",
                    "amount": "2000.00",
                    "frequency": "Monthly"
                }}
            ],
            "key_transactions": {{
                "rent_payments": [
                    {{
                        "description": "Rent to ABC Properties",
                        "amount": "2000.00",
                        "frequency": "Monthly"
                    }}
                ],
                "salary_deposits": [
                    {{
                        "description": "Salary from XYZ Corp",
                        "amount": "5000.00",
                        "frequency": "Monthly"
                    }}
                ],
                "utility_payments": [
                    {{
                        "type": "Electricity",
                        "description": "Power Company Bill",
                        "amount": "150.00",
                        "frequency": "Monthly"
                    }},
                    {{
                        "type": "Water",
                        "description": "City Water Bill",
                        "amount": "75.00",
                        "frequency": "Monthly"
                    }}
                ],
                "loan_payments": [
                    {{
                        "description": "Car Loan Payment",
                        "amount": "400.00",
                        "frequency": "Monthly",
                        "estimated_total_debt": "24000.00"
                    }}
                ]
            }},
            "loan_recommendation": {{
                "approved": true,
                "max_amount": "25000.00",
                "explanation": "Strong cash flow with consistent monthly deposits averaging $5000. Regular rent payments show responsibility, and the growing account balance demonstrates good financial management."
            }}
        }}
        """

        # Get analysis from Claude
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse JSON response
        try:
            # Extract the content from the response
            response_text = response.content[0].text
            
            # Remove code block markers if present
            if response_text.startswith('```'):
                start = response_text.find('\n') + 1
                end = response_text.rfind('```')
                if end == -1:
                    response_text = response_text[start:]
                else:
                    response_text = response_text[start:end]
            
            # Remove "json" if it's the first line
            if response_text.startswith('json'):
                response_text = response_text[4:]
            
            # Clean up any potential JSON formatting issues
            response_text = response_text.replace("Rs.", "")  # Remove currency markers
            
            # Convert numeric strings to floats for proper JSON parsing
            import re
            def convert_numeric_string(match):
                # Remove all commas before converting to float
                num_str = match.group(1).replace(',', '')
                try:
                    return str(float(num_str))
                except ValueError:
                    return match.group(0)
            
            # Match any quoted number with optional commas
            response_text = re.sub(r'"([\d,]+\.?\d*)"', convert_numeric_string, response_text)
                
            # Parse the JSON
            analysis = json.loads(response_text.strip())
            return analysis
            
        except (json.JSONDecodeError, AttributeError, IndexError) as e:
            print(f"Error parsing Claude's response: {str(e)}")
            print("Raw response:", response.content)
            return None

def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Analyze bank statements using Claude')
    parser.add_argument('pdf_path', type=str, help='Path to the PDF bank statement file')
    parser.add_argument('--api-key', type=str, help='Anthropic API key', 
                        default=os.getenv('ANTHROPIC_API_KEY'))
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: No API key provided. Set ANTHROPIC_API_KEY environment variable or use --api-key")
        return
        
    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found at {args.pdf_path}")
        return
    
    if not args.pdf_path.lower().endswith('.pdf'):
        print("Error: File must be a PDF")
        return
    
    analyzer = BankStatementAnalyzer(os.path.dirname(args.pdf_path), args.api_key)
    analysis = analyzer.analyze_statement(args.pdf_path)
    
    if analysis:
        print("\nBank Statement Analysis")
        print("=" * 50)
        
        try:
            print(f"Opening Balance: ${float(analysis.get('opening_balance', 0)):,.2f}")
            print(f"Ending Balance: ${float(analysis.get('ending_balance', 0)):,.2f}")
            print(f"Total Deposits: ${float(analysis.get('total_deposits', 0)):,.2f}")
            print(f"Total Withdrawals: ${float(analysis.get('total_withdrawals', 0)):,.2f}")
            
            # Calculate net change
            net_change = float(analysis.get('ending_balance', 0)) - float(analysis.get('opening_balance', 0))
            print(f"Net Change: ${net_change:,.2f}")
            
            # Print recurring transactions
            print("\nRecurring Transactions:")
            print("-" * 50)
            recurring = analysis.get('recurring_transactions', [])
            if recurring:
                for transaction in recurring:
                    amount = float(transaction.get('amount', 0))
                    desc = transaction.get('description', 'Unknown')
                    freq = transaction.get('frequency', 'Unknown')
                    print(f"Description: {desc}")
                    print(f"Amount: ${amount:,.2f}")
                    print(f"Frequency: {freq}")
                    print("-" * 30)
            else:
                print("No recurring transactions found")
            
            # Print key transactions
            print("\nKey Transactions Analysis")
            print("=" * 50)
            
            # Print rent payments
            print("\nRent/Lease Payments:")
            print("-" * 30)
            rent_payments = analysis.get('key_transactions', {}).get('rent_payments', [])
            if rent_payments:
                for payment in rent_payments:
                    amount = float(payment.get('amount', 0))
                    desc = payment.get('description', 'Unknown')
                    freq = payment.get('frequency', 'Unknown')
                    print(f"Description: {desc}")
                    print(f"Amount: ${amount:,.2f}")
                    print(f"Frequency: {freq}")
                    print("-" * 20)
            else:
                print("No rent payments identified")
            
            # Print salary deposits
            print("\nSalary/Income Deposits:")
            print("-" * 30)
            salary_deposits = analysis.get('key_transactions', {}).get('salary_deposits', [])
            if salary_deposits:
                for deposit in salary_deposits:
                    amount = float(deposit.get('amount', 0))
                    desc = deposit.get('description', 'Unknown')
                    freq = deposit.get('frequency', 'Unknown')
                    print(f"Description: {desc}")
                    print(f"Amount: ${amount:,.2f}")
                    print(f"Frequency: {freq}")
                    print("-" * 20)
            else:
                print("No salary deposits identified")
            
            # Print utility payments
            print("\nUtility Payments:")
            print("-" * 30)
            utility_payments = analysis.get('key_transactions', {}).get('utility_payments', [])
            if utility_payments:
                for payment in utility_payments:
                    amount = float(payment.get('amount', 0))
                    desc = payment.get('description', 'Unknown')
                    type_ = payment.get('type', 'Unknown')
                    freq = payment.get('frequency', 'Unknown')
                    print(f"Type: {type_}")
                    print(f"Description: {desc}")
                    print(f"Amount: ${amount:,.2f}")
                    print(f"Frequency: {freq}")
                    print("-" * 20)
            else:
                print("No utility payments identified")
            
            # Print loan payments
            print("\nLoan Payments and Debt Obligations:")
            print("-" * 30)
            loan_payments = analysis.get('key_transactions', {}).get('loan_payments', [])
            if loan_payments:
                for payment in loan_payments:
                    amount = float(payment.get('amount', 0))
                    desc = payment.get('description', 'Unknown')
                    freq = payment.get('frequency', 'Unknown')
                    total_debt = payment.get('estimated_total_debt', 'Unknown')
                    
                    print(f"Description: {desc}")
                    print(f"Payment Amount: ${amount:,.2f}")
                    print(f"Frequency: {freq}")
                    
                    # Only try to format total_debt if it's a number
                    if isinstance(total_debt, (int, float)) or (isinstance(total_debt, str) and total_debt.replace('.', '').isdigit()):
                        try:
                            total_debt = float(total_debt)
                            print(f"Estimated Total Debt: ${total_debt:,.2f}")
                        except ValueError:
                            print(f"Estimated Total Debt: {total_debt}")
                    else:
                        print(f"Estimated Total Debt: {total_debt}")
                    
                    print("-" * 20)
            else:
                print("No loan payments identified")
            
            # Print loan recommendation
            print("\nLoan Recommendation")
            print("-" * 50)
            recommendation = analysis.get('loan_recommendation', {})
            decision = "APPROVED" if recommendation.get('approved', False) else "DENIED"
            max_amount = float(recommendation.get('max_amount', 0))
            explanation = recommendation.get('explanation', 'No explanation provided')
            
            print(f"Decision: {decision}")
            if max_amount > 0:
                print(f"Maximum Recommended Amount: ${max_amount:,.2f}")
            print(f"Explanation: {explanation}")
                
        except ValueError as e:
            print(f"Error formatting numbers: {str(e)}")
            print("Raw analysis:", analysis)

if __name__ == "__main__":
    main() 