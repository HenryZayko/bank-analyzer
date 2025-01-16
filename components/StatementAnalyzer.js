import React, { useState } from 'react';
import axios from 'axios';

const StatementAnalyzer = () => {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
        setError(null);
        setResult(null);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        
        if (!file) {
            setError('Please select a file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        setError(null);

        try {
            const response = await axios.post('http://localhost:5000/analyze', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            setResult(response.data);
        } catch (err) {
            setError(err.response?.data?.error || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const formatCurrency = (amount) => {
        return amount ? `$${amount.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}` : 'Not available';
    };

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Bank Statement Analyzer</h1>
            
            <form onSubmit={handleSubmit} className="mb-4">
                <div className="mb-4">
                    <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        className="border p-2"
                    />
                </div>
                <button
                    type="submit"
                    disabled={loading || !file}
                    className="bg-blue-500 text-white px-4 py-2 rounded"
                >
                    {loading ? 'Analyzing...' : 'Analyze Statement'}
                </button>
            </form>

            {error && (
                <div className="text-red-500 mb-4">
                    {error}
                </div>
            )}

            {result && (
                <div className="space-y-4">
                    <div className="border p-4 rounded">
                        <h2 className="text-xl font-bold mb-2">Financial Analysis</h2>
                        <p>Opening Balance: {formatCurrency(result.analysis.opening_balance)}</p>
                        <p>Total Credits: {formatCurrency(result.analysis.total_credits)}</p>
                        <p>Total Debits: {formatCurrency(result.analysis.total_debits)}</p>
                        <p>Net Change: {formatCurrency(result.analysis.net_change)}</p>
                        {result.analysis.percentage_change && (
                            <p>Percentage Change: {result.analysis.percentage_change.toFixed(2)}%</p>
                        )}
                    </div>

                    <div className="border p-4 rounded">
                        <h2 className="text-xl font-bold mb-2">Loan Assessment</h2>
                        <p className="text-lg">
                            Status: <span className={result.loan_assessment.eligible ? 'text-green-500' : 'text-red-500'}>
                                {result.loan_assessment.eligible ? 'APPROVED' : 'DENIED'}
                            </span>
                        </p>
                        <p>Credit Score: {result.loan_assessment.score.toFixed(1)}/100</p>
                        
                        {result.loan_assessment.eligible && (
                            <p>Recommended Loan Range: {formatCurrency(result.loan_assessment.loan_range.min)} - {formatCurrency(result.loan_assessment.loan_range.max)}</p>
                        )}
                        
                        <h3 className="font-bold mt-2">Key Factors:</h3>
                        <ul className="list-disc pl-5">
                            {result.loan_assessment.reasons.map((reason, index) => (
                                <li key={index}>{reason}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}
        </div>
    );
};

export default StatementAnalyzer; 