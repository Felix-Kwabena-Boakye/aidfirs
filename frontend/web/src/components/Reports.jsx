import React, { useState, useEffect } from 'react';
import { casesAPI, evidenceAPI, analysisAPI } from '../api';
import { jsPDF } from 'jspdf';
import { FileText, Download, BarChart2, PieChart, Calendar } from 'lucide-react';

const Reports = () => {
  const [stats, setStats] = useState({
    totalCases: 0,
    totalEvidence: 0,
    totalAnalyses: 0,
    casesByStatus: {},
    casesByPriority: {},
    cases: [],
    evidence: [],
    analyses: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reportType, setReportType] = useState('summary');
  const [selectedCase, setSelectedCase] = useState(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [casesRes, evidenceRes, analysesRes] = await Promise.all([
        casesAPI.getCases(),
        evidenceAPI.getEvidence(),
        analysisAPI.getAnalyses()
      ]);

      const cases = casesRes.data || [];
      const evidence = evidenceRes.data || [];
      const analyses = analysesRes.data || [];

      // Calculate cases by status
      const casesByStatus = cases.reduce((acc, c) => {
        acc[c.status] = (acc[c.status] || 0) + 1;
        return acc;
      }, {});

      // Calculate cases by priority
      const casesByPriority = cases.reduce((acc, c) => {
        acc[c.priority] = (acc[c.priority] || 0) + 1;
        return acc;
      }, {});

      setStats({
        totalCases: cases.length,
        totalEvidence: evidence.length,
        totalAnalyses: analyses.length,
        casesByStatus,
        casesByPriority,
        cases,
        evidence,
        analyses
      });
    } catch (err) {
      setError('Failed to load statistics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Generate professional PDF report
  const generatePDFReport = () => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    let yPos = margin;

    // Header - Blue banner
    doc.setFillColor(30, 58, 138); // Dark blue
    doc.rect(0, 0, pageWidth, 40, 'F');
    
    // Title
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(22);
    doc.setFont('helvetica', 'bold');
    doc.text('AI Digital Forensics System', margin, 20);
    
    doc.setFontSize(14);
    doc.setFont('helvetica', 'normal');
    doc.text('Forensic Analysis Report', margin, 30);

    yPos = 55;

    // Report metadata
    doc.setTextColor(100, 100, 100);
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, margin, yPos);
    yPos += 7;
    doc.text(`Report Type: ${reportType === 'summary' ? 'Summary Report' : 'Detailed Case Report'}`, margin, yPos);
    yPos += 15;

    // Horizontal line
    doc.setDrawColor(200, 200, 200);
    doc.line(margin, yPos, pageWidth - margin, yPos);
    yPos += 15;

    // Executive Summary Section
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Executive Summary', margin, yPos);
    yPos += 10;

    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    const summaryText = `This report provides a comprehensive overview of the digital forensics cases, evidence, and analyses conducted using the AI Digital Forensics System. The data presented covers all cases, evidence items, and analysis results in the system.`;
    
    const splitSummary = doc.splitTextToSize(summaryText, pageWidth - 2 * margin);
    doc.text(splitSummary, margin, yPos);
    yPos += splitSummary.length * 5 + 10;

    // Statistics Section
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('System Statistics', margin, yPos);
    yPos += 10;

    // Statistics table
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    
    const statsData = [
      ['Total Cases', stats.totalCases.toString()],
      ['Total Evidence Items', stats.totalEvidence.toString()],
      ['Total Analyses', stats.totalAnalyses.toString()],
      ['Open Cases', (stats.casesByStatus['open'] || 0).toString()],
      ['Closed Cases', (stats.casesByStatus['closed'] || 0).toString()],
      ['In Progress Cases', (stats.casesByStatus['in_progress'] || 0).toString()],
      ['Archived Cases', (stats.casesByStatus['archived'] || 0).toString()]
    ];

    // Table header
    doc.setFillColor(240, 240, 240);
    doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 10, 'F');
    doc.setFont('helvetica', 'bold');
    doc.text('Metric', margin + 5, yPos);
    doc.text('Count', pageWidth - margin - 30, yPos);
    yPos += 10;

    // Table rows
    doc.setFont('helvetica', 'normal');
    statsData.forEach((row, index) => {
      if (index % 2 === 0) {
        doc.setFillColor(250, 250, 250);
        doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 8, 'F');
      }
      doc.text(row[0], margin + 5, yPos);
      doc.text(row[1], pageWidth - margin - 30, yPos);
      yPos += 8;
    });

    yPos += 15;

    // Cases by Priority
    if (Object.keys(stats.casesByPriority).length > 0) {
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Cases by Priority', margin, yPos);
      yPos += 10;

      doc.setFontSize(11);
      doc.setFont('helvetica', 'normal');
      
      Object.entries(stats.casesByPriority).forEach(([priority, count]) => {
        const priorityLabel = priority.charAt(0).toUpperCase() + priority.slice(1);
        doc.text(`• ${priorityLabel}: ${count} cases`, margin + 5, yPos);
        yPos += 7;
      });
      
      yPos += 10;
    }

    // Cases List (if there's room)
    if (yPos < pageHeight - 60 && stats.cases.length > 0) {
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Recent Cases', margin, yPos);
      yPos += 10;

      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      
      stats.cases.slice(0, 10).forEach((caseItem) => {
        if (yPos > pageHeight - 30) {
          doc.addPage();
          yPos = margin;
        }
        
        const caseInfo = `#${caseItem.case_number || 'N/A'} - ${caseItem.title || 'Untitled'}`;
        const caseStatus = `Status: ${caseItem.status || 'unknown'} | Priority: ${caseItem.priority || 'N/A'}`;
        
        doc.setFont('helvetica', 'bold');
        doc.text(caseInfo, margin, yPos);
        yPos += 5;
        
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(100, 100, 100);
        doc.text(caseStatus, margin, yPos);
        doc.setTextColor(0, 0, 0);
        yPos += 8;
      });
    }

    // Footer on last page
    const totalPages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(9);
      doc.setTextColor(150, 150, 150);
      doc.text(
        `Page ${i} of ${totalPages} | AI Digital Forensics System | Confidential`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      );
    }

    // Save the PDF
    doc.save(`forensic-report-${new Date().toISOString().split('T')[0]}.pdf`);
  };

  // Generate case-specific PDF report
  const generateCasePDF = (caseItem) => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 20;
    let yPos = margin;

    // Header
    doc.setFillColor(30, 58, 138);
    doc.rect(0, 0, pageWidth, 40, 'F');
    
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('Digital Forensics Case Report', margin, 20);
    
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text(`Case Number: ${caseItem.case_number || 'N/A'}`, margin, 32);

    yPos = 55;

    // Case Details
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Case Information', margin, yPos);
    yPos += 10;

    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    
    const caseDetails = [
      ['Case Number:', caseItem.case_number || 'N/A'],
      ['Title:', caseItem.title || 'Untitled'],
      ['Description:', caseItem.description || 'No description'],
      ['Status:', (caseItem.status || 'unknown').toUpperCase()],
      ['Priority:', (caseItem.priority || 'N/A').toUpperCase()],
      ['Case Type:', caseItem.case_type || 'N/A'],
      ['Created:', caseItem.created_at ? new Date(caseItem.created_at).toLocaleString() : 'N/A'],
    ];

    caseDetails.forEach(([label, value]) => {
      doc.setFont('helvetica', 'bold');
      doc.text(label, margin, yPos);
      doc.setFont('helvetica', 'normal');
      const valueStr = value.toString();
      const splitValue = doc.splitTextToSize(valueStr, pageWidth - margin - 60);
      doc.text(splitValue, margin + 60, yPos);
      yPos += splitValue.length * 5 + 3;
    });

    yPos += 10;

    // Evidence Section
    const caseEvidence = stats.evidence.filter(e => e.case_id === caseItem._id);
    if (caseEvidence.length > 0) {
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Evidence Items', margin, yPos);
      yPos += 10;

      doc.setFontSize(10);
      caseEvidence.forEach((ev) => {
        if (yPos > 270) {
          doc.addPage();
          yPos = margin;
        }
        doc.setFont('helvetica', 'bold');
        doc.text(`• ${ev.file_name || 'Unknown file'}`, margin, yPos);
        yPos += 5;
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(100, 100, 100);
        doc.text(`  Type: ${ev.evidence_type || 'N/A'} | Status: ${ev.status || 'N/A'}`, margin, yPos);
        doc.setTextColor(0, 0, 0);
        yPos += 8;
      });
    }

    // Analysis Section
    const caseAnalyses = stats.analyses.filter(a => a.case_id === caseItem._id);
    if (caseAnalyses.length > 0) {
      yPos += 10;
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Analysis Results', margin, yPos);
      yPos += 10;

      doc.setFontSize(10);
      caseAnalyses.forEach((analysis) => {
        if (yPos > 270) {
          doc.addPage();
          yPos = margin;
        }
        doc.setFont('helvetica', 'bold');
        doc.text(`• ${analysis.analysis_type || 'Analysis'}`, margin, yPos);
        yPos += 5;
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(100, 100, 100);
        doc.text(`  Status: ${analysis.status || 'N/A'} | Severity: ${analysis.severity || 'N/A'}`, margin, yPos);
        doc.setTextColor(0, 0, 0);
        yPos += 8;
      });
    }

    // Footer
    const pageHeight = doc.internal.pageSize.getHeight();
    doc.setFontSize(9);
    doc.setTextColor(150, 150, 150);
    doc.text(
      `Generated: ${new Date().toLocaleString()} | AI Digital Forensics System`,
      pageWidth / 2,
      pageHeight - 10,
      { align: 'center' }
    );

    doc.save(`case-${caseItem.case_number || caseItem._id}-report.pdf`);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'open': return 'bg-green-500';
      case 'in_progress': return 'bg-blue-500';
      case 'closed': return 'bg-gray-500';
      case 'archived': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FileText className="w-6 h-6 text-blue-400" />
          Reports
        </h1>
        <div className="flex gap-2">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="bg-gray-900 border border-gray-700 text-gray-200 px-4 py-2 rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm"
          >
            <option value="summary">Summary Report</option>
            <option value="detailed">Detailed Report</option>
          </select>
          <button
            onClick={generatePDFReport}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl transition-all font-semibold flex items-center gap-2 hover:scale-[1.01] text-sm"
          >
            <Download className="w-4 h-4" />
            Export PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/20 border border-rose-500/30 text-rose-400 px-4 py-3 rounded-xl mb-4 text-xs font-mono">
          {error}
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-gray-400">Loading statistics...</div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
              <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 font-mono">
                <BarChart2 className="w-4 h-4 text-blue-400" />
                Total Cases
              </h3>
              <p className="text-3xl font-bold text-white mt-3">{stats.totalCases}</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
              <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 font-mono">
                <FileText className="w-4 h-4 text-green-400" />
                Total Evidence
              </h3>
              <p className="text-3xl font-bold text-white mt-3">{stats.totalEvidence}</p>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
              <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider flex items-center gap-2 font-mono">
                <PieChart className="w-4 h-4 text-purple-400" />
                Total Analyses
              </h3>
              <p className="text-3xl font-bold text-white mt-3">{stats.totalAnalyses}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Cases by Status */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
              <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-blue-400" />
                Cases by Status
              </h3>
              {Object.keys(stats.casesByStatus).length === 0 ? (
                <p className="text-gray-400 text-sm">No case data available</p>
              ) : (
                <div className="space-y-3">
                  {Object.entries(stats.casesByStatus).map(([status, count]) => (
                    <div key={status} className="flex items-center">
                      <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(status)} mr-3`}></div>
                      <span className="flex-1 text-gray-300 text-sm capitalize">{status.replace('_', ' ')}</span>
                      <span className="font-bold text-white font-mono text-sm">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Cases by Priority */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-lg">
              <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-blue-400" />
                Cases by Priority
              </h3>
              {Object.keys(stats.casesByPriority).length === 0 ? (
                <p className="text-gray-400 text-sm">No case data available</p>
              ) : (
                <div className="space-y-3">
                  {Object.entries(stats.casesByPriority).map(([priority, count]) => (
                    <div key={priority} className="flex items-center">
                      <div className={`w-2.5 h-2.5 rounded-full ${getPriorityColor(priority)} mr-3`}></div>
                      <span className="flex-1 text-gray-300 text-sm capitalize">{priority}</span>
                      <span className="font-bold text-white font-mono text-sm">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Cases Table */}
          {reportType === 'detailed' && stats.cases.length > 0 && (
            <div className="mt-6 bg-gray-800 border border-gray-700 rounded-xl shadow-xl overflow-hidden">
              <div className="p-4 border-b border-gray-700 bg-gray-900/30">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-400" />
                  All Cases
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-900/40 border-b border-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-gray-400 font-semibold text-xs uppercase tracking-wider font-mono">Case #</th>
                      <th className="px-4 py-3 text-left text-gray-400 font-semibold text-xs uppercase tracking-wider font-mono">Title</th>
                      <th className="px-4 py-3 text-left text-gray-400 font-semibold text-xs uppercase tracking-wider font-mono">Status</th>
                      <th className="px-4 py-3 text-left text-gray-400 font-semibold text-xs uppercase tracking-wider font-mono">Priority</th>
                      <th className="px-4 py-3 text-left text-gray-400 font-semibold text-xs uppercase tracking-wider font-mono">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {stats.cases.map((caseItem) => (
                      <tr key={caseItem._id} className="hover:bg-gray-700/20 transition-all">
                        <td className="px-4 py-3 text-blue-400 font-mono text-sm">{caseItem.case_number || 'N/A'}</td>
                        <td className="px-4 py-3 text-gray-200 text-sm">{caseItem.title || 'Untitled'}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs text-white font-semibold ${getStatusColor(caseItem.status)}`}>
                            {caseItem.status || 'N/A'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs text-white font-semibold ${getPriorityColor(caseItem.priority)}`}>
                            {caseItem.priority || 'N/A'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => generateCasePDF(caseItem)}
                            className="text-blue-400 hover:text-blue-300 text-sm font-semibold transition-colors"
                          >
                            Export PDF
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Reports;
