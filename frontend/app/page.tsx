'use client';

import { useState, useRef, ChangeEvent } from 'react';
import { documentAPI } from './services/api';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [studyGuide, setStudyGuide] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file first');
      return;
    }

    try {
      setUploadStatus('Uploading...');
      const response = await documentAPI.uploadDocument(file);

      setUploadStatus('Upload successful. Processing started...');
      setJobId(response.data.job_id);
      setIsProcessing(true);
      
      // Poll for processing status
      await pollForStatus(response.data.job_id);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus('Upload failed. Please try again.');
    }
  };

  const pollForStatus = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await documentAPI.getProcessingStatus(jobId);
        const { status, progress, message, study_guide_id } = response.data;

        setProgress(progress);
        setUploadStatus(message);

        if (status === 'completed') {
          clearInterval(pollInterval);
          setIsProcessing(false);
          
          // Fetch the generated study guide
          if (study_guide_id) {
            const guideResponse = await documentAPI.getStudyGuide(response.data.document_id);
            setStudyGuide(guideResponse.data);
            setUploadStatus('Study guide generated successfully!');
          }
        } else if (status === 'failed') {
          clearInterval(pollInterval);
          setIsProcessing(false);
          setUploadStatus('Processing failed. Please try again.');
        }
      } catch (error) {
        console.error('Status check error:', error);
        clearInterval(pollInterval);
        setIsProcessing(false);
        setUploadStatus('Error checking status. Please try again.');
      }
    }, 2000); // Poll every 2 seconds
  };

  const handleExport = async (format: string) => {
    if (!jobId) return;
    
    try {
      await documentAPI.exportStudyGuide(jobId, format);
      alert(`Study guide exported in ${format} format!`);
    } catch (error) {
      console.error('Export error:', error);
    }
 };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-gray-900 sm:text-5xl sm:tracking-tight lg:text-6xl">
            Study Guide Generator
          </h1>
          <p className="mt-3 max-w-2xl mx-auto text-xl text-gray-500 sm:mt-4">
            Transform your lecture materials into comprehensive study guides with AI-powered content analysis
          </p>
        </div>

        <div className="bg-white shadow-xl rounded-lg p-6 mb-8">
          <div className="flex flex-col items-center justify-center">
            <div className="w-full max-w-md">
              <div className="mb-6">
                <label className="block text-lg font-medium text-gray-700 mb-2">
                  Upload your document
                </label>
                <div className="flex items-center justify-center w-full">
                  <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer border-gray-300 bg-gray-50 hover:bg-gray-10">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                      </svg>
                      <p className="mb-2 text-sm text-gray-500">
                        <span className="font-semibold">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-gray-500">
                        PDF, DOCX, or image files (MAX. 50MB)
                      </p>
                    </div>
                    <input
                      id="file-upload"
                      type="file"
                      className="hidden"
                      onChange={handleFileChange}
                      accept=".pdf,.docx,.jpg,.jpeg,.png"
                    />
                  </label>
                </div>
                {file && (
                  <p className="mt-2 text-center text-sm text-gray-60">
                    Selected: {file.name}
                  </p>
                )}
              </div>

              <div className="flex justify-center">
                <button
                  onClick={handleUpload}
                  disabled={!file || isProcessing}
                  className={`px-6 py-3 rounded-md text-white font-medium ${
                    !file || isProcessing
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-indigo-600 hover:bg-indigo-700'
                  }`}
                >
                  {isProcessing ? 'Processing...' : 'Generate Study Guide'}
                </button>
              </div>
            </div>

            {uploadStatus && (
              <div className="mt-6 w-full max-w-md">
                <div className="text-center mb-2">
                  <p className="text-gray-700">{uploadStatus}</p>
                </div>
                {isProcessing && (
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className="bg-indigo-60 h-2.5 rounded-full transition-all duration-300 ease-in-out"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {studyGuide && (
          <div className="bg-white shadow-xl rounded-lg p-6">
            <h2 className="text-2xl font-bold text-gray-90 mb-4">Your Study Guide</h2>
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-800 mb-2">Title: {studyGuide.title || 'Untitled'}</h3>
              <p className="text-gray-600 mb-4">{studyGuide.summary || 'Summary will appear here...'}</p>
            </div>
            
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleExport('pdf')}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                Export as PDF
              </button>
              <button
                onClick={() => handleExport('markdown')}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Export as Markdown
              </button>
              <button
                onClick={() => handleExport('html')}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-70"
              >
                Export as HTML
              </button>
              <button
                onClick={() => handleExport('anki')}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              >
                Export for Anki
              </button>
            </div>
          </div>
        )}

        <div className="mt-12 bg-white shadow-lg rounded-lg p-6">
          <h2 className="text-2xl font-bold text-gray-90 mb-4">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-4">
              <div className="mx-auto bg-indigo-10 text-indigo-600 rounded-full w-16 h-16 flex items-center justify-center mb-4">
                <span className="text-2xl font-bold">1</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Upload Document</h3>
              <p className="text-gray-600">
                Upload your lecture slides, PDFs, or other course materials in various formats
              </p>
            </div>
            <div className="text-center p-4">
              <div className="mx-auto bg-indigo-100 text-indigo-600 rounded-full w-16 h-16 flex items-center justify-center mb-4">
                <span className="text-2xl font-bold">2</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">AI Processing</h3>
              <p className="text-gray-600">
                Our AI analyzes content, extracts key concepts, and generates questions
              </p>
            </div>
            <div className="text-center p-4">
              <div className="mx-auto bg-indigo-100 text-indigo-600 rounded-full w-16 h-16 flex items-center justify-center mb-4">
                <span className="text-2xl font-bold">3</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Download Study Guide</h3>
              <p className="text-gray-600">
                Get your customized study guide with summaries, questions, and concept maps
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}