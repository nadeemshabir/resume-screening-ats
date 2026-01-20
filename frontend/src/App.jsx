import React, { useState, useEffect } from 'react';
import { Upload, FileText, Briefcase, Download, Trash2, Eye, X, BarChart3, Filter, Search, RefreshCw, AlertCircle, CheckCircle, Database, FileSpreadsheet, Link, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const ResumeScreeningSystem = () => {
    // State Management
    const [jobDescription, setJobDescription] = useState('');
    const [jdSet, setJdSet] = useState(false);
    const [jdRequirements, setJdRequirements] = useState(null);
    const [candidates, setCandidates] = useState([]);
    const [sheetFile, setSheetFile] = useState(null);
    const [failedCandidates, setFailedCandidates] = useState([]);
    const [processingProgress, setProcessingProgress] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [selectedCandidate, setSelectedCandidate] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterScore, setFilterScore] = useState('all');
    const [stats, setStats] = useState(null);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [backendStatus, setBackendStatus] = useState(null);

    // Check backend health on mount
    useEffect(() => {
        checkBackendHealth();
    }, []);

    // Fetch candidates on mount if JD is set
    useEffect(() => {
        if (jdSet) {
            fetchCandidates();
            fetchStats();
        }
    }, [jdSet]);

    const checkBackendHealth = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/`);
            setBackendStatus(response.data);
            showSuccess('Backend connected successfully');
        } catch (err) {
            showError('Backend not reachable. Make sure FastAPI server is running on port 8000');
            setBackendStatus({ status: 'offline' });
        }
    };

    const showError = (message) => {
        setError(message);
        setTimeout(() => setError(null), 5000);
    };

    const showSuccess = (message) => {
        setSuccess(message);
        setTimeout(() => setSuccess(null), 3000);
    };

    // Set Job Description
    const handleSetJD = async () => {
        if (!jobDescription.trim() || jobDescription.length < 50) {
            showError('Job description must be at least 50 characters');
            return;
        }

        try {
            setProcessing(true);
            const formData = new FormData();
            formData.append('jd_text', jobDescription);

            const response = await axios.post(`${API_BASE_URL}/api/jd/set`, formData);

            setJdSet(true);
            setJdRequirements(response.data.requirements_found);
            showSuccess('Job description set successfully! AI extracted requirements.');
            setProcessing(false);
        } catch (err) {
            showError(err.response?.data?.detail || 'Failed to set job description');
            setProcessing(false);
        }
    };

    // Handle Google Sheet file selection
    const handleSheetFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            setSheetFile(file);
        }
        e.target.value = '';
    };

    // Process Google Sheet - Parse file, fetch resumes from Drive, and score
    const handleProcessSheet = async () => {
        if (!sheetFile) {
            showError('Please upload a Google Sheet file');
            return;
        }

        if (!jdSet) {
            showError('Please set job description first');
            return;
        }

        setProcessing(true);
        setProcessingProgress({ status: 'Reading sheet...', current: 0, total: 0 });

        try {
            const formData = new FormData();
            formData.append('sheet_file', sheetFile);

            const response = await axios.post(`${API_BASE_URL}/api/sheets/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const { success_count, fail_count, failed_candidates } = response.data;

            setFailedCandidates(failed_candidates || []);
            setProcessingProgress(null);
            setProcessing(false);
            setSheetFile(null); // Clear uploaded file

            if (fail_count > 0) {
                showSuccess(`Processed ${success_count} candidates. ${fail_count} failed - check Failed Candidates section.`);
            } else {
                showSuccess(`Successfully processed ${success_count} candidates!`);
            }

            // Refresh candidates list
            fetchCandidates();
            fetchStats();

        } catch (err) {
            setProcessing(false);
            setProcessingProgress(null);
            showError(err.response?.data?.detail || 'Failed to process Google Sheet');
        }
    };

    // Upload Resumes and Match with CSV data
    const handleResumeUpload = async (e) => {
        const files = Array.from(e.target.files);

        if (!jdSet) {
            showError('Please set job description first');
            return;
        }

        if (csvData.length === 0) {
            showError('Please import CSV data from Google Sheets first');
            return;
        }

        setProcessing(true);
        let successCount = 0;
        let failCount = 0;

        for (const file of files) {
            try {
                // Match resume file to CSV data by filename or manual input
                // For now, we'll extract name from filename
                const fileNameWithoutExt = file.name.replace(/\.[^/.]+$/, "");

                // Try to find matching candidate in CSV
                let candidateData = csvData.find(c =>
                    fileNameWithoutExt.toLowerCase().includes(c.name?.toLowerCase())
                );

                if (!candidateData) {
                    // If no match, use first unprocessed candidate or skip
                    candidateData = csvData[successCount] || {
                        name: fileNameWithoutExt,
                        email: 'unknown@example.com',
                        phone: 'N/A'
                    };
                }

                // Prepare form data
                const formData = new FormData();
                formData.append('name', candidateData.name || fileNameWithoutExt);
                formData.append('email', candidateData.email || 'unknown@example.com');
                formData.append('phone', candidateData.phone || 'N/A');
                formData.append('experience_years', candidateData.experience_years || candidateData.experience || '');
                formData.append('current_location', candidateData.current_location || candidateData.location || '');
                formData.append('notice_period', candidateData.notice_period || '');
                formData.append('resume', file);

                // Upload to backend
                await axios.post(`${API_BASE_URL}/api/candidates/upload`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });

                successCount++;
            } catch (err) {
                console.error(`Failed to process ${file.name}:`, err);
                failCount++;
            }
        }

        setProcessing(false);
        showSuccess(`Processed ${successCount} resumes successfully${failCount > 0 ? `, ${failCount} failed` : ''}`);

        // Refresh candidates list
        fetchCandidates();
        fetchStats();

        e.target.value = '';
    };

    // Fetch all candidates
    const fetchCandidates = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/candidates/list`);
            setCandidates(response.data.candidates || []);
        } catch (err) {
            console.error('Failed to fetch candidates:', err);
        }
    };

    // Fetch statistics
    const fetchStats = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/stats`);
            setStats(response.data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    };

    // View candidate details
    const viewCandidateDetails = async (candidateId) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/candidates/${candidateId}`);
            setSelectedCandidate(response.data);
        } catch (err) {
            showError('Failed to load candidate details');
        }
    };

    // Delete candidate
    const deleteCandidate = async (candidateId) => {
        if (!confirm('Are you sure you want to delete this candidate?')) return;

        try {
            await axios.delete(`${API_BASE_URL}/api/candidates/${candidateId}`);
            showSuccess('Candidate deleted');
            fetchCandidates();
            fetchStats();
        } catch (err) {
            showError('Failed to delete candidate');
        }
    };

    // Clear all candidates
    const clearAll = async () => {
        if (!confirm('Clear all candidates? This cannot be undone.')) return;

        try {
            await axios.delete(`${API_BASE_URL}/api/candidates/clear`);
            setCandidates([]);
            setCsvData([]);
            showSuccess('All candidates cleared');
            fetchStats();
        } catch (err) {
            showError('Failed to clear candidates');
        }
    };

    // Export to CSV
    const exportToCSV = () => {
        const headers = [
            'Rank', 'Name', 'Email', 'Phone', 'Experience', 'Location', 'Notice Period',
            'Overall Score', 'Skills Match', 'Experience Match', 'Education Match', 'Keywords Match'
        ];

        const rows = filteredCandidates.map(c => [
            c.rank,
            c.name,
            c.email,
            c.phone,
            c.experience_years || 'N/A',
            c.current_location || 'N/A',
            c.notice_period || 'N/A',
            c.overall_score,
            c.skills_match,
            c.experience_match,
            c.education_match,
            c.keywords_match
        ]);

        const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `candidates_ranked_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
    };

    const getScoreColor = (score) => {
        if (score >= 75) return 'bg-green-100 text-green-800 border-green-300';
        if (score >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
        return 'bg-red-100 text-red-800 border-red-300';
    };

    const getScoreBadge = (score) => {
        if (score >= 75) return { label: 'Excellent', color: 'bg-green-600' };
        if (score >= 50) return { label: 'Good', color: 'bg-yellow-600' };
        return { label: 'Poor', color: 'bg-red-600' };
    };

    // Filter candidates
    const filteredCandidates = candidates.filter(c => {
        const matchesSearch = c.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            c.email?.toLowerCase().includes(searchTerm.toLowerCase());

        let matchesFilter = true;
        if (filterScore === 'excellent') matchesFilter = c.overall_score >= 75;
        else if (filterScore === 'good') matchesFilter = c.overall_score >= 50 && c.overall_score < 75;
        else if (filterScore === 'poor') matchesFilter = c.overall_score < 50;

        return matchesSearch && matchesFilter;
    });

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-4 md:p-8">
            <div className="max-w-7xl mx-auto">

                {/* Notifications */}
                {error && (
                    <div className="fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" />
                        {error}
                    </div>
                )}
                {success && (
                    <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2">
                        <CheckCircle className="w-5 h-5" />
                        {success}
                    </div>
                )}

                {/* Header */}
                <div className="text-center mb-8">
                    <div className="flex items-center justify-center mb-3">
                        <BarChart3 className="w-10 h-10 text-indigo-600 mr-3" />
                        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-indigo-600 to-blue-600 bg-clip-text text-transparent">
                            AI Resume Screening System
                        </h1>
                    </div>
                    <p className="text-gray-600 text-lg">Google Forms → CSV Import → AI Scoring → Ranked Results</p>

                    {/* Backend Status */}
                    <div className="mt-3 flex items-center justify-center gap-4 text-sm">
                        <span className={`flex items-center gap-1 ${backendStatus?.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                            <div className={`w-2 h-2 rounded-full ${backendStatus?.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                            Backend: {backendStatus?.status || 'Checking...'}
                        </span>
                        {backendStatus?.groq_api_available && (
                            <span className="flex items-center gap-1 text-green-600">
                                <CheckCircle className="w-3 h-3" />
                                Groq AI Active
                            </span>
                        )}
                        {backendStatus?.ocr_available && (
                            <span className="flex items-center gap-1 text-green-600">
                                <CheckCircle className="w-3 h-3" />
                                OCR Active
                            </span>
                        )}
                    </div>
                </div>

                {/* Statistics Dashboard */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-indigo-500">
                            <div className="text-sm text-gray-600">Total Candidates</div>
                            <div className="text-3xl font-bold text-indigo-600">{stats.total_candidates}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                            <div className="text-sm text-gray-600">Average Score</div>
                            <div className="text-3xl font-bold text-green-600">{stats.average_score}%</div>
                        </div>
                        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                            <div className="text-sm text-gray-600">Top Score</div>
                            <div className="text-3xl font-bold text-blue-600">{stats.top_score}%</div>
                        </div>
                        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
                            <div className="text-sm text-gray-600">JD Status</div>
                            <div className="text-sm font-semibold text-purple-600">{stats.jd_set ? 'Set ✓' : 'Not Set'}</div>
                        </div>
                    </div>
                )}

                {/* Job Description Section */}
                <div className="bg-white rounded-xl shadow-lg p-6 mb-6 border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center">
                            <Briefcase className="w-6 h-6 text-indigo-600 mr-3" />
                            <h2 className="text-2xl font-semibold text-gray-800">Step 1: Set Job Description</h2>
                        </div>
                        {jdSet && (
                            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold flex items-center gap-1">
                                <CheckCircle className="w-4 h-4" />
                                JD Set
                            </span>
                        )}
                    </div>
                    <textarea
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder="Paste the complete job description here... AI will extract requirements automatically."
                        className="w-full h-48 p-4 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none transition-all text-gray-700 mb-3"
                        disabled={jdSet}
                    />
                    <button
                        onClick={handleSetJD}
                        disabled={processing || jdSet}
                        className={`px-6 py-2 rounded-lg font-semibold transition-all ${jdSet
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md hover:shadow-lg'
                            }`}
                    >
                        {processing ? 'Processing...' : jdSet ? 'JD Already Set' : 'Set Job Description'}
                    </button>
                    {jdSet && (
                        <button
                            onClick={() => {
                                setJdSet(false);
                                setJdRequirements(null);
                                setJobDescription('');
                            }}
                            className="ml-3 px-6 py-2 rounded-lg font-semibold bg-orange-500 text-white hover:bg-orange-600 transition-all shadow-md"
                        >
                            Reset JD
                        </button>
                    )}

                    {jdRequirements && (
                        <div className="mt-4 p-4 bg-indigo-50 rounded-lg">
                            <div className="text-sm font-semibold text-indigo-900 mb-2">AI Extracted Requirements:</div>
                            <div className="flex flex-wrap gap-2">
                                {jdRequirements.skills?.slice(0, 10).map((skill, i) => (
                                    <span key={i} className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded-full">
                                        {skill}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Google Sheets Integration Section */}
                <div className="bg-white rounded-xl shadow-lg p-6 mb-6 border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center">
                            <FileSpreadsheet className="w-6 h-6 text-indigo-600 mr-3" />
                            <h2 className="text-2xl font-semibold text-gray-800">Step 2: Process Google Sheets</h2>
                        </div>
                        {candidates.length > 0 && (
                            <div className="flex gap-2">
                                <button
                                    onClick={fetchCandidates}
                                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all shadow-md"
                                >
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Refresh
                                </button>
                                <button
                                    onClick={exportToCSV}
                                    className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-all shadow-md"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    Export CSV
                                </button>
                                <button
                                    onClick={clearAll}
                                    className="flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all shadow-md"
                                >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    Clear All
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="space-y-4">
                        {/* Sheet File Upload */}
                        <div className="border-2 border-dashed border-indigo-300 rounded-xl p-6 text-center hover:border-indigo-400 hover:bg-indigo-50/50 transition-all">
                            <input
                                type="file"
                                accept=".xlsx,.xls,.csv"
                                onChange={handleSheetFileSelect}
                                className="hidden"
                                id="sheet-upload"
                                disabled={!jdSet || processing}
                            />
                            <label htmlFor="sheet-upload" className="cursor-pointer">
                                <FileSpreadsheet className="w-16 h-16 text-indigo-400 mx-auto mb-3" />
                                {!jdSet ? (
                                    <p className="text-lg text-gray-400 font-semibold">Set Job Description First</p>
                                ) : sheetFile ? (
                                    <div>
                                        <p className="text-lg text-green-600 font-semibold mb-1">
                                            <CheckCircle className="w-5 h-5 inline mr-2" />
                                            {sheetFile.name}
                                        </p>
                                        <p className="text-sm text-gray-500">Click to change file</p>
                                    </div>
                                ) : (
                                    <div>
                                        <p className="text-lg text-gray-700 font-semibold mb-1">
                                            Upload Google Sheets File
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            Download your Google Sheet as Excel (.xlsx) or CSV and upload here
                                        </p>
                                    </div>
                                )}
                            </label>
                        </div>

                        <p className="text-xs text-gray-500 text-center">
                            Sheet must have columns: Name, Email, Phone, Experience, Expected CTC, Resume Link (Google Drive link)
                        </p>

                        {/* Process Button */}
                        <button
                            onClick={handleProcessSheet}
                            disabled={!jdSet || !sheetFile || processing}
                            className={`w-full py-4 rounded-lg font-semibold text-lg transition-all flex items-center justify-center gap-3 ${!jdSet || !sheetFile || processing
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-gradient-to-r from-indigo-600 to-blue-600 text-white hover:from-indigo-700 hover:to-blue-700 shadow-lg hover:shadow-xl'
                                }`}
                        >
                            {processing ? (
                                <>
                                    <RefreshCw className="w-6 h-6 animate-spin" />
                                    {processingProgress?.status || 'Processing candidates...'}
                                </>
                            ) : (
                                <>
                                    <Upload className="w-6 h-6" />
                                    Process Google Sheet
                                </>
                            )}
                        </button>

                        {/* Processing Progress */}
                        {processing && (
                            <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                                    <div>
                                        <p className="font-semibold text-indigo-800">Fetching resumes from Google Drive...</p>
                                        <p className="text-sm text-indigo-600">This may take a few minutes depending on the number of candidates</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Info Box */}
                        {!processing && (
                            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                                <div className="flex items-start gap-3">
                                    <FileText className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
                                    <div className="text-sm text-blue-800">
                                        <p className="font-semibold mb-1">How it works:</p>
                                        <ol className="list-decimal list-inside space-y-1">
                                            <li>Download your Google Sheet as Excel (.xlsx) or CSV</li>
                                            <li>Each row should have a Resume Link pointing to Google Drive</li>
                                            <li>System will automatically download and process each resume</li>
                                            <li>AI will score and rank all candidates</li>
                                        </ol>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Failed Candidates Section */}
                {failedCandidates.length > 0 && (
                    <div className="bg-white rounded-xl shadow-lg p-6 mb-6 border border-orange-200">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center">
                                <AlertTriangle className="w-6 h-6 text-orange-500 mr-3" />
                                <h2 className="text-xl font-semibold text-gray-800">
                                    Failed Candidates ({failedCandidates.length})
                                </h2>
                            </div>
                            <button
                                onClick={() => setFailedCandidates([])}
                                className="text-sm text-gray-500 hover:text-gray-700"
                            >
                                Clear List
                            </button>
                        </div>
                        <p className="text-sm text-gray-600 mb-4">
                            These candidates could not be processed automatically. Please upload their resumes manually.
                        </p>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-orange-50 border-b border-orange-200">
                                    <tr>
                                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Row</th>
                                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Name</th>
                                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Email</th>
                                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Phone</th>
                                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Error</th>
                                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Resume Link</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {failedCandidates.map((fc, index) => (
                                        <tr key={index} className="hover:bg-orange-50">
                                            <td className="px-4 py-3 text-sm text-gray-600">{fc.row_number}</td>
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{fc.name}</td>
                                            <td className="px-4 py-3 text-sm text-gray-600">{fc.email}</td>
                                            <td className="px-4 py-3 text-sm text-gray-600">{fc.phone}</td>
                                            <td className="px-4 py-3 text-sm text-red-600">{fc.error}</td>
                                            <td className="px-4 py-3 text-sm">
                                                {fc.resume_link ? (
                                                    <a
                                                        href={fc.resume_link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 hover:underline truncate block max-w-xs"
                                                    >
                                                        Open Link
                                                    </a>
                                                ) : (
                                                    <span className="text-gray-400">No link</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Candidates Table */}
                {candidates.length > 0 && (
                    <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100">
                        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-blue-50">
                            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                                <h2 className="text-2xl font-semibold text-gray-800">
                                    Ranked Candidates ({filteredCandidates.length} of {candidates.length})
                                </h2>

                                <div className="flex flex-col sm:flex-row gap-3">
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            placeholder="Search..."
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-sm"
                                        />
                                    </div>

                                    <div className="relative">
                                        <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                                        <select
                                            value={filterScore}
                                            onChange={(e) => setFilterScore(e.target.value)}
                                            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-sm appearance-none cursor-pointer"
                                        >
                                            <option value="all">All Scores</option>
                                            <option value="excellent">Excellent (75%+)</option>
                                            <option value="good">Good (50-74%)</option>
                                            <option value="poor">Poor (&lt;50%)</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b-2 border-gray-200">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Rank</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Candidate</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Contact</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Details</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Score</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Skills</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Experience</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Education</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Keywords</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {filteredCandidates.map((candidate, index) => {
                                        const badge = getScoreBadge(candidate.overall_score);
                                        return (
                                            <tr key={candidate.id} className="hover:bg-gray-50 transition-colors">
                                                <td className="px-4 py-4">
                                                    <span className={`text-2xl font-bold ${index < 3 ? 'text-indigo-600' : 'text-gray-400'}`}>
                                                        #{candidate.rank}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="flex items-center">
                                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center text-white font-bold mr-3">
                                                            {candidate.name?.charAt(0)?.toUpperCase()}
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-semibold text-gray-900">{candidate.name}</div>
                                                            <div className="text-xs text-gray-500">{candidate.resume_filename}</div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="text-sm text-gray-900">{candidate.email}</div>
                                                    <div className="text-xs text-gray-500">{candidate.phone}</div>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="text-xs text-gray-600">
                                                        {candidate.experience_years && <div>Exp: {candidate.experience_years}</div>}
                                                        {candidate.current_location && <div>Loc: {candidate.current_location}</div>}
                                                        {candidate.notice_period && <div>Notice: {candidate.notice_period}</div>}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className={`inline-flex flex-col items-center px-3 py-2 rounded-lg border-2 ${getScoreColor(candidate.overall_score)}`}>
                                                        <span className="text-xl font-bold">{candidate.overall_score}%</span>
                                                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full text-white mt-1 ${badge.color}`}>
                                                            {badge.label}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className="text-sm font-semibold text-gray-900">{candidate.skills_match}%</span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className="text-sm font-semibold text-gray-900">{candidate.experience_match}%</span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className="text-sm font-semibold text-gray-900">{candidate.education_match}%</span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className="text-sm font-semibold text-gray-900">{candidate.keywords_match}%</span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => viewCandidateDetails(candidate.id)}
                                                            className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                                                            title="View Details"
                                                        >
                                                            <Eye className="w-5 h-5" />
                                                        </button>
                                                        <button
                                                            onClick={() => deleteCandidate(candidate.id)}
                                                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-all"
                                                            title="Delete"
                                                        >
                                                            <Trash2 className="w-5 h-5" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Candidate Details Modal */}
                {selectedCandidate && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
                        <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
                            <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-blue-50 flex justify-between items-start">
                                <div>
                                    <h3 className="text-2xl font-bold text-gray-800">{selectedCandidate.name}</h3>
                                    <p className="text-sm text-gray-600 mt-1">{selectedCandidate.email} • {selectedCandidate.phone}</p>
                                    <div className="mt-3 flex gap-3">
                                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getScoreColor(selectedCandidate.overall_score)}`}>
                                            Score: {selectedCandidate.overall_score}%
                                        </span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setSelectedCandidate(null)}
                                    className="p-2 text-gray-500 hover:bg-white rounded-lg transition-all"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Scrollable Content Area */}
                            <div className="overflow-y-auto" style={{ maxHeight: 'calc(90vh - 160px)' }}>
                                {/* Score Breakdown */}
                                <div className="p-6 border-b border-gray-200 bg-gray-50">
                                    <h4 className="font-semibold text-gray-700 mb-3">Score Breakdown</h4>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="bg-white p-3 rounded-lg border border-gray-200">
                                            <div className="text-xs text-gray-500 mb-1">Skills Match</div>
                                            <div className="text-xl font-bold text-indigo-600">{selectedCandidate.skills_match}%</div>
                                        </div>
                                        <div className="bg-white p-3 rounded-lg border border-gray-200">
                                            <div className="text-xs text-gray-500 mb-1">Experience</div>
                                            <div className="text-xl font-bold text-indigo-600">{selectedCandidate.experience_match}%</div>
                                        </div>
                                        <div className="bg-white p-3 rounded-lg border border-gray-200">
                                            <div className="text-xs text-gray-500 mb-1">Education</div>
                                            <div className="text-xl font-bold text-indigo-600">{selectedCandidate.education_match}%</div>
                                        </div>
                                        <div className="bg-white p-3 rounded-lg border border-gray-200">
                                            <div className="text-xs text-gray-500 mb-1">Keywords</div>
                                            <div className="text-xl font-bold text-indigo-600">{selectedCandidate.keywords_match}%</div>
                                        </div>
                                    </div>

                                    {/* AI Explanation */}
                                    {selectedCandidate.scores?.explanation && (
                                        <div className="mt-4 space-y-3">
                                            <div className="bg-white p-3 rounded-lg border border-gray-200">
                                                <div className="text-xs font-semibold text-gray-600 mb-1">Overall Assessment:</div>
                                                <div className="text-sm text-gray-700">{selectedCandidate.scores.explanation.overall}</div>
                                            </div>

                                            {selectedCandidate.scores.explanation.strengths?.length > 0 && (
                                                <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                                                    <div className="text-xs font-semibold text-green-800 mb-2">Strengths:</div>
                                                    <ul className="text-sm text-green-700 space-y-1">
                                                        {selectedCandidate.scores.explanation.strengths.map((s, i) => (
                                                            <li key={i}>• {s}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}

                                            {selectedCandidate.scores.explanation.weaknesses?.length > 0 && (
                                                <div className="bg-red-50 p-3 rounded-lg border border-red-200">
                                                    <div className="text-xs font-semibold text-red-800 mb-2">Areas for Improvement:</div>
                                                    <ul className="text-sm text-red-700 space-y-1">
                                                        {selectedCandidate.scores.explanation.weaknesses.map((w, i) => (
                                                            <li key={i}>• {w}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="p-6 overflow-y-auto max-h-96">
                                    <h4 className="font-semibold text-gray-700 mb-3">Full Resume</h4>
                                    <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-gray-50 p-4 rounded-lg border border-gray-200">
                                        {selectedCandidate.resume_text}
                                    </pre>
                                </div>
                            </div> {/* End Scrollable Content Area */}
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {candidates.length === 0 && !processing && (
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-8">
                        <div className="flex flex-col items-center text-center">
                            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                                <FileText className="w-10 h-10 text-blue-600" />
                            </div>
                            <h3 className="text-2xl font-bold text-blue-900 mb-3">Ready to Screen Candidates</h3>
                            <div className="max-w-3xl">
                                <p className="text-blue-800 mb-4">Follow the workflow:</p>
                                <div className="grid md:grid-cols-3 gap-4 text-left">
                                    <div className="bg-white p-4 rounded-lg border border-blue-200">
                                        <div className="flex items-start">
                                            <div className="w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold mr-3 flex-shrink-0">1</div>
                                            <div>
                                                <div className="font-semibold text-gray-800 mb-1">Set Job Description</div>
                                                <div className="text-sm text-gray-600">AI will extract requirements automatically</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="bg-white p-4 rounded-lg border border-blue-200">
                                        <div className="flex items-start">
                                            <div className="w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold mr-3 flex-shrink-0">2</div>
                                            <div>
                                                <div className="font-semibold text-gray-800 mb-1">Import Google Sheets CSV</div>
                                                <div className="text-sm text-gray-600">Export from Google Forms and upload</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="bg-white p-4 rounded-lg border border-blue-200">
                                        <div className="flex items-start">
                                            <div className="w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold mr-3 flex-shrink-0">3</div>
                                            <div>
                                                <div className="font-semibold text-gray-800 mb-1">Upload Resumes</div>
                                                <div className="text-sm text-gray-600">AI scores and ranks automatically</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ResumeScreeningSystem;